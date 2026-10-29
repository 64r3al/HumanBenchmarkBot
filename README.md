# HumanBenchmarkBot

A Python desktop-automation prototype for selected [Human Benchmark](https://humanbenchmark.com/) mini-games. The project uses visible-screen detection, mouse/keyboard input, clipboard validation, and OCR. Its routines are experimental and may need recalibration when the website changes.

> **Current version: 0.2.0 (hardening work in progress).** Passing unit tests does not prove that a routine works correctly on the live website. Each game needs supervised, real-browser testing before it should be considered reliable.

## Safety first

**The default command is preview-only.** It does not open a browser, move the mouse, press keys, or access the clipboard.

- Actual desktop automation requires the explicit `--allow-input` flag and an interactive confirmation.
- Keep the Human Benchmark tab visible and active. Browser layout, zoom, display scaling, and other open windows can still affect coordinates.
- PyAutoGUI's emergency fail-safe remains enabled. Moving the pointer to the top-left corner of the primary display should stop input actions.
- The bot can click/type into whichever window is active. No software-only safeguard can guarantee that an unintended click will never reach another application. Close unsaved work and do not use the computer for other tasks while it runs.
- Diagnostic screenshots are disabled by default. Use `--debug` only when needed; screenshots can contain anything visible on the desktop.
- Do not use the project to misrepresent automated results as human performance, evade safeguards, or submit misleading scores. Follow the website's current terms.

## Current routines

| Game | Command | Method | Status |
|---|---|---|---|
| Reaction Time | `reaction` | Polls a screen pixel for the green state and checks that it changes after a click. | Experimental; live testing required |
| Number Memory | `number` | Selects and copies the displayed number, validates the clipboard, then submits it. | Experimental; depends on text selection |
| Verbal Memory | `verbal` | Reads the displayed word with confidence-checked Tesseract OCR and tracks seen words. | Experimental; OCR and end-state detection need live validation |
| Visual Memory | `visual` | Detects bright tile regions from screenshots and waits for visual transitions. | Experimental; requires grid/layout validation |

The initial coordinate map is based on a 1920 × 1080 reference layout. Coordinate scaling alone does not compensate for browser chrome, zoom, display scaling, page layout, or changes to the game's UI.

## Requirements

- Python 3.10 or newer
- A desktop session with a visible browser and mouse/keyboard control
- Tesseract OCR installed separately for Verbal Memory
- Clipboard support for Number Memory

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/64r3al/HumanBenchmarkBot.git
cd HumanBenchmarkBot
```

### 2. Create a virtual environment

**Windows (PowerShell):**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**

```bat
py -m venv .venv
.\.venv\Scripts\activate.bat
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install the project

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Install Tesseract from the official [Tesseract OCR project](https://github.com/tesseract-ocr/tesseract). If it is not on your `PATH`, provide its executable path using `--tesseract-cmd`.

## Usage

### Preview only (safe default)

```bash
python -m human_benchmark_bot --game reaction
python -m human_benchmark_bot --game all --dry-run
```

Preview mode prints the planned game and round count. It does not open a browser or control desktop input.

### Enable actual desktop input

Run this in an interactive terminal. The program asks for confirmation before starting.

```bash
python -m human_benchmark_bot --game reaction --allow-input
```

Other examples:

```bash
python -m human_benchmark_bot --game number --rounds 20 --allow-input
python -m human_benchmark_bot --game verbal --rounds 100 --allow-input
python -m human_benchmark_bot --game visual --rounds 15 --allow-input
```

Use a custom Tesseract path:

```bash
python -m human_benchmark_bot --game verbal --tesseract-cmd "C:\Program Files\Tesseract-OCR\tesseract.exe" --allow-input
```

Show all options:

```bash
python -m human_benchmark_bot --help
```

Each game has a bounded maximum run length. If a visual state or OCR result is ambiguous, the routine should stop instead of continuing blindly.

## Debugging and diagnostics

Use `--debug` to save a screenshot when a supported detection failure occurs:

```bash
python -m human_benchmark_bot --game reaction --allow-input --debug
```

Diagnostic images are written to `diagnostics/` by default and are ignored by Git. Inspect them before sharing; they may contain unrelated desktop content. The debug flag is opt-in and is not required for normal runs.

## Tests and development

Install development dependencies with:

```bash
python -m pip install -e ".[dev]"
python -m pytest
ruff check .
ruff format --check .
```

GitHub Actions checks syntax, lint, formatting, and unit tests on Python 3.10–3.13. Tests mock desktop interactions or use synthetic images; they do not interact with the live website. A successful CI run is therefore not proof of real-browser reliability.

## Known limitations

- Screen coordinates and observed pixel colors can become stale when the website changes.
- Number Memory depends on selectable text and clipboard behavior.
- Verbal Memory depends on Tesseract's English model and OCR confidence.
- Visual Memory's bright-tile detector is heuristic; synthetic tests cover only the cases represented in the test suite.
- Browser focus and desktop interaction are not fully controllable by the application.
- No live-browser acceptance test has been performed as part of this release.

## Project scope and disclaimer

This is an independent experimental project. Human Benchmark is a third-party website; this repository is not affiliated with, endorsed by, or sponsored by Human Benchmark. Use the site and this project responsibly and in accordance with the site's current terms.
