# Farthest Distance (Arduino App Lab)

The App Lab version of `../FarthestDistance`, for the Arduino UNO Q and
VENTUNO Q. **Setup steps: [SETUP.md](SETUP.md).**

The Modulino Distance measures one distance straight ahead, so **slowly sweep
it across the scene**. The sketch keeps the farthest reading from the last
5 seconds and sends it to Python 4 times a second. `python/main.py` prints:

```
now:      41.2 cm  farthest:      1.19 m  ########
*** New farthest object: 1.19 m ***
```

Objects beyond the sensor's range (roughly 1.2 m) show as `out of range`.

## Proximity alarm
Add a **Modulino Buzzer** to the Qwiic chain and it works like a parking
sensor: it beeps when something comes closer than **40 cm**, beeps faster
as it gets closer, and sounds continuously below **10 cm**. Change
`alertMm` and `solidMm` at the top of the sketch to adjust the distances.
The buzzer is optional; without it you still get the distances.

## Layout
- `app.yaml` - app name, icon and description
- `sketch/sketch.ino` - reads the sensor and tracks the farthest reading
- `sketch/sketch.yaml` - board platform and library versions
- `python/main.py` - prints the readings and new farthest records
