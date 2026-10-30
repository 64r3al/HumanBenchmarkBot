"""PyInstaller-friendly entry point for the HumanBenchmarkBot desktop app."""

from human_benchmark_bot.ui.app import main


if __name__ == "__main__":
    raise SystemExit(main())
