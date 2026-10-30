"""Tests for worker-safe, callback-based routine logging."""

from __future__ import annotations

import sys
from threading import Event
from types import SimpleNamespace

from human_benchmark_bot.automation import open_game
from human_benchmark_bot.ui.services import RunConfig, run_game
from human_benchmark_bot.ui.workers import RunWorker


def test_open_game_routes_status_messages_to_callback(monkeypatch) -> None:
    from human_benchmark_bot import automation

    monkeypatch.setattr(automation.webbrowser, "open_new_tab", lambda _url: True)
    messages: list[tuple[str, str]] = []

    open_game(
        "Test Game",
        "https://example.com/",
        load_wait=0,
        log_callback=lambda level, message: messages.append((level, message)),
    )

    assert messages == [
        ("info", "Opening Test Game: https://example.com/"),
        (
            "info",
            "Automation is active. Do not use the mouse or keyboard for other tasks.",
        ),
    ]


def test_open_game_keeps_cli_console_output_without_callback(
    monkeypatch, capsys
) -> None:
    from human_benchmark_bot import automation

    monkeypatch.setattr(automation.webbrowser, "open_new_tab", lambda _url: True)

    open_game("Test Game", "https://example.com/", load_wait=0)

    output = capsys.readouterr().out
    assert "Opening Test Game: https://example.com/" in output
    assert "Automation is active." in output


def test_run_game_passes_logging_callback_to_routine(monkeypatch) -> None:
    from human_benchmark_bot.ui import services

    captured: dict[str, object] = {}
    fake_module = SimpleNamespace(run=lambda **kwargs: captured.update(kwargs))
    monkeypatch.setattr(
        services.importlib,
        "import_module",
        lambda *_args, **_kwargs: fake_module,
    )
    def callback(_level, _message):
        return None

    result = run_game(
        RunConfig(game="reaction", rounds=1),
        Event(),
        callback,
    )

    assert captured["log_callback"] is callback
    assert result["status"] == "completed_review"


def test_worker_does_not_replace_process_stdout_or_stderr(monkeypatch) -> None:
    from human_benchmark_bot.ui import workers

    original_stdout = sys.stdout
    original_stderr = sys.stderr
    messages: list[tuple[str, str]] = []
    results: list[dict] = []

    def fake_run_game(config, cancel_event, log_callback):
        log_callback("info", "Worker logging is callback-based.")
        return {
            "status": "completed_review",
            "message": "Finished; review required.",
            "elapsed_seconds": 0.01,
        }

    monkeypatch.setattr(workers, "run_game", fake_run_game)
    worker = RunWorker(RunConfig(game="reaction", rounds=1))
    worker.log.connect(lambda level, message: messages.append((level, message)))
    worker.result_ready.connect(results.append)

    worker.run()

    assert sys.stdout is original_stdout
    assert sys.stderr is original_stderr
    assert messages == [("info", "Worker logging is callback-based.")]
    assert results[0]["status"] == "completed_review"
