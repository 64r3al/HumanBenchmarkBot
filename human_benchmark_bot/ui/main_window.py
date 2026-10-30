"""Main window orchestration for the HumanBenchmarkBot desktop UI."""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QCloseEvent, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ..calibration import (
    CalibrationError,
    calibration_path,
    config_directory,
    load_calibration,
    save_calibration,
)
from .dialogs import SafetyDialog, SelectionDialog
from .pages import MainWindowPages, NAV_ITEMS, _muted_label
from .services import (
    GAME_LABELS,
    HistoryStore,
    PreflightCheck,
    RunConfig,
    build_preflight,
    build_preview,
    can_start_run,
    validate_run_config,
)
from .theme import stylesheet
from .workers import RunWorker


class MainWindow(QMainWindow, MainWindowPages):
    """Coordinate navigation, settings, calibration, and background run state."""

    def __init__(self, settings: QSettings, parent: QWidget | None = None):
        super().__init__(parent)
        self.settings = settings
        self.history = HistoryStore()
        self.worker: RunWorker | None = None
        self.current_config: RunConfig | None = None
        self.pending_result: dict[str, Any] | None = None
        self.run_started_at = 0.0
        self.current_page = 0
        self.elapsed_timer = QTimer(self)
        self.elapsed_timer.setInterval(1000)
        self.elapsed_timer.timeout.connect(self._update_elapsed)

        self.setWindowTitle("HumanBenchmarkBot")
        self.setMinimumSize(960, 680)
        self.resize(1220, 820)

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.setCentralWidget(central)

        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(218)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(16, 20, 16, 16)
        side_layout.setSpacing(8)

        brand_row = QHBoxLayout()
        brand_mark = QLabel("HB")
        brand_mark.setObjectName("BrandMark")
        brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_mark.setFixedSize(40, 40)
        brand_text = QVBoxLayout()
        brand_title = QLabel("HumanBenchmark")
        brand_title.setObjectName("BrandTitle")
        brand_subtitle = QLabel("DESKTOP AUTOMATION")
        brand_subtitle.setObjectName("BrandSubtitle")
        brand_text.addWidget(brand_title)
        brand_text.addWidget(brand_subtitle)
        brand_row.addWidget(brand_mark)
        brand_row.addLayout(brand_text, 1)
        side_layout.addLayout(brand_row)
        side_layout.addSpacing(24)

        self.nav_buttons: list[QPushButton] = []
        for index, (label, tooltip) in enumerate(NAV_ITEMS):
            nav = QPushButton(label)
            nav.setObjectName("NavButton")
            nav.setCheckable(True)
            nav.setToolTip(tooltip)
            nav.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            nav.clicked.connect(lambda checked=False, i=index: self.navigate(i))
            self.nav_buttons.append(nav)
            side_layout.addWidget(nav)

        side_layout.addStretch(1)
        safety_card = QFrame()
        safety_card.setObjectName("Card")
        safety_layout = QVBoxLayout(safety_card)
        safety_layout.setContentsMargins(12, 12, 12, 12)
        safety_title = QLabel("Safety first")
        safety_title.setObjectName("CardTitle")
        safety_layout.addWidget(safety_title)
        safety_layout.addWidget(
            _muted_label(
                "Preview is safe by default. Desktop input always requires confirmation."
            )
        )
        side_layout.addWidget(safety_card)
        version = QLabel("v0.3.0 · experimental")
        version.setObjectName("BrandSubtitle")
        side_layout.addWidget(version)
        root.addWidget(sidebar)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready · Preview mode is the safe default")

        self.dashboard_page = self._build_dashboard()
        self.games_page = self._build_games()
        self.run_page = self._build_run_page()
        self.calibration_page = self._build_calibration()
        self.history_page = self._build_history_page()
        self.settings_page = self._build_settings()
        for page in (
            self.dashboard_page,
            self.games_page,
            self.run_page,
            self.calibration_page,
            self.history_page,
            self.settings_page,
        ):
            self.stack.addWidget(page)

        self.navigate(0)
        self._refresh_dashboard()
        self._refresh_history()
        self._show_calibration_status()

def navigate(self, index: int) -> None:
        """Switch page and keep sidebar selection synchronized."""
        if not 0 <= index < self.stack.count() and self.stack.count() > 0:
            return
        if self.worker is not None and self.worker.isRunning() and index != 2:
            self.status_bar.showMessage(
                "A run is active. Finish or request cancellation before navigating away."
            )
            return
        self.current_page = index
        if self.stack.count():
            self.stack.setCurrentIndex(index)
        for i, button in enumerate(self.nav_buttons):
            button.setChecked(i == index)
        if index == 4:
            self._refresh_history()
        if index == 3:
            self._show_calibration_status()

    def _configure_game(self, key: str) -> None:
        index = self.game_combo.findData(key)
        if index >= 0:
            self.game_combo.setCurrentIndex(index)
        self.navigate(2)

    def _on_game_changed(self, *_args) -> None:
        key = self.game_combo.currentData()
        if key not in GAME_LABELS:
            return
        self.rounds_spin.setMaximum(MAX_ROUNDS[key])
        self.rounds_spin.setValue(DEFAULT_ROUNDS[key])
        self.game_description.setText(GAME_DESCRIPTIONS[key])
        self.preflight_summary.setText(
            "Run preflight after selecting the game and settings."
        )
        self._clear_preflight_rows()
        self.start_button.setEnabled(False)

    def _read_config(self) -> RunConfig:
        config = RunConfig(
            game=str(self.game_combo.currentData()),
            rounds=self.rounds_spin.value(),
            load_wait=self.load_wait_spin.value(),
            debug=self.debug_checkbox.isChecked(),
            tesseract_cmd=self.settings.value("ocr/tesseract_cmd", "", type=str),
            diagnostics_dir=self.settings.value(
                "diagnostics/directory",
                str(config_directory() / "diagnostics"),
                type=str,
            ),
        )
        validate_run_config(config)
        return config

    def _clear_preflight_rows(self) -> None:
        while self.preflight_rows.count():
            item = self.preflight_rows.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _display_preflight(self, checks: list[PreflightCheck]) -> None:
        self._clear_preflight_rows()
        blocking_ok = can_start_run(checks)
        self.preflight_summary.setText(
            "Critical checks passed. Review the warnings before continuing."
            if blocking_ok
            else "A critical check failed. Fix the blocking issue before starting."
        )
        for check in checks:
            row = QFrame()
            row.setObjectName("Card")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 8, 10, 8)
            status = QLabel(check.status.upper())
            status.setObjectName("StatusPill")
            status.setMinimumWidth(84)
            title_detail = QVBoxLayout()
            name = QLabel(check.name)
            name.setObjectName("CardTitle")
            detail = QLabel(check.detail)
            detail.setWordWrap(True)
            detail.setObjectName("CardDescription")
            title_detail.addWidget(name)
            title_detail.addWidget(detail)
            row_layout.addWidget(status, 0, Qt.AlignmentFlag.AlignTop)
            row_layout.addLayout(title_detail, 1)
            self.preflight_rows.addWidget(row)
        self.start_button.setEnabled(blocking_ok and not self._is_running())
        self.dashboard_readiness.setText(
            "Critical preflight checks passed."
            if blocking_ok
            else "At least one critical preflight check needs attention."
        )

    def _run_preflight(self) -> list[PreflightCheck] | None:
        try:
            config = self._read_config()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid configuration", str(exc))
            return None
        checks = build_preflight(config)
        self._display_preflight(checks)
        self.status_bar.showMessage(
            "Preflight complete"
            if can_start_run(checks)
            else "Preflight blocked: fix critical checks"
        )
        return checks

    def _dashboard_preflight(self) -> None:
        self.navigate(2)
        self._run_preflight()

    def _show_preview(self) -> None:
        try:
            config = self._read_config()
            preview = build_preview(config)
        except ValueError as exc:
            QMessageBox.warning(self, "Cannot create preview", str(exc))
            return
        QMessageBox.information(self, "Preview only", preview)

    def _request_start(self) -> None:
        if self._is_running():
            return
        checks = self._run_preflight()
        if checks is None or not can_start_run(checks):
            QMessageBox.warning(
                self,
                "Preflight failed",
                "Desktop automation is blocked until the critical preflight checks pass. "
                "Review the results and correct the problem first.",
            )
            return
        try:
            config = self._read_config()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid configuration", str(exc))
            return
        dialog = SafetyDialog(GAME_LABELS[config.game], self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self._append_log("info", "Run cancelled before desktop input was enabled.")
            return
        self._start_worker(config)

    def _start_worker(self, config: RunConfig) -> None:
        worker = RunWorker(config, self)
        self.worker = worker
        self.current_config = config
        self.pending_result = None
        self.run_started_at = time.monotonic()
        self.run_status_label.setText("Starting the selected routine…")
        self.run_elapsed_label.setText("Elapsed: 00:00:00")
        self.run_progress.setRange(0, 0)
        self.elapsed_timer.start()
        self._append_log(
            "info", f"Starting {GAME_LABELS[config.game]}. Preflight passed."
        )
        self.start_button.setEnabled(False)
        self.preflight_button.setEnabled(False)
        self.preview_button.setEnabled(False)
        self.game_combo.setEnabled(False)
        self.rounds_spin.setEnabled(False)
        self.load_wait_spin.setEnabled(False)
        self.debug_checkbox.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status_bar.showMessage(
            "Automation is active. Keep the intended game visible."
        )
        worker.log.connect(self._append_log)
        worker.result_ready.connect(self._on_worker_result)
        worker.error.connect(self._on_worker_error)
        worker.cancelled.connect(self._on_worker_cancelled)
        worker.finished.connect(self._on_worker_finished)
        worker.start()

    def _request_cancel(self) -> None:
        if self.worker is None or not self.worker.isRunning():
            return
        self.worker.request_cancel()
        self.cancel_button.setEnabled(False)
        self.preflight_summary.setText(
            "Cancellation requested. The routine will stop at its next safe checkpoint."
        )
        self.run_status_label.setText(
            "Cancellation requested · waiting for a safe checkpoint."
        )
        self._append_log(
            "warning", "Cancellation requested; waiting for a safe checkpoint."
        )
        self.status_bar.showMessage("Cancellation requested…")

    def _on_worker_result(self, result: dict[str, Any]) -> None:
        self.pending_result = result

    def _on_worker_error(self, message: str) -> None:
        self.pending_result = {
            "status": "failed",
            "message": message,
            "elapsed_seconds": round(time.monotonic() - self.run_started_at, 2),
        }

    def _on_worker_cancelled(self, message: str) -> None:
        self.pending_result = {
            "status": "cancelled",
            "message": message,
            "elapsed_seconds": round(time.monotonic() - self.run_started_at, 2),
        }

    def _on_worker_finished(self) -> None:
        config = self.current_config
        result = self.pending_result or {
            "status": "failed",
            "message": "The worker ended without returning a status.",
            "elapsed_seconds": round(time.monotonic() - self.run_started_at, 2),
        }
        if config is not None:
            entry = {
                "game": GAME_LABELS[config.game],
                "rounds": config.rounds,
                **result,
            }
            try:
                self.history.add(entry)
            except (OSError, TypeError, ValueError) as exc:
                self._append_log(
                    "warning",
                    f"Could not save local history: {exc}",
                )
        status = str(result.get("status", "unknown"))
        message = str(result.get("message", "No details were returned."))
        self.elapsed_timer.stop()
        self.run_progress.setRange(0, 100)
        self.run_progress.setValue(0)
        self.run_status_label.setText(f"{status.replace('_', ' ').title()} · {message}")
        self._update_elapsed()
        self._append_log(
            "info" if status == "completed_review" else "warning",
            f"Run status: {status}. {message}",
        )
        self.preflight_summary.setText(f"Last run: {status}. {message}")
        self.status_bar.showMessage(
            f"Run {status.replace('_', ' ')} · review the result before running again."
        )
        worker = self.worker
        self.worker = None
        self.current_config = None
        self.pending_result = None
        if worker is not None:
            worker.deleteLater()
        self.preflight_button.setEnabled(True)
        self.preview_button.setEnabled(True)
        self.game_combo.setEnabled(True)
        self.rounds_spin.setEnabled(True)
        self.load_wait_spin.setEnabled(True)
        self.debug_checkbox.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.start_button.setEnabled(False)
        self._refresh_dashboard()
        self._refresh_history()

    def _update_elapsed(self) -> None:
        """Update real elapsed time without inventing game-round progress."""
        elapsed = max(0, int(time.monotonic() - self.run_started_at))
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.run_elapsed_label.setText(
            f"Elapsed: {hours:02d}:{minutes:02d}:{seconds:02d}"
        )

    def _append_log(self, level: str, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        safe_level = level.upper()
        self.session_log.appendPlainText(f"{timestamp}  [{safe_level}]  {message}")
        self.session_log.ensureCursorVisible()
        if self._is_running():
            self.run_status_label.setText(message)

    def _is_running(self) -> bool:
        return self.worker is not None and self.worker.isRunning()

    def _refresh_dashboard(self) -> None:
        entries = self.history.read()
        if not entries:
            self.dashboard_activity.setText("No runs have been recorded yet.")
        else:
            lines = []
            for entry in reversed(entries[-3:]):
                lines.append(
                    f"{entry.get('game', 'Unknown')} · {entry.get('status', 'unknown')} · "
                    f"{entry.get('elapsed_seconds', 0)}s"
                )
            self.dashboard_activity.setText("\n".join(lines))

    def _refresh_history(self) -> None:
        if not hasattr(self, "history_list"):
            return
        while self.history_list.count():
            item = self.history_list.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        entries = list(reversed(self.history.read()))
        if not entries:
            label = _muted_label(
                "No run history yet. Completed, cancelled, and failed sessions will appear here."
            )
            self.history_list.addWidget(label)
            return
        for entry in entries:
            card = QFrame()
            card.setObjectName("Card")
            row = QHBoxLayout(card)
            row.setContentsMargins(12, 10, 12, 10)
            details = QVBoxLayout()
            game = QLabel(str(entry.get("game", "Unknown game")))
            game.setObjectName("CardTitle")
            timestamp = str(entry.get("timestamp", ""))
            try:
                stamp = (
                    datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    .astimezone()
                    .strftime("%Y-%m-%d %H:%M")
                )
            except ValueError:
                stamp = timestamp
            sub = _muted_label(
                f"{stamp} · limit {entry.get('rounds', 0)} · {entry.get('elapsed_seconds', 0)} seconds"
            )
            details.addWidget(game)
            details.addWidget(sub)
            state = QLabel(
                str(entry.get("status", "unknown")).replace("_", " ").upper()
            )
            state.setObjectName("StatusPill")
            row.addLayout(details, 1)
            row.addWidget(state, 0, Qt.AlignmentFlag.AlignTop)
            self.history_list.addWidget(card)
        self.history_list.addStretch(1)

    def _clear_history(self) -> None:
        reply = QMessageBox.question(
            self,
            "Clear history",
            "Delete the locally stored run history? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.history.clear()
            self._refresh_history()
            self._refresh_dashboard()
            self.status_bar.showMessage("Local history cleared.")

    def _show_calibration_status(self) -> None:
        try:
            profile = load_calibration()
        except CalibrationError as exc:
            self.calibration_status.setText(f"Invalid profile: {exc}")
            return
        if profile is None:
            self.calibration_status.setText(
                "No viewport has been saved. Calibration is required before GUI automation."
            )
            return
        self.calibration_status.setText(
            f"Saved viewport: x={profile.x}, y={profile.y}, width={profile.width}, "
            f"height={profile.height} on {profile.screen_width} × {profile.screen_height}. "
            f"Created {profile.created_at}."
        )

    def _capture_calibration(self) -> None:
        try:
            import pyautogui

            screenshot = pyautogui.screenshot()
            screen_width, screen_height = pyautogui.size()
            image_width, image_height = screenshot.size
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Screen capture unavailable",
                f"Could not capture the screen: {exc}",
            )
            return
        if (screen_width, screen_height) != (image_width, image_height):
            QMessageBox.warning(
                self,
                "Unsupported display scaling",
                "The screenshot dimensions differ from pointer coordinates. "
                "This environment's HiDPI mapping cannot be calibrated safely by this UI.",
            )
            return
        rgb = screenshot.convert("RGB")
        raw = rgb.tobytes()
        image = QImage(
            raw,
            image_width,
            image_height,
            image_width * 3,
            QImage.Format.Format_RGB888,
        ).copy()
        pixmap = QPixmap.fromImage(image)
        pixmap = pixmap.scaled(
            1000,
            620,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        dialog = SelectionDialog(pixmap, QSize(image_width, image_height), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            x, y, width, height = dialog.image_label.selection_in_screen_coordinates()
            profile = save_calibration(
                screen_width=screen_width,
                screen_height=screen_height,
                x=x,
                y=y,
                width=width,
                height=height,
            )
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Could not save calibration", str(exc))
            return
        self._show_calibration_status()
        self.status_bar.showMessage(
            f"Viewport saved: {profile.width} × {profile.height}. Run preflight before automation."
        )
        QMessageBox.information(
            self,
            "Viewport saved",
            "The viewport was saved locally. It guards clicks and screenshot regions, "
            "but does not recalibrate fixed game points. Run preflight and verify that "
            "the reference layout fits inside this region.",
        )

    def _clear_calibration(self) -> None:
        reply = QMessageBox.question(
            self,
            "Clear calibration",
            "Remove the saved viewport? GUI automation will remain blocked until you calibrate again.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        path = calibration_path()
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            QMessageBox.warning(self, "Could not clear calibration", str(exc))
            return
        self._show_calibration_status()
        self.status_bar.showMessage(
            "Calibration cleared; GUI automation is now blocked until recalibrated."
        )

    def _browse_tesseract(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Tesseract executable",
            self.tesseract_edit.text() or str(Path.home()),
            "Executable files (*.exe);;All files (*)",
        )
        if path:
            self.tesseract_edit.setText(path)

    def _test_tesseract(self) -> None:
        from .services import _find_tesseract

        path = _find_tesseract(self.tesseract_edit.text())
        if path:
            QMessageBox.information(
                self, "Tesseract available", f"Executable found:\n{path}"
            )
        else:
            QMessageBox.warning(
                self,
                "Tesseract unavailable",
                "No Tesseract executable was found. Install Tesseract or select its executable path.",
            )

    def _browse_diagnostics(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            "Choose diagnostic directory",
            self.diagnostics_dir_edit.text() or str(config_directory()),
        )
        if directory:
            self.diagnostics_dir_edit.setText(directory)

    def _open_diagnostics(self) -> None:
        import os
        import subprocess
        import sys

        path = Path(self.diagnostics_dir_edit.text()).expanduser()
        try:
            path.mkdir(parents=True, exist_ok=True)
            if sys.platform.startswith("win"):
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except OSError as exc:
            QMessageBox.warning(self, "Could not open folder", str(exc))

    def _save_settings(self) -> None:
        self.settings.setValue("appearance/theme", str(self.theme_combo.currentData()))
        self.settings.setValue("ocr/tesseract_cmd", self.tesseract_edit.text().strip())
        self.settings.setValue(
            "diagnostics/directory", self.diagnostics_dir_edit.text().strip()
        )
        self.settings.setValue("diagnostics/enabled", self.debug_checkbox.isChecked())
        self.settings.setValue("run/load_wait", self.load_wait_spin.value())
        self.settings.sync()
        QApplication.instance().setStyleSheet(
            stylesheet(str(self.theme_combo.currentData()))
        )
        self.status_bar.showMessage("Preferences saved locally.")
        QMessageBox.information(
            self, "Settings saved", "Your preferences were saved locally."
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._is_running():
            self.worker.request_cancel()
            QMessageBox.warning(
                self,
                "Run still active",
                "A cancellation request was sent. Keep the application open until the routine "
                "reaches a safe checkpoint and the run status changes.",
            )
            event.ignore()
            return
        event.accept()
