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

## Layout
- `app.yaml` - app name, icon and description
- `sketch/sketch.ino` - reads the sensor and tracks the farthest reading
- `sketch/sketch.yaml` - board platform and library versions
- `python/main.py` - prints the readings and new farthest records
