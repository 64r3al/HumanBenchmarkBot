"""Main window and pages for the HumanBenchmarkBot desktop UI."""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QSettings, Qt, QRect, QSize, Signal
from PySide6.QtGui import QCloseEvent, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QStatusBar,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QRubberBand,
)

from ..calibration import (
    CalibrationError,
    calibration_path,
    config_directory,
    load_calibration,
    save_calibration,
)
from ..config import DEFAULT_LOAD_WAIT, DEFAULT_ROUNDS, MAX_LOAD_WAIT, MAX_ROUNDS
from .services import (
    GAME_DESCRIPTIONS,
    GAME_LABELS,
    PreflightCheck,
    RunConfig,
    HistoryStore,
    build_preflight,
    build_preview,
    can_start_run,
    validate_run_config,
)
from .theme import stylesheet
from .workers import RunWorker

NAV_ITEMS = [
    ("Dashboard", "Overview"),
    ("Games", "Choose a game"),
    ("Run", "Preview and execute"),
    ("Calibration", "Screen viewport"),
    ("History", "Recent activity"),
    ("Settings", "Preferences"),
]


def _make_card() -> QFrame:
    card = QFrame()
    card.setObjectName("Card")
    return card


def _muted_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("class", "muted")
    label.setWordWrap(True)
    return label


def _button(text: str, *, primary: bool = False, danger: bool = False) -> QPushButton:
    button = QPushButton(text)
    if primary:
        button.setObjectName("PrimaryButton")
    elif danger:
        button.setObjectName("DangerButton")
    return button


class SafetyDialog(QDialog):
    """Explicit warning dialog that requires a checked acknowledgement."""

    def __init__(self, game_label: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Confirm desktop automation")
        self.setModal(True)
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)
        title = QLabel("You are about to enable mouse and keyboard input")
        title.setObjectName("CardTitle")
        layout.addWidget(title)
        explanation = QLabel(
            f"HumanBenchmarkBot is about to run {game_label}. It can control the "
            "active desktop window. It cannot guarantee that the intended browser "
            "tab remains focused.\n\n"
            "Save unsaved work, keep the correct game visible, and do not use other "
            "desktop applications during the run. The routine is experimental; you "
            "must verify its on-screen result. The emergency fail-safe remains enabled."
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        self.acknowledgement = QCheckBox(
            "I understand and want to allow this run to send desktop input."
        )
        layout.addWidget(self.acknowledgement)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = _button("Cancel")
        self.start_button = _button("Start run", primary=True)
        self.start_button.setEnabled(False)
        buttons.addWidget(cancel)
        buttons.addWidget(self.start_button)
        layout.addLayout(buttons)
        self.acknowledgement.toggled.connect(self.start_button.setEnabled)
        cancel.clicked.connect(self.reject)
        self.start_button.clicked.connect(self.accept)


class SelectionLabel(QLabel):
    """Pixmap label allowing a user to select a rectangular viewport."""

    selectionChanged = Signal()

    def __init__(self, pixmap: QPixmap, original_size: QSize, parent: QWidget | None = None):
        super().__init__(parent)
        self.setPixmap(pixmap)
        self.setFixedSize(pixmap.size())
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.original_size = original_size
        self.selection = QRect()
        self._origin = None
        self._rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.position().toPoint()
            self.selection = QRect(self._origin, QSize())
            self._rubber_band.setGeometry(self.selection)
            self._rubber_band.show()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._origin is not None:
            self.selection = QRect(self._origin, event.position().toPoint()).normalized()
            self._rubber_band.setGeometry(self.selection)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._origin is not None:
            self.selection = QRect(self._origin, event.position().toPoint()).normalized()
            self._rubber_band.setGeometry(self.selection)
            self._origin = None
            self.selectionChanged.emit()
        super().mouseReleaseEvent(event)

    def selection_in_screen_coordinates(self) -> tuple[int, int, int, int]:
        """Map the selected display-scaled rectangle to screenshot coordinates."""
        pixmap = self.pixmap()
        if pixmap is None or pixmap.width() <= 0 or pixmap.height() <= 0:
            raise ValueError("No screenshot is available for calibration.")
        rect = self.selection.intersected(self.rect())
        if rect.width() < 80 or rect.height() < 80:
            raise ValueError("Select a game viewport at least 80 × 80 pixels in size.")
        scale_x = self.original_size.width() / pixmap.width()
        scale_y = self.original_size.height() / pixmap.height()
        x = round(rect.x() * scale_x)
        y = round(rect.y() * scale_y)
        width = round(rect.width() * scale_x)
        height = round(rect.height() * scale_y)
        return x, y, width, height


class SelectionDialog(QDialog):
    """Display an explicitly requested screenshot and collect a viewport region."""

    def __init__(self, pixmap: QPixmap, original_size: QSize, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Select the game viewport")
        self.setModal(True)
        layout = QVBoxLayout(self)
        heading = QLabel("Drag a rectangle around the complete game area")
        heading.setObjectName("CardTitle")
        layout.addWidget(heading)
        note = _muted_label(
            "Include all buttons and the entire play area used by this game. "
            "The saved viewport prevents clicks and screenshot regions from leaving "
            "these bounds; it does not automatically recalibrate the game's fixed points."
        )
        layout.addWidget(note)
        self.image_label = SelectionLabel(pixmap, original_size)
        scroll = QScrollArea()
        scroll.setWidget(self.image_label)
        scroll.setWidgetResizable(False)
        layout.addWidget(scroll, 1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = _button("Cancel")
        self.save_button = _button("Save viewport", primary=True)
        self.save_button.setEnabled(False)
        buttons.addWidget(cancel)
        buttons.addWidget(self.save_button)
        layout.addLayout(buttons)
        cancel.clicked.connect(self.reject)
        self.save_button.clicked.connect(self._accept_selection)
        self.image_label.selectionChanged.connect(self._update_save_button)

    def _update_save_button(self) -> None:
        self.save_button.setEnabled(
            self.image_label.selection.width() >= 80
            and self.image_label.selection.height() >= 80
        )

    def _accept_selection(self) -> None:
        try:
            self.image_label.selection_in_screen_coordinates()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid viewport", str(exc))
            return
        self.accept()


class MainWindow(QMainWindow):
    """Main desktop window with dashboard, game configuration, and run controls."""

    def __init__(self, settings: QSettings, parent: QWidget | None = None):
        super().__init__(parent)
        self.settings = settings
        self.history = HistoryStore()
        self.worker: RunWorker | None = None
        self.current_config: RunConfig | None = None
        self.pending_result: dict[str, Any] | None = None
        self.run_started_at = 0.0
        self.current_page = 0

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
            _muted_label("Preview is safe by default. Desktop input always requires confirmation.")
        )
        side_layout.addWidget(safety_card)
        version = QLabel("v0.2.0 · experimental")
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

    def _page(self, title: str, subtitle: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(30, 24, 30, 22)
        outer.setSpacing(16)

        header = QVBoxLayout()
        eyebrow = QLabel("HUMANBENCHMARKBOT  /  DESKTOP")
        eyebrow.setObjectName("Eyebrow")
        page_title = QLabel(title)
        page_title.setObjectName("PageTitle")
        page_subtitle = QLabel(subtitle)
        page_subtitle.setObjectName("PageSubtitle")
        page_subtitle.setWordWrap(True)
        header.addWidget(eyebrow)
        header.addWidget(page_title)
        header.addWidget(page_subtitle)
        outer.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 8, 4)
        content_layout.setSpacing(15)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)
        return page, content_layout

    def _build_dashboard(self) -> QWidget:
        page, layout = self._page(
            "Dashboard",
            "A clear overview of your games, readiness, and recent activity.",
        )
        hero = QFrame()
        hero.setObjectName("HeroCard")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(22, 22, 22, 22)
        hero_text = QVBoxLayout()
        hero_tag = QLabel("READY WHEN YOU ARE")
        hero_tag.setObjectName("Eyebrow")
        hero_title = QLabel("Run your next session with confidence.")
        hero_title.setWordWrap(True)
        hero_title.setStyleSheet("font-size: 23px; font-weight: 750;")
        hero_body = _muted_label(
            "Choose a game, check your setup, preview the plan, and explicitly approve "
            "any action that controls your desktop."
        )
        hero_text.addWidget(hero_tag)
        hero_text.addWidget(hero_title)
        hero_text.addWidget(hero_body)
        hero_layout.addLayout(hero_text, 1)
        hero_actions = QVBoxLayout()
        configure = _button("Configure a run", primary=True)
        preview = _button("Preview a plan")
        configure.clicked.connect(lambda: self.navigate(2))
        preview.clicked.connect(self._show_preview)
        hero_actions.addWidget(configure)
        hero_actions.addWidget(preview)
        hero_actions.addStretch(1)
        hero_layout.addLayout(hero_actions)
        layout.addWidget(hero)

        section_title = QLabel("Your games")
        section_title.setObjectName("CardTitle")
        layout.addWidget(section_title)
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        for index, key in enumerate(GAME_LABELS):
            grid.addWidget(self._game_card(key, "Configure", lambda k=key: self._configure_game(k)), index // 2, index % 2)
        layout.addLayout(grid)

        system_card = _make_card()
        system_layout = QVBoxLayout(system_card)
        system_title = QLabel("System readiness")
        system_title.setObjectName("CardTitle")
        system_layout.addWidget(system_title)
        self.dashboard_readiness = QLabel("Readiness checks run before each session.")
        self.dashboard_readiness.setWordWrap(True)
        system_layout.addWidget(self.dashboard_readiness)
        buttons = QHBoxLayout()
        check_button = _button("Run readiness checks")
        calibrate_button = _button("Calibrate viewport")
        check_button.clicked.connect(self._dashboard_preflight)
        calibrate_button.clicked.connect(lambda: self.navigate(3))
        buttons.addWidget(check_button)
        buttons.addWidget(calibrate_button)
        buttons.addStretch(1)
        system_layout.addLayout(buttons)
        layout.addWidget(system_card)

        activity_card = _make_card()
        activity_layout = QVBoxLayout(activity_card)
        activity_title = QLabel("Recent activity")
        activity_title.setObjectName("CardTitle")
        activity_layout.addWidget(activity_title)
        self.dashboard_activity = QLabel("No runs have been recorded yet.")
        self.dashboard_activity.setWordWrap(True)
        activity_layout.addWidget(self.dashboard_activity)
        history_button = _button("View history")
        history_button.clicked.connect(lambda: self.navigate(4))
        activity_layout.addWidget(history_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(activity_card)
        layout.addStretch(1)
        return page

    def _game_card(self, key: str, action_text: str, action) -> QFrame:
        card = _make_card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        top = QHBoxLayout()
        title = QLabel(GAME_LABELS[key])
        title.setObjectName("CardTitle")
        status = QLabel("EXPERIMENTAL")
        status.setObjectName("StatusPill")
        top.addWidget(title, 1)
        top.addWidget(status)
        card_layout.addLayout(top)
        description = QLabel(GAME_DESCRIPTIONS[key])
        description.setObjectName("CardDescription")
        description.setWordWrap(True)
        card_layout.addWidget(description)
        bottom = QHBoxLayout()
        note = _muted_label(f"Limit: {MAX_ROUNDS[key]} interactions")
        bottom.addWidget(note, 1)
        button = _button(action_text)
        button.clicked.connect(action)
        bottom.addWidget(button)
        card_layout.addLayout(bottom)
        return card

    def _build_games(self) -> QWidget:
        page, layout = self._page(
            "Games",
            "Select a routine. Every game is experimental until it has passed supervised live-browser testing.",
        )
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        for index, key in enumerate(GAME_LABELS):
            grid.addWidget(self._game_card(key, "Configure game", lambda k=key: self._configure_game(k)), index // 2, index % 2)
        layout.addLayout(grid)
        notice = QLabel(
            "Passing automated tests does not prove that the current website layout, "
            "detectors, or game transitions are correct."
        )
        notice.setWordWrap(True)
        notice.setObjectName("StatusPill")
        layout.addWidget(notice)
        layout.addStretch(1)
        return page

    def _build_run_page(self) -> QWidget:
        page, layout = self._page(
            "Configure and run",
            "Preview is non-invasive. Actual desktop automation requires preflight and a separate confirmation.",
        )
        config_card = _make_card()
        config_layout = QVBoxLayout(config_card)
        config_layout.setContentsMargins(18, 18, 18, 18)
        config_title = QLabel("Run configuration")
        config_title.setObjectName("CardTitle")
        config_layout.addWidget(config_title)

        game_row = QHBoxLayout()
        game_row.addWidget(QLabel("Game"))
        self.game_combo = QComboBox()
        for key, label in GAME_LABELS.items():
            self.game_combo.addItem(label, key)
        game_row.addWidget(self.game_combo, 1)
        config_layout.addLayout(game_row)

        self.game_description = _muted_label(GAME_DESCRIPTIONS["reaction"])
        config_layout.addWidget(self.game_description)

        fields = QHBoxLayout()
        rounds_box = QVBoxLayout()
        rounds_box.addWidget(QLabel("Interaction limit"))
        self.rounds_spin = QSpinBox()
        self.rounds_spin.setMinimum(1)
        self.rounds_spin.setMaximum(MAX_ROUNDS["reaction"])
        self.rounds_spin.setValue(DEFAULT_ROUNDS["reaction"])
        rounds_box.addWidget(self.rounds_spin)
        fields.addLayout(rounds_box)
        wait_box = QVBoxLayout()
        wait_box.addWidget(QLabel("Startup countdown (seconds)"))
        self.load_wait_spin = QSpinBox()
        self.load_wait_spin.setRange(0, MAX_LOAD_WAIT)
        self.load_wait_spin.setValue(int(self.settings.value("run/load_wait", DEFAULT_LOAD_WAIT)))
        wait_box.addWidget(self.load_wait_spin)
        fields.addLayout(wait_box)
        fields.addStretch(1)
        config_layout.addLayout(fields)

        self.debug_checkbox = QCheckBox("Save a diagnostic screenshot when a supported detection failure occurs")
        self.debug_checkbox.setChecked(self.settings.value("diagnostics/enabled", False, type=bool))
        config_layout.addWidget(self.debug_checkbox)

        actions = QHBoxLayout()
        self.preflight_button = _button("Run preflight")
        self.preview_button = _button("Preview only")
        self.start_button = _button("Start desktop automation", primary=True)
        self.cancel_button = _button("Request stop", danger=True)
        self.cancel_button.setEnabled(False)
        actions.addWidget(self.preflight_button)
        actions.addWidget(self.preview_button)
        actions.addWidget(self.start_button)
        actions.addWidget(self.cancel_button)
        self.start_button.setEnabled(False)
        config_layout.addLayout(actions)
        layout.addWidget(config_card)

        preflight_card = _make_card()
        preflight_layout = QVBoxLayout(preflight_card)
        preflight_layout.setContentsMargins(18, 18, 18, 18)
        preflight_title = QLabel("Preflight results")
        preflight_title.setObjectName("CardTitle")
        preflight_layout.addWidget(preflight_title)
        self.preflight_summary = QLabel("Run preflight before enabling desktop input.")
        self.preflight_summary.setWordWrap(True)
        preflight_layout.addWidget(self.preflight_summary)
        self.preflight_rows = QVBoxLayout()
        preflight_layout.addLayout(self.preflight_rows)
        layout.addWidget(preflight_card)

        log_card = _make_card()
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(18, 18, 18, 18)
        log_head = QHBoxLayout()
        log_title = QLabel("Session log")
        log_title.setObjectName("CardTitle")
        clear_button = _button("Clear log")
        clear_button.clicked.connect(lambda: self.session_log.clear())
        log_head.addWidget(log_title, 1)
        log_head.addWidget(clear_button)
        log_layout.addLayout(log_head)
        self.session_log = QPlainTextEdit()
        self.session_log.setReadOnly(True)
        self.session_log.setMaximumBlockCount(500)
        self.session_log.setPlaceholderText("Run messages and actionable errors will appear here.")
        self.session_log.setMinimumHeight(180)
        log_layout.addWidget(self.session_log)
        layout.addWidget(log_card)
        layout.addStretch(1)

        self.game_combo.currentIndexChanged.connect(self._on_game_changed)
        self.preflight_button.clicked.connect(self._run_preflight)
        self.preview_button.clicked.connect(self._show_preview)
        self.start_button.clicked.connect(self._request_start)
        self.cancel_button.clicked.connect(self._request_cancel)
        self._on_game_changed()
        return page

    def _build_calibration(self) -> QWidget:
        page, layout = self._page(
            "Calibration",
            "Define a viewport guard for the game area. The current routines still use their experimental reference coordinates.",
        )
        card = _make_card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        title = QLabel("Game viewport")
        title.setObjectName("CardTitle")
        card_layout.addWidget(title)
        card_layout.addWidget(
            _muted_label(
                "Capture is performed only after you click the button below. Select a rectangle "
                "that contains every required game button and screenshot region. The saved bounds "
                "reject clicks or captures outside that area; they do not automatically correct "
                "browser zoom, offsets, or the game's fixed reference points."
            )
        )
        self.calibration_status = QLabel("No viewport has been saved.")
        self.calibration_status.setWordWrap(True)
        self.calibration_status.setObjectName("StatusPill")
        card_layout.addWidget(self.calibration_status)
        buttons = QHBoxLayout()
        capture = _button("Capture screen and select viewport", primary=True)
        reset = _button("Clear calibration", danger=True)
        capture.clicked.connect(self._capture_calibration)
        reset.clicked.connect(self._clear_calibration)
        buttons.addWidget(capture)
        buttons.addWidget(reset)
        buttons.addStretch(1)
        card_layout.addLayout(buttons)
        layout.addWidget(card)
        warning_card = _make_card()
        warning_layout = QVBoxLayout(warning_card)
        warning_layout.setContentsMargins(18, 18, 18, 18)
        warning_title = QLabel("Before running")
        warning_title.setObjectName("CardTitle")
        warning_layout.addWidget(warning_title)
        warning_layout.addWidget(
            _muted_label(
                "Keep the browser zoom and display configuration stable. If screen dimensions "
                "change, the saved profile becomes invalid and preflight will require recalibration. "
                "Do not continue if the reference game points do not fall inside your selected viewport."
            )
        )
        layout.addWidget(warning_card)
        layout.addStretch(1)
        return page

    def _build_history_page(self) -> QWidget:
        page, layout = self._page(
            "History",
            "A local record of recent sessions. No scores or answers are inferred or fabricated.",
        )
        card = _make_card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        header = QHBoxLayout()
        title = QLabel("Recent sessions")
        title.setObjectName("CardTitle")
        clear = _button("Clear history", danger=True)
        clear.clicked.connect(self._clear_history)
        header.addWidget(title, 1)
        header.addWidget(clear)
        card_layout.addLayout(header)
        self.history_list = QVBoxLayout()
        card_layout.addLayout(self.history_list)
        layout.addWidget(card)
        layout.addStretch(1)
        return page

    def _build_settings(self) -> QWidget:
        page, layout = self._page(
            "Settings",
            "Local preferences and optional dependencies.",
        )
        appearance_card = _make_card()
        appearance_layout = QVBoxLayout(appearance_card)
        appearance_layout.setContentsMargins(18, 18, 18, 18)
        appearance_title = QLabel("Appearance")
        appearance_title.setObjectName("CardTitle")
        appearance_layout.addWidget(appearance_title)
        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("Theme"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Dark", "dark")
        self.theme_combo.addItem("Light", "light")
        current_theme = self.settings.value("appearance/theme", "dark", type=str)
        theme_index = self.theme_combo.findData(current_theme)
        self.theme_combo.setCurrentIndex(max(0, theme_index))
        theme_row.addWidget(self.theme_combo, 1)
        appearance_layout.addLayout(theme_row)
        layout.addWidget(appearance_card)

        ocr_card = _make_card()
        ocr_layout = QVBoxLayout(ocr_card)
        ocr_layout.setContentsMargins(18, 18, 18, 18)
        ocr_title = QLabel("OCR")
        ocr_title.setObjectName("CardTitle")
        ocr_layout.addWidget(ocr_title)
        ocr_layout.addWidget(_muted_label("Required for Verbal Memory only. Leave blank to use Tesseract from PATH."))
        path_row = QHBoxLayout()
        self.tesseract_edit = QLineEdit(self.settings.value("ocr/tesseract_cmd", "", type=str))
        self.tesseract_edit.setPlaceholderText("Path to tesseract.exe (optional)")
        browse = _button("Browse")
        test = _button("Check availability")
        browse.clicked.connect(self._browse_tesseract)
        test.clicked.connect(self._test_tesseract)
        path_row.addWidget(self.tesseract_edit, 1)
        path_row.addWidget(browse)
        path_row.addWidget(test)
        ocr_layout.addLayout(path_row)
        layout.addWidget(ocr_card)

        diagnostics_card = _make_card()
        diagnostics_layout = QVBoxLayout(diagnostics_card)
        diagnostics_layout.setContentsMargins(18, 18, 18, 18)
        diagnostics_title = QLabel("Diagnostics")
        diagnostics_title.setObjectName("CardTitle")
        diagnostics_layout.addWidget(diagnostics_title)
        diagnostics_layout.addWidget(
            _muted_label("Screenshots may contain other desktop content. They are local and disabled unless explicitly enabled.")
        )
        directory_row = QHBoxLayout()
        self.diagnostics_dir_edit = QLineEdit(
            self.settings.value("diagnostics/directory", str(config_directory() / "diagnostics"), type=str)
        )
        browse_dir = _button("Choose folder")
        open_dir = _button("Open folder")
        browse_dir.clicked.connect(self._browse_diagnostics)
        open_dir.clicked.connect(self._open_diagnostics)
        directory_row.addWidget(self.diagnostics_dir_edit, 1)
        directory_row.addWidget(browse_dir)
        directory_row.addWidget(open_dir)
        diagnostics_layout.addLayout(directory_row)
        layout.addWidget(diagnostics_card)

        save_row = QHBoxLayout()
        save_row.addStretch(1)
        save = _button("Save preferences", primary=True)
        save.clicked.connect(self._save_settings)
        save_row.addWidget(save)
        layout.addLayout(save_row)
        layout.addStretch(1)
        return page

    def navigate(self, index: int) -> None:
        """Switch page and keep sidebar selection synchronized."""
        if not 0 <= index < self.stack.count() and self.stack.count() > 0:
            return
        if self.worker is not None and self.worker.isRunning() and index != 2:
            self.status_bar.showMessage("A run is active. Finish or request cancellation before navigating away.")
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
        self.preflight_summary.setText("Run preflight after selecting the game and settings.")
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
                "diagnostics/directory", str(config_directory() / "diagnostics"), type=str
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
            "Critical preflight checks passed." if blocking_ok else "At least one critical preflight check needs attention."
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
            "Preflight complete" if can_start_run(checks) else "Preflight blocked: fix critical checks"
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
        self._append_log("info", f"Starting {GAME_LABELS[config.game]}. Preflight passed.")
        self.start_button.setEnabled(False)
        self.preflight_button.setEnabled(False)
        self.preview_button.setEnabled(False)
        self.game_combo.setEnabled(False)
        self.rounds_spin.setEnabled(False)
        self.load_wait_spin.setEnabled(False)
        self.debug_checkbox.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status_bar.showMessage("Automation is active. Keep the intended game visible.")
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
        self._append_log("warning", "Cancellation requested; waiting for a safe checkpoint.")
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
            self.history.add(entry)
        status = str(result.get("status", "unknown"))
        message = str(result.get("message", "No details were returned."))
        self._append_log("info" if status == "completed_review" else "warning", f"Run status: {status}. {message}")
        self.preflight_summary.setText(f"Last run: {status}. {message}")
        self.status_bar.showMessage(f"Run {status.replace('_', ' ')} · review the result before running again.")
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

    def _append_log(self, level: str, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        safe_level = level.upper()
        self.session_log.appendPlainText(f"{timestamp}  [{safe_level}]  {message}")
        self.session_log.ensureCursorVisible()

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
            label = _muted_label("No run history yet. Completed, cancelled, and failed sessions will appear here.")
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
                stamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d %H:%M")
            except ValueError:
                stamp = timestamp
            sub = _muted_label(
                f"{stamp} · limit {entry.get('rounds', 0)} · {entry.get('elapsed_seconds', 0)} seconds"
            )
            details.addWidget(game)
            details.addWidget(sub)
            state = QLabel(str(entry.get("status", "unknown")).replace("_", " ").upper())
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
            self.calibration_status.setText("No viewport has been saved. Calibration is required before GUI automation.")
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
        path = calibration_path()
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            QMessageBox.warning(self, "Could not clear calibration", str(exc))
            return
        self._show_calibration_status()
        self.status_bar.showMessage("Calibration cleared; GUI automation is now blocked until recalibrated.")

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
            QMessageBox.information(self, "Tesseract available", f"Executable found:\n{path}")
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
        path.mkdir(parents=True, exist_ok=True)
        try:
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
        self.settings.setValue("diagnostics/directory", self.diagnostics_dir_edit.text().strip())
        self.settings.setValue("diagnostics/enabled", self.debug_checkbox.isChecked())
        self.settings.setValue("run/load_wait", self.load_wait_spin.value())
        self.settings.sync()
        QApplication.instance().setStyleSheet(stylesheet(str(self.theme_combo.currentData())))
        self.status_bar.showMessage("Preferences saved locally.")
        QMessageBox.information(self, "Settings saved", "Your preferences were saved locally.")

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
