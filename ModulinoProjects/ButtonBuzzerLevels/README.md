# ButtonBuzzerLevels

Three buttons, three buzzer levels, using Arduino Modulino nodes.

| Button | Level | Frequency |
|--------|-------|-----------|
| A      | 1 (quietest) | 400 Hz  |
| B      | 2            | 1500 Hz |
| C      | 3 (loudest)  | 4000 Hz |

## Hardware
- Arduino board with a Qwiic connector (e.g. UNO R4 WiFi, Nano Matter, Plug and Make Kit)
- Modulino Buttons
- Modulino Buzzer

Daisy-chain the modules with Qwiic cables.

## Software
Install the **Modulino** library from the Arduino Library Manager, then open
`ButtonBuzzerLevels.ino` and upload.

## About "louder"
The Modulino Buzzer has no volume setting, only frequency and duration. A
piezo is loudest near its resonant frequency (around 4 kHz), so each button
uses a frequency closer to that point to sound louder. Change
`levelFrequency[]` in the sketch to tune the levels by ear.
