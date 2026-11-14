# VibroButtonLevels

Hold a button on the Modulino Buttons to run the Modulino Vibro, from barely
vibrating to super vibrating. Release to stop; the LED above the held button
lights up.

| Button | Strength | Power value |
|--------|----------|-------------|
| A | barely vibrating | `GENTLE` (25) |
| B | medium           | `MEDIUM` (35) |
| C | super vibrating  | `MAXIMUM` (50) |

The power values come from the Arduino_Modulino library, whose range is
`GENTLE` (25) to `MAXIMUM` (50). Change `levelPower[]` in the sketch to tune
them; much below 25 the motor may not start.

## Hardware
- Arduino board with a Qwiic connector (e.g. UNO R4 WiFi, UNO Q, VENTUNO Q)
- Modulino Buttons, Modulino Vibro, 2 Qwiic cables (daisy-chain them)

## Software
Install the **Arduino_Modulino** library from the Library Manager, open
`VibroButtonLevels.ino` and upload. The Serial Monitor (9600 baud) shows each
press and says if a module isn't found.

On the UNO Q / VENTUNO Q in the Arduino IDE, install the **Arduino UNO Q
Zephyr Core** from the Boards Manager first; the sketch uses the board's
Qwiic connector (`Wire1`) automatically. For the Python version, use
`../VibroButtonLevelsApp` in Arduino App Lab.
