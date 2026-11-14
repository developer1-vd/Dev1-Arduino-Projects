# RandomBuzzer

Buzzer-only Modulino project (no buttons). The Modulino Buzzer plays
continuously and randomly jumps between low and high levels, holding each for
a random 0.2–1.5 s.

| Level | Sound | Pitch |
|-------|-------|-------|
| 1 | low (quietest) | 400 Hz  |
| 2 | mid            | 1500 Hz |
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

For the UNO Q / VENTUNO Q, use `../RandomBuzzerApp` in Arduino App Lab instead.
