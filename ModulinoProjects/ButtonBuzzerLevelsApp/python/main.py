"""Button Buzzer Levels - Python side of the Arduino App Lab app.

The sketch calls Bridge.notify("level_changed", level) whenever the held
button changes. This script logs each press, how long it was held, and keeps
a running count of presses per level.
"""

import time

from arduino.app_utils import App, Bridge

LEVEL_NAMES = {1: "A (quiet)", 2: "B (medium)", 3: "C (loud)"}

press_counts = {1: 0, 2: 0, 3: 0}
current_level = 0
pressed_at = 0.0


def level_changed(level: int):
    """Called from the sketch each time the held button changes."""
    global current_level, pressed_at

    level = int(level)
    now = time.monotonic()

    # Report how long the previous button was held
    if current_level:
        held_for = now - pressed_at
        print(f"Released {LEVEL_NAMES[current_level]} after {held_for:.2f} s")

    current_level = level
    if level in LEVEL_NAMES:
        pressed_at = now
        press_counts[level] += 1
        print(f"Holding button {LEVEL_NAMES[level]} -> level {level}")
        print(
            "Presses so far: "
            + ", ".join(f"{LEVEL_NAMES[l]}={n}" for l, n in press_counts.items())
        )
    else:
        print("Silent")


print("Registering 'level_changed' callback.")
Bridge.provide("level_changed", level_changed)

print("Starting App... hold a button on the Modulino Buttons.")
App.run()
