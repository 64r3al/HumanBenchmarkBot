"""Safety and viewport-selection dialogs used by the desktop interface."""

from __future__ import annotations

from PySide6.QtCore import Qt, QRect, QSize, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRubberBand,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .pages import _muted_label


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

    def __init__(
        self, pixmap: QPixmap, original_size: QSize, parent: QWidget | None = None
    ):
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
            self.selection = QRect(
                self._origin, event.position().toPoint()
            ).normalized()
            self._rubber_band.setGeometry(self.selection)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._origin is not None:
            self.selection = QRect(
                self._origin, event.position().toPoint()
            ).normalized()
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

    def __init__(
        self, pixmap: QPixmap, original_size: QSize, parent: QWidget | None = None
    ):
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
