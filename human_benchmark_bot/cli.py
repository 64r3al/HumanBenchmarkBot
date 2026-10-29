"""Command-line entry point for HumanBenchmarkBot."""

from __future__ import annotations

import argparse
import importlib
import sys

from . import __version__
from .config import DEFAULT_ROUNDS


GAME_MODULES = {
    "reaction": ".games.reaction_time",
    "number": ".games.number_memory",
    "verbal": ".games.verbal_memory",
    "visual": ".games.visual_memory",
}


def build_parser() -> argparse.ArgumentParser:
    """Construct the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="human-benchmark-bot",
        description="Experimental desktop automation for selected Human Benchmark games.",
    )
    parser.add_argument(
        "--game",
        choices=[*GAME_MODULES, "all"],
        required=True,
        help="Game routine to run.",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=None,
        help="Number of rounds/levels (defaults vary by game).",
    )
    parser.add_argument(
        "--load-wait",
        type=int,
        default=5,
        help="Seconds to wait after opening the browser tab (default: 5).",
    )
    parser.add_argument(
        "--tesseract-cmd",
        default=None,
        help="Optional full path to the Tesseract executable (used by Verbal Memory).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def _run_game(game: str, rounds: int, load_wait: int, tesseract_cmd: str | None) -> None:
    """Load one routine lazily so help output does not initialize desktop libraries."""
    if game == "verbal" and tesseract_cmd:
        import pytesseract

        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    module = importlib.import_module(GAME_MODULES[game], package=__package__)
    module.run(rounds=rounds, load_wait=load_wait)


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and run the requested game routine."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.rounds is not None and args.rounds < 1:
        parser.error("--rounds must be at least 1.")
    if args.load_wait < 0:
        parser.error("--load-wait must be zero or greater.")

    games = list(GAME_MODULES) if args.game == "all" else [args.game]
    try:
        for game in games:
            rounds = args.rounds if args.rounds is not None else DEFAULT_ROUNDS[game]
            print(f"\n=== {game.title()} ({rounds} round(s)) ===")
            _run_game(game, rounds, args.load_wait, args.tesseract_cmd)
    except KeyboardInterrupt:
        print("\nStopped by user.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        print(
            "Tip: move the pointer to the top-left screen corner to trigger "
            "PyAutoGUI's fail-safe if automation is active.",
            file=sys.stderr,
        )
        return 1

    return 0
