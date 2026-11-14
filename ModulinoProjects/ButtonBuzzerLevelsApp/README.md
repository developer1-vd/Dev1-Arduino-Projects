# Button Buzzer Levels (Arduino App Lab)

The App Lab version of `../ButtonBuzzerLevels`, for the Arduino UNO Q.

Hold a button on the Modulino Buttons to play the Modulino Buzzer at one of 3
loudness levels; release it to stop. Each time the held button changes, the
sketch notifies Python over the Bridge, and `python/main.py` logs the press,
how long it was held and a count per level.

| Button | Level | Pitch |
|--------|-------|-------|
| A      | 1 (quietest) | 400 Hz  |
| B      | 2            | 1500 Hz |
| C      | 3 (loudest)  | 4000 Hz |

The buzzer has no volume control, so "louder" comes from pitches closer to the
piezo's ~4 kHz resonance. Tune `levelFrequency[]` in `sketch/sketch.ino`.

## Layout
- `app.yaml` - app name, icon and description
- `sketch/sketch.ino` - runs on the microcontroller: reads buttons, drives the buzzer
- `sketch/sketch.yaml` - board platform and library versions
- `python/main.py` - runs on Linux: receives `level_changed` and logs it

## Run it
1. Connect the Modulino Buttons and Buzzer to the UNO Q's Qwiic connector.
2. Copy this folder into your App Lab apps folder (or create a new app and
   replace its files with these).
3. Open it in Arduino App Lab and press **Run**. The Python output shows in
   the app's console.
