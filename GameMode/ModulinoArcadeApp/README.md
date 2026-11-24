# Modulino Arcade (App Lab app)

Two games on the Arduino UNO Q / VENTUNO Q, played with a **Modulino Buttons**
and a **Modulino Buzzer**, shown on the board's **8×13 LED matrix**, with
scores and high scores in your browser.

| Button | Game | Score |
|---|---|---|
| **A** | **Reaction**: wait for a button's LED (and that third of the LED matrix) to light, press it as fast as you can. 5 rounds. Early, late or wrong presses add 1000 ms. | Average ms, lower is better |
| **B** | **Simon**: watch the lights and tones, repeat the sequence. It grows by one each round and speeds up. | Longest sequence |

You can also start a game from the browser page. The top 10 scores of each
game are saved on the board (`highscores.json` in the app folder).

## Setup
1. Connect the Modulino Buttons and Modulino Buzzer to the board's Qwiic
   connector (daisy-chain them). The buzzer is optional: without it the games
   are silent.
2. Import `ModulinoArcadeApp.zip` from [`GameMode/AppLabImports/`](../AppLabImports/)
   (GitHub's **Download raw file** button, then **Import app** in App Lab), or
   create a new app and copy in these files.
3. Press **Run**. The LED matrix shows a smiley and all three button LEDs light:
   it's ready.
4. Open the page: App Lab shows the Web UI link, or open
   `http://<board-name>.local:7000` (or `http://<board IP>:7000`). Over USB:
   `adb forward tcp:7000 tcp:7000`, then `http://127.0.0.1:7000`.

## Files
| File | Role |
|---|---|
| `sketch/sketch.ino` | The games: buttons, buzzer and LED matrix; reports to Python through the Bridge |
| `python/main.py` | High scores and the browser page (Web UI brick) |
| `assets/` | The browser page |
| `app.yaml`, `sketch/sketch.yaml` | App settings, Web UI brick, Modulino library |

The page loads Socket.IO from a CDN, so the browser needs internet.
