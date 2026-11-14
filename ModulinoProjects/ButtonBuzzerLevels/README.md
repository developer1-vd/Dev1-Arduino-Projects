# ButtonBuzzerLevels

Three buttons, three buzzer levels, using Arduino Modulino nodes. The buzzer
sounds continuously while a button is held and stops when it is released.

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

## Arduino UNO Q / VENTUNO Q in the Arduino IDE
This sketch also runs on the UNO Q (and VENTUNO Q) from the regular Arduino
IDE; it automatically uses the board's Qwiic connector (`Wire1`).

1. In **Tools > Board > Boards Manager**, search `UNO Q` and install the
   **Arduino UNO Q Zephyr Core**. If it isn't listed, add
   `https://downloads.arduino.cc/packages/package_zephyr_index.json` under
   **File > Preferences > Additional Boards Manager URLs**.
2. Install the **Arduino_Modulino** library from the Library Manager.
3. Select **Tools > Board > Arduino UNO Q Board > Arduino UNO Q** and the
   board's port, then upload.
4. Power: the UNO Q runs from USB-C (5 V 3 A). The VENTUNO Q needs a 7–24 V
   supply on its barrel jack; a computer's USB port can't power it.

The IDE only programs the board's microcontroller. To also run the Python
side, use the App Lab app in `../ButtonBuzzerLevelsApp` instead.
