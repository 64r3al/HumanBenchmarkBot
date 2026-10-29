"""Shared game URLs, reference-layout constants, and safe run limits."""

GAME_URLS = {
    "reaction": "https://www.humanbenchmark.com/tests/reactiontime",
    "number": "https://www.humanbenchmark.com/tests/number-memory",
    "verbal": "https://www.humanbenchmark.com/tests/verbal-memory",
    "visual": "https://www.humanbenchmark.com/tests/memory",
}

# The initial coordinate map is calibrated around a 1920 x 1080 display.
REFERENCE_SIZE = (1920, 1080)

# RGB values observed in the older reference UI. A changed website may need
# recalibration; detection is deliberately conservative and stops on timeout.
REACTION_GREEN = (24, 217, 113)
REACTION_RESULT_BLUE = (0, 137, 206)
NUMBER_INPUT_BLUE = (0, 110, 165)
NUMBER_READY_BLUE = (0, 137, 206)

DEFAULT_ROUNDS = {
    "reaction": 5,
    "number": 20,
    "verbal": 100,
    "visual": 15,
}

# Limits protect against accidental, unexpectedly long runs. They are not
# claims that the game can successfully complete this many rounds.
MAX_ROUNDS = {
    "reaction": 20,
    "number": 100,
    "verbal": 250,
    "visual": 50,
}

DEFAULT_LOAD_WAIT = 5
MAX_LOAD_WAIT = 120
