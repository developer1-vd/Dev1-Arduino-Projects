"""Random Buzzer - Python side of the Arduino App Lab app.

The sketch calls Bridge.notify("level_changed", level, hold_ms) every time
the buzzer randomly jumps to a new level. This script logs each change and
keeps a running tally of how often each level came up.
"""

from arduino.app_utils import App, Bridge

LEVEL_NAMES = {1: "low", 2: "mid", 3: "high"}

counts = {1: 0, 2: 0, 3: 0}
total_ms = {1: 0, 2: 0, 3: 0}


def level_changed(level: int, hold_ms: int):
    """Called from the sketch each time the buzzer changes level."""
    level = int(level)
    hold_ms = int(hold_ms)
    if level not in LEVEL_NAMES:
        print(f"Unexpected level: {level}")
        return

    counts[level] += 1
    total_ms[level] += hold_ms

    bar = "#" * level
    print(f"{bar:<3} level {level} ({LEVEL_NAMES[level]}) for {hold_ms} ms")

    # Print a summary every 10 changes
    if sum(counts.values()) % 10 == 0:
        print(
            "Tally: "
            + ", ".join(
                f"{LEVEL_NAMES[l]}={counts[l]}x/{total_ms[l] / 1000:.1f}s"
                for l in LEVEL_NAMES
            )
        )


def buzzer_status(found: bool):
    """Called from the sketch when it looks for the Modulino Buzzer."""
    if found:
        print("Modulino Buzzer found.")
    else:
        print(
            "Modulino Buzzer NOT found - check the Qwiic cable goes from the "
            "board's Qwiic connector to the buzzer. Retrying..."
        )


print("Registering callbacks.")
Bridge.provide("level_changed", level_changed)
Bridge.provide("buzzer_status", buzzer_status)

print("Starting App... the buzzer will randomly go low and high.")
App.run()
