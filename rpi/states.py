import re

# BCM pin numbers
OUT1 = 17
OUT2 = 27
OUT3 = 22
PINS = (OUT1, OUT2, OUT3)

# Bit patterns (HIGH=1, LOW=0)
# Note: FORWARD and BACKWARD are swapped per your request.
STATES = {
    "FORWARD":  (0, 0, 1),
    "BACKWARD": (0, 1, 0),
    "LEFT":     (0, 1, 1),
    "RIGHT":    (1, 0, 0),
    "LOCK":     (1, 0, 1),
    "UNLOCK":   (1, 1, 0),
    "STOP":     (0, 0, 0),
}

ALIASES = {
    "f": "FORWARD", "forward": "FORWARD",
    "b": "BACKWARD", "backward": "BACKWARD", "reverse": "BACKWARD",
    "l": "LEFT", "left": "LEFT",
    "r": "RIGHT", "right": "RIGHT",
    "lock": "LOCK", "unlock": "UNLOCK",
    "stop": "STOP", "s": "STOP",
    "sleep": "SLEEP", "wait": "SLEEP",
}

# Command pattern: name [duration]  e.g., "forward 2", "right:1.5"
CMD_PATTERN = re.compile(r"^\s*([a-zA-Z_]+)\s*(?::|\s)?\s*([0-9]*\.?[0-9]+)?\s*$")

# Defaults
DEFAULT_STEP_DURATION = 1.0
PAUSE_AFTER_SEQ_SECONDS = 1.0  # STOP hold after every `seq` run

