"""Experimental Visual Memory routine with bounded tile-detection waits."""

from __future__ import annotations

import time
from threading import Event

import pyautogui
from PIL import Image

from ..automation import (
    AutomationError,
    DetectionTimeout,
    check_cancelled,
    click_point,
    emit_log,
    LogCallback,
    interruptible_sleep,
    open_game,
    reference_point,
    reference_region,
    save_diagnostic_screenshot,
)
from ..config import GAME_URLS


def _active_runs(active: list[bool], max_gap: int = 2) -> list[tuple[int, int]]:
    """Group nearby active indices into inclusive runs."""
    indices = [index for index, value in enumerate(active) if value]
    if not indices:
        return []

    runs: list[tuple[int, int]] = []
    start = previous = indices[0]
    for index in indices[1:]:
        if index - previous <= max_gap + 1:
            previous = index
        else:
            runs.append((start, previous))
            start = previous = index
    runs.append((start, previous))
    return runs


def find_highlighted_cells(image: Image.Image) -> list[tuple[int, int]]:
    """Estimate highlighted tile centers from bright rectangular regions.

    The result contains centers relative to the supplied screenshot crop. This
    heuristic is experimental; the live site's tile rendering may need recalibration.
    """
    if image.width < 1 or image.height < 1:
        return []

    rgb = image.convert("RGB")
    pixels = rgb.load()
    width, height = rgb.size

    def is_bright(pixel: tuple[int, int, int]) -> bool:
        red, green, blue = pixel
        return red >= 245 and green >= 245 and blue >= 245

    min_column_pixels = max(10, int(height * 0.025))
    column_counts = [
        sum(1 for y in range(height) if is_bright(pixels[x, y])) for x in range(width)
    ]
    x_runs = _active_runs(
        [count >= min_column_pixels for count in column_counts],
        max_gap=2,
    )

    cells: list[tuple[int, int]] = []
    for x_start, x_end in x_runs:
        tile_width = x_end - x_start + 1
        if tile_width < 20 or tile_width > width * 0.5:
            continue

        row_threshold = max(8, int(tile_width * 0.18))
        row_counts = [
            sum(1 for x in range(x_start, x_end + 1) if is_bright(pixels[x, y]))
            for y in range(height)
        ]
        y_runs = _active_runs(
            [count >= row_threshold for count in row_counts],
            max_gap=2,
        )

        for y_start, y_end in y_runs:
            tile_height = y_end - y_start + 1
            if tile_height < 20 or tile_height > height * 0.85:
                continue
            cells.append(
                (
                    (x_start + x_end) // 2,
                    (y_start + y_end) // 2,
                )
            )

    unique: list[tuple[int, int]] = []
    for cell in cells:
        if not any(
            abs(cell[0] - old[0]) < 8 and abs(cell[1] - old[1]) < 8 for old in unique
        ):
            unique.append(cell)
    return unique


def _wait_for_cells(
    region: tuple[int, int, int, int],
    *,
    should_be_visible: bool,
    timeout: float,
    cancel_event: Event | None = None,
) -> list[tuple[int, int]]:
    """Wait for highlighted tiles to appear or to disappear stably.

    When waiting for disappearance, return the last non-empty pattern observed
    before three consecutive blank frames. This captures the latest revealed
    pattern instead of reusing only the first partial frame.
    """
    if timeout <= 0:
        raise ValueError("timeout must be positive.")

    deadline = time.monotonic() + timeout
    last_cells: list[tuple[int, int]] = []
    empty_frames = 0
    while time.monotonic() < deadline:
        check_cancelled(cancel_event)
        screenshot = pyautogui.screenshot(region=region)
        cells = find_highlighted_cells(screenshot)
        if should_be_visible and cells:
            return cells
        if cells:
            last_cells = cells
            empty_frames = 0
        else:
            empty_frames += 1
            if not should_be_visible and empty_frames >= 3:
                return last_cells
        interruptible_sleep(0.05, cancel_event)

    state = "appear" if should_be_visible else "disappear"
    raise DetectionTimeout(
        f"Highlighted tiles did not {state} within {timeout:.1f} seconds."
    )


def run(
    rounds: int = 15,
    load_wait: int = 5,
    *,
    debug: bool = False,
    diagnostics_dir: str = "diagnostics",
    cancel_event: Event | None = None,
    log_callback: LogCallback | None = None,
) -> None:
    """Replay detected tile patterns; abort when a visual transition is uncertain."""
    if rounds < 1:
        raise ValueError("rounds must be at least 1.")

    open_game(
        "Visual Memory",
        GAME_URLS["visual"],
        load_wait,
        cancel_event=cancel_event,
        log_callback=log_callback,
    )
    start_point = reference_point(960, 360)
    region = reference_region(596, 280, 700, 445)
    left, top, _, _ = region

    click_point(start_point, cancel_event=cancel_event)
    interruptible_sleep(0.3, cancel_event)

    for turn in range(1, rounds + 1):
        try:
            _wait_for_cells(
                region,
                should_be_visible=True,
                timeout=8,
                cancel_event=cancel_event,
            )
            # Capture the latest visible pattern after the reveal has actually ended.
            cells = _wait_for_cells(
                region,
                should_be_visible=False,
                timeout=8,
                cancel_event=cancel_event,
            )
        except DetectionTimeout:
            save_diagnostic_screenshot(
                "visual-pattern-transition-failed",
                enabled=debug,
                directory=diagnostics_dir,
                log_callback=log_callback,
            )
            raise

        if not cells:
            raise AutomationError(
                "No highlighted tiles were detected before the reveal disappeared. "
                "Stopping safely instead of guessing."
            )

        for relative_x, relative_y in cells:
            check_cancelled(cancel_event)
            click_point(
                (left + relative_x, top + relative_y), cancel_event=cancel_event
            )
            interruptible_sleep(0.05, cancel_event)

        emit_log(
            f"Visual Memory: selected {len(cells)} detected tile(s) "
            f"at level {turn}/{rounds}.",
            log_callback,
        )

        if turn < rounds:
            # Require a blank transition before accepting another pattern.
            try:
                _wait_for_cells(
                    region,
                    should_be_visible=False,
                    timeout=5,
                    cancel_event=cancel_event,
                )
            except DetectionTimeout:
                save_diagnostic_screenshot(
                    "visual-post-click-transition-failed",
                    enabled=debug,
                    directory=diagnostics_dir,
                    log_callback=log_callback,
                )
                raise

    emit_log(
        "Visual Memory routine reached its configured level limit. Verify the "
        "on-screen result; layout changes may require detector recalibration.",
        log_callback,
    )
