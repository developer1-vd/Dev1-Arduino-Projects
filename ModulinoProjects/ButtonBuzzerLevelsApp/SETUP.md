# Setup: Arduino UNO Q and VENTUNO Q

This app runs unchanged on both boards. Both put the Qwiic connector on the
`Wire1` bus (`Modulino.begin(Wire1)` in the sketch) and both use the
`arduino:zephyr` platform and the Bridge library, so the same
`sketch.ino`, `sketch.yaml` and `python/main.py` work on either.

## What you need

| | UNO Q | VENTUNO Q |
|---|---|---|
| Board | UNO Q (2 GB or 4 GB) | VENTUNO Q |
| Power | USB-C, 5 V 3 A | Barrel jack 7–24 V (≥ 3 A), e.g. Arduino 65 W USB-C supply with its barrel adapter |
| Link to your computer | USB-C cable (data + power) | USB-C cable (data only, see power note) |
| Modulinos | Modulino Buttons, Modulino Buzzer, 2 Qwiic cables | same |
| Software | Arduino App Lab | Arduino App Lab |

Get Arduino App Lab from the App Lab section of
<https://www.arduino.cc/en/software>. It is also pre-installed on both boards
for use with a monitor, keyboard and mouse.

## 1. Power the board

**UNO Q:** plug the USB-C cable into your computer (or a 5 V 3 A charger).
That powers it and connects it.

**VENTUNO Q:** power it from the **barrel jack** (7–24 V, max 5 A) or the
screw terminals. A computer's USB port cannot power it: USB-C power needs at
least 9 V via Power Delivery, and plain 5 V gives a USB fault (blinking red
LED by the USB port). The fault is harmless; fix the power and power-cycle.
Then connect USB-C to your computer for data.

## 2. Connect the Modulinos

1. With the board off, plug a Qwiic cable from the board's **Qwiic**
   connector into the Modulino Buttons.
2. Plug a second Qwiic cable from the Buttons' other connector into the
   Modulino Buzzer (daisy-chain). Order does not matter.
3. The Qwiic connector is **3.3 V only**; use Qwiic/Modulino parts only.

## 3. First connection in App Lab

1. Open Arduino App Lab. Your board appears in the list; click it.
2. The first time, set the **board name**, **keyboard language** and
   **Wi‑Fi**, choose a password, and install any updates it offers.
3. Afterwards you can also connect over **Network Mode** (board shown with a
   Wi‑Fi/Network tag; enter the *board's* password). The board and computer
   must be on the same network.

Troubleshooting:
- **Linux computer:** App Lab needs USB permissions (udev rules) or it fails
  silently. See "Linux Host Setup" in the UNO Q user manual.
- **Windows:** allow `mdns-discovery.exe` through the firewall, or Network
  Mode won't find the board (it needs UDP port 5353).

## 4. Create the app

1. In App Lab, create a new app (e.g. "3 button buzzer").
2. Replace its files with the ones from this folder:

   | In your app | Copy from this folder |
   |---|---|
   | `sketch/sketch.ino` | `sketch/sketch.ino` |
   | `sketch/sketch.yaml` | `sketch/sketch.yaml` |
   | `python/main.py` | `python/main.py` |

   Do **not** use `../ButtonBuzzerLevels/ButtonBuzzerLevels.ino`; that is
   the Arduino IDE version and fails with `Modulino.h: No such file`.
3. Check the app has the **Arduino_Modulino** library. Copying
   `sketch.yaml` adds it; otherwise add it from the app's **Libraries**
   panel. If it is missing you get `Arduino_Modulino.h: No such file`.

## 5. Run it

1. Press **Run**. App Lab compiles and uploads the sketch, then starts
   `python/main.py`.
2. Hold button A, B or C: the buzzer plays at level 1, 2 or 3 and the LED
   above the button lights. Release to stop.
3. The console shows the Python log, e.g.
   `Holding button B (medium) -> level 2` and
   `Released B (medium) after 1.24 s`.

## Optional: run at startup

To start the app whenever the board powers on: open the app, click the arrow
(▼) next to its name, and turn on **Run at startup**. Or, in the board's
terminal:

```bash
arduino-app-cli properties set default user:<NAME_OF_YOUR_APP>
```

## Sources

- [UNO Q user manual](https://docs.arduino.cc/tutorials/uno-q/user-manual/)
- [VENTUNO Q user manual](https://docs.arduino.cc/tutorials/ventuno-q/user-manual/)
