"""PyInstaller-friendly entry point and frozen-bundle import check."""

from __future__ import annotations

import importlib
import sys

from human_benchmark_bot.ui.app import main

GAME_MODULES = (
    "human_benchmark_bot.games.reaction_time",
    "human_benchmark_bot.games.number_memory",
    "human_benchmark_bot.games.verbal_memory",
    "human_benchmark_bot.games.visual_memory",
)


def verify_game_modules() -> int:
    """Import every dynamically-dispatched game module without sending input."""
    for module_name in GAME_MODULES:
        importlib.import_module(module_name)
    return 0


if __name__ == "__main__":
    if "--self-test-imports" in sys.argv[1:]:
        raise SystemExit(verify_game_modules())
    raise SystemExit(main())
