"""Tests for pure geometry helpers (no desktop session required)."""

import pytest

from human_benchmark_bot.geometry import scaled_point, scaled_region


def test_scaled_point_preserves_reference_coordinates() -> None:
    assert scaled_point(960, 270, (1920, 1080)) == (960, 270)


def test_scaled_point_scales_for_smaller_screen() -> None:
    assert scaled_point(960, 270, (1280, 720)) == (640, 180)


def test_scaled_region_scales_position_and_dimensions() -> None:
    assert scaled_region(100, 100, 200, 100, (960, 540)) == (50, 50, 100, 50)


def test_scaled_point_rejects_invalid_screen_size() -> None:
    with pytest.raises(ValueError):
        scaled_point(1, 1, (0, 1080))


@pytest.mark.parametrize("width,height", [(0, 10), (10, 0), (-1, 5)])
def test_scaled_region_rejects_invalid_dimensions(width: int, height: int) -> None:
    with pytest.raises(ValueError):
        scaled_region(0, 0, width, height, (1920, 1080))
