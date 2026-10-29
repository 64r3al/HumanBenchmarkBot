"""UI-facing services kept independent of Qt widgets."""

from __future__ import annotations

import importlib
import importlib.util
import json
import shutil
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Event
from typing import Any

from ..calibration import (
    CalibrationError,
    calibration_path,
    config_directory,
    load_calibration,
    validate_current_display,
)
from ..config import (
    DEFAULT_LOAD_WAIT,
    DEFAULT_ROUNDS,
    GAME_URLS,
    MAX_LOAD_WAIT,
    MAX_ROUNDS,
)

GAME_MODULES = {
    "reaction": ".games.reaction_time",
    "number": ".games.number_memory",
    "verbal": ".games.verbal_memory",
    "visual": ".games.visual_memory",
}
GAME_LABELS = {
    "reaction": "Reaction Time",
    "number": "Number Memory",
    "verbal": "Verbal Memory",
    "visual": "Visual Memory",
}
GAME_DESCRIPTIONS = {
    "reaction": "Detect a visual signal and interact with the game. Timing is affected by screen detection and automation latency.",
    "number": "Read and submit the displayed number using the configured extraction method.",
    "verbal": "Use Tesseract OCR to read displayed words and classify repeated words.",
    "visual": "Detect highlighted tile patterns and attempt to reproduce them.",
}


@dataclass(frozen=True)
class RunConfig:
    """Validated inputs for one game run."""

    game: str
    rounds: int
    load_wait: int = DEFAULT_LOAD_WAIT
    debug: bool = False
    tesseract_cmd: str = ""


@dataclass(frozen=True)
class PreflightCheck:
    """One readiness result shown in the desktop interface."""

    name: str
    status: str
    detail: str
    blocking: bool = False


def validate_run_config(config: RunConfig) -> None:
    """Validate a GUI configuration against the project's central limits."""
    if config.game not in GAME_MODULES:
        raise ValueError(f"Unsupported game: {config.game!r}.")
    if not 1 <= config.rounds <= MAX_ROUNDS[config.game]:
        raise ValueError(
            f"{GAME_LABELS[config.game]} rounds must be between 1 and "
            f"{MAX_ROUNDS[config.game]}."
        )
    if not 0 <= config.load_wait <= MAX_LOAD_WAIT:
        raise ValueError(f"Browser countdown must be between 0 and {MAX_LOAD_WAIT} seconds.")


def _find_tesseract(custom_path: str = "") -> str | None:
    """Return a usable Tesseract executable path if one can be found."""
    if custom_path.strip():
        candidate = Path(custom_path.strip()).expanduser()
        if candidate.is_file():
            return str(candidate)
        return shutil.which(custom_path.strip())
    return shutil.which("tesseract")


def build_preflight(config: RunConfig) -> list[PreflightCheck]:
    """Run non-invasive readiness checks without starting desktop input."""
    checks: list[PreflightCheck] = []
    try:
        validate_run_config(config)
    except ValueError as exc:
        return [
            PreflightCheck("Run configuration", "failed", str(exc), blocking=True)
        ]

    checks.append(
        PreflightCheck(
            "Run configuration",
            "passed",
            f"{GAME_LABELS[config.game]} · {config.rounds} interaction(s) · "
            f"{config.load_wait}s startup countdown.",
        )
    )

    try:
        import pyautogui

        screen_width, screen_height = pyautogui.size()
        if screen_width <= 0 or screen_height <= 0:
            raise RuntimeError("The operating system returned invalid display dimensions.")
        checks.append(
            PreflightCheck(
                "Display",
                "passed",
                f"Detected {screen_width} × {screen_height} physical screen coordinates.",
            )
        )
    except Exception as exc:
        screen_width = screen_height = 0
        checks.append(
            PreflightCheck(
                "Display",
                "failed",
                f"Could not read the display configuration: {exc}",
                blocking=True,
            )
        )

    try:
        profile = load_calibration()
        if profile is None:
            checks.append(
                PreflightCheck(
                    "Game viewport",
                    "failed",
                    "No viewport is calibrated. Open Calibration, capture the screen, and select the game area.",
                    blocking=True,
                )
            )
        elif screen_width and screen_height:
            validate_current_display(profile, screen_width, screen_height)
            checks.append(
                PreflightCheck(
                    "Game viewport",
                    "passed",
                    f"Saved viewport ({profile.x}, {profile.y}, {profile.width}, {profile.height}) "
                    "matches the current display.",
                )
            )
        else:
            checks.append(
                PreflightCheck(
                    "Game viewport",
                    "failed",
                    "The current display could not be verified against the saved viewport.",
                    blocking=True,
                )
            )
    except CalibrationError as exc:
        checks.append(
            PreflightCheck("Game viewport", "failed", str(exc), blocking=True)
        )

    if config.game == "verbal":
        executable = _find_tesseract(config.tesseract_cmd)
        if executable:
            checks.append(
                PreflightCheck("Tesseract OCR", "passed", f"Executable found at {executable}.")
            )
        else:
            checks.append(
                PreflightCheck(
                    "Tesseract OCR",
                    "failed",
                    "Tesseract is unavailable. Install it or set its executable path in Settings.",
                    blocking=True,
                )
            )

    if config.game == "number":
        try:
            available = importlib.util.find_spec("pyperclip") is not None
        except (ImportError, ValueError):
            available = False
        checks.append(
            PreflightCheck(
                "Clipboard support",
                "passed" if available else "failed",
                (
                    "Clipboard package is installed. Actual access is checked at run time; "
                    "preflight does not read or overwrite clipboard contents."
                    if available
                    else "The required pyperclip package is unavailable."
                ),
                blocking=not available,
            )
        )

    checks.append(
        PreflightCheck(
            "Browser focus",
            "attention",
            "The active browser window cannot be reliably verified on every operating system. "
            "Keep the intended game visible and do not use other desktop applications during a run.",
            blocking=False,
        )
    )
    checks.append(
        PreflightCheck(
            "Experimental routine",
            "attention",
            "Passing preflight does not prove the live website state detector is accurate. "
            "Review the on-screen result after the run.",
            blocking=False,
        )
    )
    return checks


def can_start_run(checks: list[PreflightCheck]) -> bool:
    """Return whether all critical preflight checks passed."""
    return not any(check.blocking and check.status != "passed" for check in checks)


def build_preview(config: RunConfig) -> str:
    """Render a preview without invoking any automation or clipboard APIs."""
    validate_run_config(config)
    return "\n".join(
        [
            "PREVIEW ONLY — no desktop input will be sent.",
            "",
            f"Game: {GAME_LABELS[config.game]}",
            f"URL: {GAME_URLS[config.game]}",
            f"Configured interaction limit: {config.rounds}",
            f"Startup countdown: {config.load_wait} seconds",
            f"Diagnostic screenshots: {'enabled' if config.debug else 'disabled'}",
            "",
            "This is a plan, not a guarantee that the live routine will complete.",
        ]
    )


def run_game(
    config: RunConfig,
    cancel_event: Event,
    log_callback,
) -> dict[str, Any]:
    """Execute one existing routine and return an honest run summary."""
    validate_run_config(config)
    if cancel_event.is_set():
        return {"status": "cancelled", "message": "Cancelled before starting."}

    if config.game == "verbal" and config.tesseract_cmd.strip():
        import pytesseract

        pytesseract.pytesseract.tesseract_cmd = config.tesseract_cmd.strip()

    module = importlib.import_module(GAME_MODULES[config.game], package="human_benchmark_bot")
    log_callback(
        "info",
        f"Starting {GAME_LABELS[config.game]} with a configured limit of {config.rounds}.",
    )
    started = time.monotonic()
    module.run(
        rounds=config.rounds,
        load_wait=config.load_wait,
        debug=config.debug,
        diagnostics_dir=str(config_directory() / "diagnostics"),
        cancel_event=cancel_event,
    )
    elapsed = time.monotonic() - started
    if cancel_event.is_set():
        status = "cancelled"
        message = "Cancellation was requested; the routine returned at a safe checkpoint."
    else:
        status = "completed_review"
        message = (
            "The routine returned without an uncaught error. Verify the game's on-screen "
            "result; this is not proof that the game accepted every interaction."
        )
    log_callback("info", message)
    return {
        "status": status,
        "message": message,
        "elapsed_seconds": round(elapsed, 2),
    }


class HistoryStore:
    """Small local JSON history with bounded retention and atomic writes."""

    def __init__(self, path: Path | None = None, limit: int = 50):
        self.path = path or (config_directory() / "run-history.json")
        self.limit = max(1, limit)

    def read(self) -> list[dict[str, Any]]:
        """Read recent history, ignoring malformed entries safely."""
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(payload, list):
            return []
        return [item for item in payload if isinstance(item, dict)][-self.limit :]

    def add(self, entry: dict[str, Any]) -> None:
        """Append a safe summary without screenshots, clipboard contents, or game answers."""
        rows = self.read()
        safe_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "game": str(entry.get("game", "")),
            "rounds": int(entry.get("rounds", 0)),
            "status": str(entry.get("status", "unknown")),
            "elapsed_seconds": float(entry.get("elapsed_seconds", 0.0)),
            "message": str(entry.get("message", ""))[:300],
        }
        rows.append(safe_entry)
        rows = rows[-self.limit :]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.path)

    def clear(self) -> None:
        """Remove the local run history."""
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
