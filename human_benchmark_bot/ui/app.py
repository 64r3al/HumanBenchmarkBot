"""Desktop application entry point."""

from __future__ import annotations

import sys


def main() -> int:
    """Launch the PySide6 desktop application."""
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print(
            "The desktop UI requires PySide6. Install it with: "
            'python -m pip install -e ".[ui]"',
            file=sys.stderr,
        )
        return 2

    from .main_window import MainWindow
    from .theme import stylesheet

    app = QApplication(sys.argv)
    app.setApplicationName("HumanBenchmarkBot")
    app.setOrganizationName("64r3al")
    app.setStyle("Fusion")
    settings = app_settings()
    theme = settings.value("appearance/theme", "dark", type=str)
    app.setStyleSheet(stylesheet(theme))
    window = MainWindow(settings=settings)
    window.show()
    return app.exec()


def app_settings():
    """Create QSettings lazily so importing this module does not require Qt."""
    from PySide6.QtCore import QSettings

    return QSettings("64r3al", "HumanBenchmarkBot")
