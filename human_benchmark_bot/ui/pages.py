"""Composable page builders for the HumanBenchmarkBot desktop interface."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..calibration import config_directory
from ..config import DEFAULT_LOAD_WAIT, DEFAULT_ROUNDS, MAX_LOAD_WAIT, MAX_ROUNDS
from .services import GAME_DESCRIPTIONS, GAME_LABELS

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


class MainWindowPages:
    """Mixin containing independent builders for the six main application pages."""

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
            grid.addWidget(
                self._game_card(
                    key, "Configure", lambda k=key: self._configure_game(k)
                ),
                index // 2,
                index % 2,
            )
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
            grid.addWidget(
                self._game_card(
                    key, "Configure game", lambda k=key: self._configure_game(k)
                ),
                index // 2,
                index % 2,
            )
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
        self.load_wait_spin.setValue(
            int(self.settings.value("run/load_wait", DEFAULT_LOAD_WAIT))
        )
        wait_box.addWidget(self.load_wait_spin)
        fields.addLayout(wait_box)
        fields.addStretch(1)
        config_layout.addLayout(fields)

        self.debug_checkbox = QCheckBox(
            "Save a diagnostic screenshot when a supported detection failure occurs"
        )
        self.debug_checkbox.setChecked(
            self.settings.value("diagnostics/enabled", False, type=bool)
        )
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

        activity_card = _make_card()
        activity_layout = QVBoxLayout(activity_card)
        activity_layout.setContentsMargins(18, 18, 18, 18)
        activity_title = QLabel("Run activity")
        activity_title.setObjectName("CardTitle")
        activity_layout.addWidget(activity_title)
        self.run_status_label = QLabel("Idle · No automation is running.")
        self.run_status_label.setWordWrap(True)
        self.run_status_label.setObjectName("CardDescription")
        activity_layout.addWidget(self.run_status_label)
        self.run_progress = QProgressBar()
        self.run_progress.setRange(0, 100)
        self.run_progress.setValue(0)
        activity_layout.addWidget(self.run_progress)
        self.run_elapsed_label = _muted_label("Elapsed: 00:00:00")
        activity_layout.addWidget(self.run_elapsed_label)
        layout.addWidget(activity_card)

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
        self.session_log.setPlaceholderText(
            "Run messages and actionable errors will appear here."
        )
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
        ocr_layout.addWidget(
            _muted_label(
                "Required for Verbal Memory only. Leave blank to use Tesseract from PATH."
            )
        )
        path_row = QHBoxLayout()
        self.tesseract_edit = QLineEdit(
            self.settings.value("ocr/tesseract_cmd", "", type=str)
        )
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
            _muted_label(
                "Screenshots may contain other desktop content. They are local and disabled unless explicitly enabled."
            )
        )
        directory_row = QHBoxLayout()
        self.diagnostics_dir_edit = QLineEdit(
            self.settings.value(
                "diagnostics/directory",
                str(config_directory() / "diagnostics"),
                type=str,
            )
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
