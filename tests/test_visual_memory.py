"""Synthetic screenshot tests for Visual Memory tile detection."""

from PIL import Image, ImageDraw

from human_benchmark_bot.games.visual_memory import find_highlighted_cells


def test_finds_centers_of_separated_bright_tiles() -> None:
    image = Image.new("RGB", (300, 200), (28, 28, 28))
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 59, 59), fill=(255, 255, 255))
    draw.rectangle((100, 100, 139, 139), fill=(255, 255, 255))

    assert find_highlighted_cells(image) == [(39, 39), (119, 119)]


def test_ignores_tiny_bright_noise() -> None:
    image = Image.new("RGB", (300, 200), (28, 28, 28))
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 23, 23), fill=(255, 255, 255))

    assert find_highlighted_cells(image) == []


def test_returns_empty_for_blank_grid() -> None:
    image = Image.new("RGB", (300, 200), (28, 28, 28))
    assert find_highlighted_cells(image) == []
