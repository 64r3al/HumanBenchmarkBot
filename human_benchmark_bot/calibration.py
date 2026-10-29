"""Persistent display calibration shared by the GUI and automation layer."""

from __future__ import annotations

import json
import os
import platform
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class CalibrationError(ValueError):
    """Raised when a saved display calibration is invalid or stale."""


@dataclass(frozen=True)
class ScreenCalibration:
    """Calibrated viewport in physical screen coordinates."""

    screen_width: int
    screen_height: int
    x: int
    y: int
    width: int
    height: int
    created_at: str

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    def validate(self) -> None:
        if min(self.screen_width, self.screen_height, self.width, self.height) <= 0:
            raise CalibrationError("Display and viewport dimensions must be positive.")
        if self.x < 0 or self.y < 0:
            raise CalibrationError("The calibrated viewport cannot start outside the display.")
        if self.right > self.screen_width or self.bottom > self.screen_height:
            raise CalibrationError("The calibrated viewport falls outside the display.")


def config_directory() -> Path:
    """Return the user-scoped configuration directory without a Qt dependency."""
    system = platform.system()
    home = Path.home()
    if system == "Windows":
        root = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        return root / "HumanBenchmarkBot"
    if system == "Darwin":
        return home / "Library" / "Application Support" / "HumanBenchmarkBot"
    return Path(os.environ.get("XDG_CONFIG_HOME", home / ".config")) / "human-benchmark-bot"


def calibration_path() -> Path:
    """Return the location of the local calibration file."""
    return config_directory() / "calibration.json"


def load_calibration() -> ScreenCalibration | None:
    """Load a valid calibration, or return None if no profile exists."""
    path = calibration_path()
    if not path.exists():
        return None
    try:
        payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        calibration = ScreenCalibration(
            screen_width=int(payload["screen_width"]),
            screen_height=int(payload["screen_height"]),
            x=int(payload["x"]),
            y=int(payload["y"]),
            width=int(payload["width"]),
            height=int(payload["height"]),
            created_at=str(payload["created_at"]),
        )
        calibration.validate()
        return calibration
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise CalibrationError(
            f"Saved calibration is invalid. Recalibrate from the desktop app. ({exc})"
        ) from exc


def save_calibration(
    *,
    screen_width: int,
    screen_height: int,
    x: int,
    y: int,
    width: int,
    height: int,
) -> ScreenCalibration:
    """Validate and atomically save a calibrated viewport."""
    profile = ScreenCalibration(
        screen_width=screen_width,
        screen_height=screen_height,
        x=x,
        y=y,
        width=width,
        height=height,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    profile.validate()
    destination = calibration_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(asdict(profile), indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)
    return profile


def validate_current_display(
    profile: ScreenCalibration,
    screen_width: int,
    screen_height: int,
) -> None:
    """Reject profiles created for a different screen size."""
    if (profile.screen_width, profile.screen_height) != (screen_width, screen_height):
        raise CalibrationError(
            "The display dimensions differ from the saved calibration. "
            "Recalibrate before running automation."
        )
