# Vibro Button Levels (Arduino App Lab)

The App Lab version of `../VibroButtonLevels`, for the Arduino UNO Q and
VENTUNO Q. **Setup steps: [SETUP.md](SETUP.md).**

Hold a button on the Modulino Buttons to run the Modulino Vibro; release to
stop. Each change is sent to Python over the Bridge, and `python/main.py`
logs the press, how long it was held and a count per level.

| Button | Strength | Power value |
|--------|----------|-------------|
| A | barely vibrating | `GENTLE` (25) |
| B | medium           | `MEDIUM` (35) |
| C | super vibrating  | `MAXIMUM` (50) |

Tune `levelPower[]` in `sketch/sketch.ino`.

## Layout
- `app.yaml` - app name, icon and description
- `sketch/sketch.ino` - reads the buttons and drives the vibration motor
- `sketch/sketch.yaml` - board platform and library versions
- `python/main.py` - logs presses, hold times and counts
