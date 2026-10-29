# HumanBenchmarkBot

A Python desktop-automation prototype for selected [Human Benchmark](https://humanbenchmark.com/) mini-games. It opens the game in your browser and uses screen pixels, mouse/keyboard input, and OCR to automate the interaction.

> **Status: experimental baseline (v0.1.0).** The website's layout and behavior can change. The included coordinate-based routines are a starting point for testing and improvement, not a guarantee of reliable results on every browser, screen size, or game version.

## Current game routines

| Game | Command name | Method |
|---|---|---|
| Reaction Time | `reaction` | Waits for the green state and clicks |
| Number Memory | `number` | Copies the displayed number, then submits it |
| Verbal Memory | `verbal` | Reads the displayed word with Tesseract OCR and tracks previously seen words |
| Visual Memory | `visual` | Attempts to detect highlighted tiles in a screenshot and clicks their centers |

The initial coordinate map is calibrated around a **1920 × 1080** display. Other resolutions are scaled proportionally, but browser zoom, browser chrome, page layout, display scaling, and the game's current UI can still affect detection.

## Requirements

- Python 3.10 or newer
- A desktop session with a visible browser and mouse/keyboard control
- Tesseract OCR installed and available on your `PATH` for the Verbal Memory routine
- Clipboard support for the Number Memory routine

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/64r3al/HumanBenchmarkBot.git
cd HumanBenchmarkBot
```

### 2. Create and activate a virtual environment

**Windows (PowerShell):**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**

```bat
py -m venv .venv
.venv\Scripts\activate.bat
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install the project

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

Install Tesseract separately from the official [Tesseract OCR project](https://github.com/tesseract-ocr/tesseract). If the executable is not on your `PATH`, pass its full path using `--tesseract-cmd`.

## Usage

Run one game:

```bash
python -m human_benchmark_bot --game reaction
python -m human_benchmark_bot --game number --rounds 20
python -m human_benchmark_bot --game verbal --rounds 100
python -m human_benchmark_bot --game visual --rounds 15
```

Run all four routines sequentially:

```bash
python -m human_benchmark_bot --game all
```

Show all options:

```bash
python -m human_benchmark_bot --help
```

The browser opens automatically. Keep the game tab visible and focused during automation. Use `--load-wait` to change the default browser-loading countdown (in seconds).

Example with a custom Tesseract path:

```bash
python -m human_benchmark_bot --game verbal --tesseract-cmd "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

## Safety and responsible use

- Use this project only for personal testing, learning, or other activity permitted by the website.
- Automated play may conflict with a website's rules or undermine the purpose of a human-performance benchmark. Do not use it to misrepresent human results, evade safeguards, or gain an unfair advantage in a competition.
- PyAutoGUI's fail-safe is enabled: moving the pointer to the **top-left corner** of the primary screen aborts automation.
- Do not use your computer for other input-driven tasks while the bot is running.
- This project does not ask for, collect, or store your Human Benchmark account credentials.

## Troubleshooting

**The script cannot detect a game state.** Make sure the browser is focused, the game is fully loaded, the page is at a supported zoom level, and the display is close to the reference layout. The site's colors and layout may have changed; detection constants are intentionally centralized so they can be tuned during development.

**Verbal Memory reports a Tesseract error.** Install Tesseract separately and ensure `tesseract` works from a terminal, or provide `--tesseract-cmd`.

**Number Memory cannot copy a number.** Make sure clipboard access works in your desktop session and that the game's number is selectable. This routine depends on browser selection behavior and may need an update.

**Visual Memory detects no tiles or clicks the wrong cells.** Tile detection is experimental and sensitive to the rendered colors and game layout. Stop the run instead of treating a failed detection as a valid result.

## Development

Install the project in editable mode as shown above. Run the lightweight test suite with:

```bash
python -m pip install pytest
python -m pytest
```

The GitHub Actions workflow also performs a Python syntax/bytecode compilation check on pushes and pull requests.

## Project scope

This repository starts with a small, readable baseline so each game routine can be tested and improved independently. Future work can focus on more reliable UI detection, safer state transitions, automated tests, and better cross-resolution support.

## Disclaimer

Human Benchmark is a third-party website. This is an independent community project and is not affiliated with, endorsed by, or sponsored by Human Benchmark.
