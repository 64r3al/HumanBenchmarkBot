"""Offscreen smoke tests for the optional Qt desktop interface."""

from __future__ import annotations

import pytest

from PySide6.QtCore import QRect, QSize, QSettings
from PySide6.QtWidgets import QApplication, QMessageBox

from human_benchmark_bot.ui.dialogs import SafetyDialog, SelectionLabel
from human_benchmark_bot.ui.main_window import MainWindow


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


def test_main_window_starts_without_enabling_desktop_input(qt_app, tmp_path) -> None:
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow(settings=settings)
    assert window.windowTitle() == "HumanBenchmarkBot"
    assert window.stack.currentIndex() == 0
    assert window.start_button.isEnabled() is False
    assert window.preview_button.isEnabled() is True
    assert window.cancel_button.isEnabled() is False
    window.close()


def test_sidebar_navigation_switches_pages(qt_app, tmp_path) -> None:
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow(settings=settings)
    window.navigate(1)
    assert window.stack.currentIndex() == 1
    assert window.nav_buttons[1].isChecked()
    window.navigate(3)
    assert window.stack.currentIndex() == 3
    assert window.nav_buttons[3].isChecked()
    window.close()


def test_safety_dialog_requires_explicit_acknowledgement(qt_app) -> None:
    dialog = SafetyDialog("Reaction Time")

    assert dialog.start_button.isEnabled() is False
    dialog.acknowledgement.setChecked(True)
    assert dialog.start_button.isEnabled() is True
    dialog.acknowledgement.setChecked(False)
    assert dialog.start_button.isEnabled() is False
    dialog.close()


def test_calibration_selection_maps_preview_pixels_to_screen_coordinates(
    qt_app,
) -> None:
    from PySide6.QtGui import QPixmap

    label = SelectionLabel(QPixmap(500, 250), QSize(1000, 500))
    label.selection = QRect(50, 25, 300, 150)

    assert label.selection_in_screen_coordinates() == (100, 50, 600, 300)



def test_calibration_capture_hides_app_before_screenshot(
    qt_app, tmp_path, monkeypatch
) -> None:
    from human_benchmark_bot.ui import main_window as main_window_module

    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow(settings=settings)
    window.show()

    scheduled: list[tuple[int, object]] = []
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )
    monkeypatch.setattr(
        main_window_module.QTimer,
        "singleShot",
        lambda delay, callback: scheduled.append((delay, callback)),
    )

    window._capture_calibration()

    assert window.isHidden()
    assert scheduled and scheduled[0][0] == 3000
    window.show()
    window.close()


def test_calibration_capture_can_be_cancelled_without_hiding_app(
    qt_app, tmp_path, monkeypatch
) -> None:
    from human_benchmark_bot.ui import main_window as main_window_module

    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow(settings=settings)
    window.show()

    scheduled: list[tuple[int, object]] = []
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.No,
    )
    monkeypatch.setattr(
        main_window_module.QTimer,
        "singleShot",
        lambda delay, callback: scheduled.append((delay, callback)),
    )

    window._capture_calibration()

    assert window.isVisible()
    assert scheduled == []
    window.close()
