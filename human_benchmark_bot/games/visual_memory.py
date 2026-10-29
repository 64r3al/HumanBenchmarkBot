"""Experimental Visual Memory routine based on bright-tile detection."""

from __future__ import annotations

import time

import pyautogui
from PIL import Image

from ..automation import open_game, reference_point, reference_region
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
    """Estimate centers of bright tile regions in a screenshot crop.

    This conservative first pass uses color projections instead of clicking
    guessed positions. It can fail when the site's tile colors or layout change;
    an empty result stops the current run.
    """
    rgb = image.convert("RGB")
    width, height = rgb.size
    pixels = list(rgb.getdata())

    def is_bright(pixel: tuple[int, int, int]) -> bool:
        red, green, blue = pixel
        return red >= 245 and green >= 245 and blue >= 245

    column_counts = [
        sum(1 for y in range(height) if is_bright(pixels[y * width + x]))
        for x in range(width)
    ]
    active_columns = [count >= 10 for count in column_counts]
    x_runs = _active_runs(active_columns)

    cells: list[tuple[int, int]] = []
    for x_start, x_end in x_runs:
        tile_width = x_end - x_start + 1
        if tile_width < 20 or tile_width > width * 0.5:
            continue

        row_threshold = max(8, int(tile_width * 0.18))
        row_counts = [
            sum(
                1
                for x in range(x_start, x_end + 1)
                if is_bright(pixels[y * width + x])
            )
            for y in range(height)
        ]
        y_runs = _active_runs([count >= row_threshold for count in row_counts])

        for y_start, y_end in y_runs:
            tile_height = y_end - y_start + 1
            if tile_height < 20 or tile_height > height * 0.85:
                continue
            cells.append(
                (
                    int(round((x_start + x_end) / 2)),
                    int(round((y_start + y_end) / 2)),
                )
            )

    unique: list[tuple[int, int]] = []
    for cell in cells:
        if not any(
            abs(cell[0] - old[0]) < 8 and abs(cell[1] - old[1]) < 8
            for old in unique
        ):
            unique.append(cell)
    return unique


def run(rounds: int = 15, load_wait: int = 5) -> None:
    """Attempt Visual Memory levels using screenshot tile detection."""
    if rounds < 1:
        raise ValueError("rounds must be at least 1.")

    open_game("Visual Memory", GAME_URLS["visual"], load_wait)

    start_point = reference_point(960, 360)
    region = reference_region(596, 280, 700, 445)

    pyautogui.click(*start_point)
    time.sleep(0.8)

    for turn in range(1, rounds + 1):
        screenshot = pyautogui.screenshot(region=region)
        cells = find_highlighted_cells(screenshot)
        if not cells:
            raise RuntimeError(
                "No highlighted cells were detected. Stopping to avoid blind "
                "clicks; the current game layout may require new detection logic."
            )

        # Allow the reveal animation to end before selecting the detected cells.
        time.sleep(0.75)
        left, top, _, _ = region
        for relative_x, relative_y in cells:
            pyautogui.click(left + relative_x, top + relative_y)
            time.sleep(0.04)

        print(
            f"Visual Memory: selected {len(cells)} detected tile(s) "
            f"at level {turn}/{rounds}."
        )
        time.sleep(1.2)

    print("Visual Memory routine finished.")
