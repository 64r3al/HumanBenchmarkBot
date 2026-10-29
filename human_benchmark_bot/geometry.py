"""Pure helpers for scaling coordinates from the reference screen layout."""

from __future__ import annotations

from typing import TypeAlias

Point: TypeAlias = tuple[int, int]
Region: TypeAlias = tuple[int, int, int, int]
Size: TypeAlias = tuple[int, int]


def scaled_point(
    x: float,
    y: float,
    screen_size: Size,
    reference_size: Size = (1920, 1080),
) -> Point:
    """Scale a point from a reference resolution to the current screen size."""
    screen_width, screen_height = screen_size
    reference_width, reference_height = reference_size
    if min(screen_width, screen_height, reference_width, reference_height) <= 0:
        raise ValueError("Screen and reference dimensions must be positive.")
    return (
        int(round(x * screen_width / reference_width)),
        int(round(y * screen_height / reference_height)),
    )


def scaled_region(
    x: float,
    y: float,
    width: float,
    height: float,
    screen_size: Size,
    reference_size: Size = (1920, 1080),
) -> Region:
    """Scale a screenshot region from reference coordinates to screen pixels."""
    if width <= 0 or height <= 0:
        raise ValueError("Region width and height must be positive.")
    left, top = scaled_point(x, y, screen_size, reference_size)
    right, bottom = scaled_point(
        x + width, y + height, screen_size, reference_size
    )
    region_width = right - left
    region_height = bottom - top
    if region_width <= 0 or region_height <= 0:
        raise ValueError("Scaled region must have positive dimensions.")
    return left, top, region_width, region_height
