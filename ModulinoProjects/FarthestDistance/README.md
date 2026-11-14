# FarthestDistance

Tells you how far away the farthest object is, using a Modulino Distance
(time-of-flight sensor).

## How it works
The sensor measures **one distance** in a narrow cone straight ahead; it
can't see a whole room at once. To find the farthest object, **slowly sweep
the sensor across the scene**. The sketch keeps the farthest reading from the
last 5 seconds, so after a sweep it shows the farthest thing you pointed it at.

Serial Monitor (9600 baud), 4 times a second:

```
now: 412 mm   farthest: 1187 mm
```

Anything beyond the sensor's range (roughly 1.2 m, less for dark targets or
bright sunlight) gives no reading and shows as `out of range`, so "farthest"
means the farthest object the sensor can actually measure.

Tune `windowMs` (how long the farthest value is kept) and `reportEveryMs` at
the top of the sketch.

## Hardware
- Arduino board with a Qwiic connector (e.g. UNO R4 WiFi, UNO Q, VENTUNO Q)
- Modulino Distance + Qwiic cable

## Software
Install the **Arduino_Modulino** library from the Library Manager, open
`FarthestDistance.ino` and upload.

On the UNO Q / VENTUNO Q in the Arduino IDE, install the **Arduino UNO Q
Zephyr Core** from the Boards Manager first; the sketch uses the board's
Qwiic connector (`Wire1`) automatically. For the Python version, use
`../FarthestDistanceApp` in Arduino App Lab.
