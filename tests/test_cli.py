"""Tests for safe-by-default CLI behavior."""

import pytest

from human_benchmark_bot import cli


def test_default_cli_is_preview_only(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["--game", "reaction"]) == 0
    output = capsys.readouterr().out
    assert "PREVIEW ONLY" in output
    assert "No browser, mouse, keyboard, or clipboard actions" in output


def test_preview_expands_all_games(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["--game", "all", "--dry-run"]) == 0
    output = capsys.readouterr().out
    assert "Reaction" in output
    assert "Number" in output
    assert "Verbal" in output
    assert "Visual" in output


def test_preview_does_not_import_game_routines(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden_import(*args: object, **kwargs: object) -> None:
        pytest.fail("preview mode must not import a game routine")

    monkeypatch.setattr(cli.importlib, "import_module", forbidden_import)
    assert cli.main(["--game", "reaction"]) == 0


def test_input_and_dry_run_flags_cannot_be_combined() -> None:
    with pytest.raises(SystemExit):
        cli.main(["--game", "reaction", "--allow-input", "--dry-run"])


def test_rounds_are_bounded_by_game(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        cli.main(["--game", "reaction", "--rounds", "21"])
    assert "cannot exceed" in capsys.readouterr().err


def test_load_wait_has_a_sensible_upper_bound(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit):
        cli.main(["--game", "reaction", "--load-wait", "121"])
    assert "between 0 and" in capsys.readouterr().err
