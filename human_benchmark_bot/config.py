"""Shared URLs and reference-layout detection constants."""

GAME_URLS = {
    "reaction": "https://humanbenchmark.com/tests/reactiontime",
    "number": "https://humanbenchmark.com/tests/number-memory",
    "verbal": "https://humanbenchmark.com/tests/verbal-memory",
    "visual": "https://humanbenchmark.com/tests/memory",
}

# Reference layout used by the initial coordinate map.
REFERENCE_SIZE = (1920, 1080)

# RGB values observed in the reference implementation's older UI.
# Current website updates may require retuning these values.
REACTION_GREEN = (24, 217, 113)
NUMBER_INPUT_BLUE = (0, 110, 165)

DEFAULT_ROUNDS = {
    "reaction": 5,
    "number": 20,
    "verbal": 100,
    "visual": 15,
}
