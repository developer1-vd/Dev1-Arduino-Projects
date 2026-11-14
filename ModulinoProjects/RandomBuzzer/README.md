# RandomBuzzer

Buzzer-only Modulino project (no buttons). The Modulino Buzzer plays
continuously and randomly jumps between low and high levels, holding each for
a random 0.2–1.5 s.

| Level | Sound | Pitch |
|-------|-------|-------|
| 1 | low (still loud) | 2500 Hz  |
| 2 | mid            | 3300 Hz |
| 3 | high (loudest) | 4000 Hz |

The buzzer has no volume control; higher pitches are closer to the piezo's
~4 kHz resonance, so they also sound louder.

## Hardware
- Arduino board with a Qwiic connector (e.g. UNO R4 WiFi)
- Modulino Buzzer + Qwiic cable

## Software
Install the **Modulino** library from the Arduino Library Manager, open
`RandomBuzzer.ino` and upload. The Serial Monitor (9600 baud) shows each level.

Tune `levelFrequency[]`, `minHoldMs` and `maxHoldMs` to taste.

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
side, use the App Lab app in `../RandomBuzzerApp` instead.
