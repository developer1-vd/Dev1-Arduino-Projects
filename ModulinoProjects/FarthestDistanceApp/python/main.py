"""Farthest Distance - Python side of the Arduino App Lab app.

The sketch sends Bridge.notify("distance", now_mm, farthest_mm) 4 times a
second (-1 means no reading). Sweep the Modulino Distance slowly across the
scene; this prints the current reading and the farthest object seen in the
last few seconds, and announces each new farthest record.
"""

from arduino.app_utils import App, Bridge

BAR_MM_PER_CHAR = 50  # one '#' per 5 cm

record_mm = 0  # farthest ever seen since the app started


def fmt(mm: int) -> str:
    if mm < 0:
        return "out of range"
    if mm >= 1000:
        return f"{mm / 1000:.2f} m"
    return f"{mm / 10:.1f} cm"


def distance(now_mm: int, farthest_mm: int):
    """Called from the sketch with the latest readings."""
    global record_mm
    now_mm = int(now_mm)
    farthest_mm = int(farthest_mm)

    bar = "#" * (max(now_mm, 0) // BAR_MM_PER_CHAR)
    print(f"now: {fmt(now_mm):>12}  farthest: {fmt(farthest_mm):>12}  {bar}")

    if farthest_mm > record_mm:
        record_mm = farthest_mm
        print(f"*** New farthest object: {fmt(record_mm)} ***")


def sensor_status(found: bool):
    """Called from the sketch while it looks for the Modulino Distance."""
    if found:
        print("Modulino Distance found. Sweep it slowly across the scene.")
    else:
        print(
            "Modulino Distance NOT found - check the Qwiic cable goes from the "
            "board's Qwiic connector to the sensor. Retrying..."
        )


print("Registering callbacks.")
Bridge.provide("distance", distance)
Bridge.provide("sensor_status", sensor_status)

print("Starting App...")
App.run()
