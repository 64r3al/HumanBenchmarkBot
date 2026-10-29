"""Command-line entry point with safe-by-default execution."""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

from . import __version__
from .config import (
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


def build_parser() -> argparse.ArgumentParser:
    """Construct the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="human-benchmark-bot",
        description=(
            "Experimental desktop automation for selected Human Benchmark games. "
            "Runs in preview-only mode unless --allow-input is specified."
        ),
    )
    parser.add_argument(
        "--game",
        choices=[*GAME_MODULES, "all"],
        required=True,
        help="Game routine to preview or run.",
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
        default=DEFAULT_LOAD_WAIT,
        help=(
            "Seconds to wait after opening the browser tab "
            f"(default: {DEFAULT_LOAD_WAIT})."
        ),
    )
    parser.add_argument(
        "--tesseract-cmd",
        default=None,
        help="Optional full path to the Tesseract executable (Verbal Memory only).",
    )
    parser.add_argument(
        "--allow-input",
        action="store_true",
        help=(
            "Enable real mouse/keyboard automation after an interactive "
            "confirmation. Without this flag, no browser or input actions run."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the run plan without opening a browser or controlling input.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Save diagnostic screenshots after detection failures.",
    )
    parser.add_argument(
        "--diagnostics-dir",
        type=Path,
        default=Path("diagnostics"),
        help="Directory for optional diagnostic screenshots (default: diagnostics).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def _selected_games(game: str) -> list[str]:
    """Expand the all-games shortcut into a deterministic order."""
    return list(GAME_MODULES) if game == "all" else [game]


def _rounds_for(game: str, requested_rounds: int | None) -> int:
    """Validate and return a bounded round count."""
    rounds = DEFAULT_ROUNDS[game] if requested_rounds is None else requested_rounds
    if rounds < 1:
        raise ValueError("--rounds must be at least 1.")
    if rounds > MAX_ROUNDS[game]:
        raise ValueError(
            f"--rounds for {game} cannot exceed {MAX_ROUNDS[game]}."
        )
    return rounds


def _print_plan(
    games: list[str],
    requested_rounds: int | None,
    load_wait: int,
) -> None:
    """Print the intended work without opening a browser or sending input."""
    print(f"HumanBenchmarkBot v{__version__} — PREVIEW ONLY")
    print("No browser, mouse, keyboard, or clipboard actions will be performed.")
    for game in games:
        rounds = _rounds_for(game, requested_rounds)
        print(f"- {game.title()}: {rounds} round(s) — {GAME_URLS[game]}")
    print(f"Browser focus countdown if run: {load_wait} second(s).")
    print("To enable actual input, rerun with --allow-input and confirm interactively.")


def _confirm_input_access() -> bool:
    """Require a real interactive terminal and an explicit user confirmation."""
    if not sys.stdin.isatty():
        print(
            "Refusing to control input from a non-interactive terminal. "
            "Run this command in a terminal and confirm when prompted.",
            file=sys.stderr,
        )
        return False
    try:
        answer = input(
            "\nWARNING: this will control your mouse and keyboard in the active "
            "desktop session. Close unsaved work, make sure only the intended "
            "Human Benchmark tab will receive input, and do not submit or "
            "misrepresent automated scores. Continue? [y/N] "
        )
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled; no automation was started.")
        return False
    if answer.strip().casefold() not in {"y", "yes"}:
        print("Cancelled; no automation was started.")
        return False
    return True


def _run_game(
    game: str,
    rounds: int,
    load_wait: int,
    tesseract_cmd: str | None,
    *,
    debug: bool,
    diagnostics_dir: Path,
) -> None:
    """Load one routine lazily so preview mode never initializes desktop controls."""
    if game == "verbal" and tesseract_cmd:
        import pytesseract

        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    module = importlib.import_module(GAME_MODULES[game], package=__package__)
    module.run(
        rounds=rounds,
        load_wait=load_wait,
        debug=debug,
        diagnostics_dir=str(diagnostics_dir),
    )


def main(argv: list[str] | None = None) -> int:
    """Validate options, preview safely by default, and optionally run automation."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.allow_input and args.dry_run:
        parser.error("--allow-input cannot be combined with --dry-run.")
    if not 0 <= args.load_wait <= MAX_LOAD_WAIT:
        parser.error(f"--load-wait must be between 0 and {MAX_LOAD_WAIT} seconds.")

    games = _selected_games(args.game)
    try:
        for game in games:
            _rounds_for(game, args.rounds)
    except ValueError as exc:
        parser.error(str(exc))

    if not args.allow_input:
        _print_plan(games, args.rounds, args.load_wait)
        return 0

    if not _confirm_input_access():
        return 2

    try:
        for game in games:
            rounds = _rounds_for(game, args.rounds)
            print(f"\n=== {game.title()} ({rounds} round(s)) ===")
            _run_game(
                game,
                rounds,
                args.load_wait,
                args.tesseract_cmd,
                debug=args.debug,
                diagnostics_dir=args.diagnostics_dir,
            )
    except KeyboardInterrupt:
        print("\nStopped by user.", file=sys.stderr)
        return 130
    except Exception as exc:
        if exc.__class__.__name__ == "FailSafeException":
            print(
                "PyAutoGUI safety stop triggered. No further input will be sent.",
                file=sys.stderr,
            )
            return 130
        print(f"\nAutomation stopped: {exc}", file=sys.stderr)
        print(
            "No further game actions will be attempted. Check the browser state "
            "before retrying.",
            file=sys.stderr,
        )
        return 1

    return 0
