# Dev1-Arduino-Projects

My Arduino projects: small projects built with Arduino Modulino modules, and
an AI coding tool for Arduino.

## Contents

| Folder | What's in it |
|---|---|
| [`ModulinoProjects/`](ModulinoProjects/) | Projects built with Modulino modules connected over Qwiic |
| [`AIProjects/`](AIProjects/) | Projects that use AI with Arduino |

### ModulinoProjects

Most projects come in two versions:

- **Arduino IDE sketch** (`ProjectName/`): a plain `.ino` sketch for any
  board with a Qwiic connector (UNO R4 WiFi, UNO Q, VENTUNO Q, ...).
- **Arduino App Lab app** (`ProjectNameApp/`): for the UNO Q and VENTUNO Q,
  with a sketch on the microcontroller and a Python script on the board's
  Linux side. Each one has a `SETUP.md` with step-by-step setup.

| Project | Modulinos | What it does |
|---|---|---|
| [ButtonBuzzerLevels](ModulinoProjects/ButtonBuzzerLevels/) · [App](ModulinoProjects/ButtonBuzzerLevelsApp/) | Buttons, Buzzer | Hold button A, B or C to play the buzzer at three loudness levels. |
| [RandomBuzzer](ModulinoProjects/RandomBuzzer/) · [App](ModulinoProjects/RandomBuzzerApp/) | Buzzer | The buzzer randomly jumps between low and high pitches. |
| [FarthestDistance](ModulinoProjects/FarthestDistance/) · [App](ModulinoProjects/FarthestDistanceApp/) | Distance, Buzzer (optional) | Sweep the sensor to find the farthest object. Beeps like a parking sensor when something comes within 40 cm. |
| [VibroButtonLevels](ModulinoProjects/VibroButtonLevels/) · [App](ModulinoProjects/VibroButtonLevelsApp/) | Buttons, Vibro | Hold button A, B or C to vibrate from barely to super strong. |

### AIProjects

| Project | What it does |
|---|---|
| [ArduinoClaudeStudio](AIProjects/ArduinoClaudeStudio/) | A local WebUI for writing Arduino code with Claude Code: editor, compile and upload with `arduino-cli`, serial monitor, and a Claude chat that can write, fix, upload and test sketches on your board. |

## Getting started

### Modulino projects in the Arduino IDE

1. Install the **Arduino_Modulino** library from the Library Manager.
2. Connect the Modulinos to the board's Qwiic connector. You can
   daisy-chain several modules.
3. Open the project's `.ino` file, select your board and port, and upload.

On the **UNO Q** or **VENTUNO Q**, first install the **Arduino UNO Q Zephyr
Core** from the Boards Manager. The sketches use the board's Qwiic
connector (`Wire1`) automatically.

### Modulino projects in Arduino App Lab (UNO Q / VENTUNO Q)

Create a new app in App Lab and copy in the `*App` folder's files:
`sketch/sketch.ino`, `sketch/sketch.yaml` and `python/main.py`. Then press
**Run**. Each app's `SETUP.md` covers power, wiring and troubleshooting.

### Arduino Claude Studio

See its [README](AIProjects/ArduinoClaudeStudio/README.md). In short: install
Python 3.10+ and `arduino-cli`, log in to Claude Code, then run `./run.sh`
(or `run.bat` on Windows) and open <http://127.0.0.1:8765>.

## Troubleshooting

| Problem | Fix |
|---|---|
| `Modulino.h` or `Arduino_Modulino.h: No such file` | Install the **Arduino_Modulino** library. In App Lab, copy the app's `sketch.yaml`, or add the library in the app's Libraries panel. |
| A module is "NOT found" | Re-seat the Qwiic cables, then unplug the board's power completely and plug it back in. |
| The buzzer is quiet | It has no volume control. It's loudest near 4000 Hz, so use pitches close to that. |
| App Lab takes a long time to start | Compiling the Modulino libraries takes a while. Turn on **Run at startup** to skip the wait. |

## License

[GNU GPL v3](LICENSE)
