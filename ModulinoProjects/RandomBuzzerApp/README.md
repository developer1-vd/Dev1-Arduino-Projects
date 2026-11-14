# Random Buzzer (Arduino App Lab)

The App Lab version of `../RandomBuzzer`, for the Arduino UNO Q and VENTUNO Q.
**Step-by-step setup for both boards: [SETUP.md](SETUP.md).**

Only a Modulino Buzzer is used, no buttons. The buzzer plays continuously and
randomly jumps between low, mid and high, holding each for a random 0.2–1.5 s.
Each jump is sent to Python over the Bridge, and `python/main.py` logs it and
prints a tally every 10 changes.

| Level | Sound | Pitch |
|-------|-------|-------|
| 1 | low (still loud) | 2500 Hz  |
| 2 | mid            | 3300 Hz |
| 3 | high (loudest) | 4000 Hz |

Tune `levelFrequency[]`, `minHoldMs` and `maxHoldMs` in `sketch/sketch.ino`.

## Layout
- `app.yaml` - app name, icon and description
- `sketch/sketch.ino` - runs on the microcontroller: picks random levels, drives the buzzer
- `sketch/sketch.yaml` - board platform and library versions
- `python/main.py` - runs on Linux: receives `level_changed` and logs it
