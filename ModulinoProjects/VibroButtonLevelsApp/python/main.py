"""Vibro Button Levels - Python side of the Arduino App Lab app.

The sketch calls Bridge.notify("level_changed", level) whenever the held
button changes (0 = off, 1..3 = button A..C). This script logs each press,
how long it was held, and a count per level.
"""

import time

from arduino.app_utils import App, Bridge

LEVEL_NAMES = {1: "A (barely)", 2: "B (medium)", 3: "C (super)"}

press_counts = {1: 0, 2: 0, 3: 0}
current_level = 0
pressed_at = 0.0


def level_changed(level: int):
    """Called from the sketch each time the held button changes."""
    global current_level, pressed_at

    level = int(level)
    now = time.monotonic()

    if current_level:
        print(f"Released {LEVEL_NAMES[current_level]} after {now - pressed_at:.2f} s")

    current_level = level
    if level in LEVEL_NAMES:
        pressed_at = now
        press_counts[level] += 1
        bar = "~" * (level * 3)
        print(f"Vibrating {LEVEL_NAMES[level]} {bar}")
        print(
            "Presses so far: "
            + ", ".join(f"{LEVEL_NAMES[l]}={n}" for l, n in press_counts.items())
        )
    else:
        print("Off")


def module_status(buttons_found: bool, vibro_found: bool):
    """Called from the sketch at startup with what it detected."""
    for name, found in (("Buttons", buttons_found), ("Vibro", vibro_found)):
        if found:
            print(f"Modulino {name} found.")
        else:
            print(
                f"Modulino {name} NOT found - check its Qwiic cable, then "
                "unplug the board's power and plug it back in."
            )


print("Registering callbacks.")
Bridge.provide("level_changed", level_changed)
Bridge.provide("module_status", module_status)

print("Starting App... hold a button on the Modulino Buttons.")
App.run()
