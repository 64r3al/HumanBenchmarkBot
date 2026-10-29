"""Consistent dark and light themes for the HumanBenchmarkBot desktop app."""

DARK_QSS = """
QMainWindow, QWidget {
    background: #111318;
    color: #F3F5F8;
    font-size: 13px;
}
QWidget#Sidebar {
    background: #151820;
    border-right: 1px solid #303644;
}
QLabel#BrandMark {
    background: #5B8DEF;
    color: #FFFFFF;
    border-radius: 10px;
    font-size: 17px;
    font-weight: 800;
}
QLabel#BrandTitle { font-size: 15px; font-weight: 700; }
QLabel#BrandSubtitle { color: #A3ACBA; font-size: 11px; }
QLabel#PageTitle { font-size: 25px; font-weight: 750; }
QLabel#PageSubtitle { color: #A3ACBA; font-size: 13px; }
QLabel#Eyebrow { color: #7EA5F5; font-size: 10px; font-weight: 800; letter-spacing: 1px; }
QFrame#Card, QFrame.Card {
    background: #1B1F28;
    border: 1px solid #303644;
    border-radius: 12px;
}
QFrame#HeroCard {
    background: #1B2230;
    border: 1px solid #354563;
    border-radius: 16px;
}
QLabel#CardTitle { font-size: 15px; font-weight: 700; }
QLabel#CardDescription, QLabel.muted { color: #A3ACBA; }
QLabel#StatusPill {
    background: #252B37;
    border: 1px solid #3A4352;
    border-radius: 9px;
    padding: 4px 8px;
    color: #CDD5E2;
    font-size: 11px;
}
QPushButton {
    background: #252B37;
    border: 1px solid #394252;
    border-radius: 8px;
    padding: 9px 13px;
    color: #F3F5F8;
    font-weight: 600;
}
QPushButton:hover { background: #303847; border-color: #56637A; }
QPushButton:pressed { background: #202631; }
QPushButton:disabled { color: #6F7785; background: #1C2028; border-color: #292E38; }
QPushButton#PrimaryButton {
    background: #5B8DEF;
    color: #FFFFFF;
    border-color: #5B8DEF;
}
QPushButton#PrimaryButton:hover { background: #6C9AF3; }
QPushButton#DangerButton { background: #702D36; border-color: #9B3B48; }
QPushButton#DangerButton:hover { background: #8D3340; }
QPushButton#NavButton {
    text-align: left;
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 11px 13px;
    color: #A3ACBA;
    font-weight: 600;
}
QPushButton#NavButton:hover { background: #202530; color: #F3F5F8; }
QPushButton#NavButton:checked {
    background: #24334D;
    color: #FFFFFF;
    border-left: 3px solid #5B8DEF;
    padding-left: 10px;
}
QLineEdit, QSpinBox, QComboBox, QPlainTextEdit, QTextEdit {
    background: #151820;
    border: 1px solid #394252;
    border-radius: 7px;
    padding: 8px;
    selection-background-color: #5B8DEF;
}
QComboBox QAbstractItemView {
    background: #1B1F28;
    color: #F3F5F8;
    selection-background-color: #30466C;
}
QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 16px; height: 16px; }
QProgressBar {
    background: #252B37;
    border: none;
    border-radius: 5px;
    min-height: 8px;
    max-height: 8px;
    text-visible: false;
}
QProgressBar::chunk { background: #5B8DEF; border-radius: 5px; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: #151820; width: 9px; margin: 2px; }
QScrollBar::handle:vertical { background: #394252; border-radius: 4px; min-height: 25px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QStatusBar { background: #151820; color: #A3ACBA; border-top: 1px solid #303644; }
QDialog { background: #151820; }
QToolTip { background: #252B37; color: #F3F5F8; border: 1px solid #56637A; padding: 5px; }
"""

LIGHT_QSS = """
QMainWindow, QWidget {
    background: #F4F6FA;
    color: #202938;
    font-size: 13px;
}
QWidget#Sidebar { background: #FFFFFF; border-right: 1px solid #DDE2EB; }
QLabel#BrandMark { background: #356DD5; color: #FFFFFF; border-radius: 10px; font-size: 17px; font-weight: 800; }
QLabel#BrandTitle { font-size: 15px; font-weight: 700; }
QLabel#BrandSubtitle, QLabel#PageSubtitle, QLabel.muted { color: #647084; }
QLabel#PageTitle { font-size: 25px; font-weight: 750; }
QLabel#Eyebrow { color: #356DD5; font-size: 10px; font-weight: 800; letter-spacing: 1px; }
QFrame#Card, QFrame.Card { background: #FFFFFF; border: 1px solid #DDE2EB; border-radius: 12px; }
QFrame#HeroCard { background: #EAF0FC; border: 1px solid #C7D7F5; border-radius: 16px; }
QLabel#CardTitle { font-size: 15px; font-weight: 700; }
QLabel#CardDescription { color: #647084; }
QLabel#StatusPill { background: #EDF0F6; border: 1px solid #DDE2EB; border-radius: 9px; padding: 4px 8px; color: #475467; font-size: 11px; }
QPushButton { background: #FFFFFF; border: 1px solid #D5DCE7; border-radius: 8px; padding: 9px 13px; color: #202938; font-weight: 600; }
QPushButton:hover { background: #F1F4F9; border-color: #A7B6CC; }
QPushButton:disabled { color: #9AA3B2; background: #F0F2F6; }
QPushButton#PrimaryButton { background: #356DD5; color: #FFFFFF; border-color: #356DD5; }
QPushButton#PrimaryButton:hover { background: #285DC1; }
QPushButton#DangerButton { background: #FDEBED; border-color: #F3B9C0; color: #9D2937; }
QPushButton#NavButton { text-align: left; background: transparent; border: none; border-radius: 8px; padding: 11px 13px; color: #647084; font-weight: 600; }
QPushButton#NavButton:hover { background: #F1F4F9; color: #202938; }
QPushButton#NavButton:checked { background: #E5EDFC; color: #244F9B; border-left: 3px solid #356DD5; padding-left: 10px; }
QLineEdit, QSpinBox, QComboBox, QPlainTextEdit, QTextEdit { background: #FFFFFF; border: 1px solid #D5DCE7; border-radius: 7px; padding: 8px; selection-background-color: #356DD5; }
QComboBox QAbstractItemView { background: #FFFFFF; color: #202938; selection-background-color: #E5EDFC; }
QProgressBar { background: #DDE2EB; border: none; border-radius: 5px; min-height: 8px; max-height: 8px; text-visible: false; }
QProgressBar::chunk { background: #356DD5; border-radius: 5px; }
QScrollArea { border: none; background: transparent; }
QStatusBar { background: #FFFFFF; color: #647084; border-top: 1px solid #DDE2EB; }
QDialog { background: #FFFFFF; }
QToolTip { background: #FFFFFF; color: #202938; border: 1px solid #D5DCE7; padding: 5px; }
"""


def stylesheet(theme: str) -> str:
    """Return the stylesheet for a known theme, defaulting to dark."""
    return LIGHT_QSS if theme.casefold() == "light" else DARK_QSS
