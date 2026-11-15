# Claude Studio (App Lab app)

Code your Arduino UNO Q / VENTUNO Q with Claude, from your computer's
browser. Import this app into Arduino App Lab, press **Run**, and open the
page it prints.

- **Editor** for this app's sketch (`sketch.ino`, `sketch.yaml`).
- **Claude chat**: ask Claude to write or fix the sketch; it edits the files
  directly and the editor updates.
- **Sketch output**: lines the sketch sends with `studioLog("...")`, live.
  Claude can read them too, to check that the code works.

## How it works, and its one limit

App Lab runs each app inside a container that can only see the app's own
folder, and can't compile or flash the microcontroller. So:

- Claude writes **this app's own sketch** (the "playground").
- To put the new code on the board, press **Stop** and then **Run** on Claude
  Studio in App Lab. App Lab compiles and flashes the sketch, and Claude
  Studio starts again with your conversation (reload the page if it doesn't
  reconnect by itself).
- If the sketch doesn't compile, App Lab shows the error in its console:
  paste it into the chat and Claude fixes it.

For a version where Claude compiles, flashes and runs any App Lab app
itself, run [Arduino Claude Studio](../ArduinoClaudeStudio/) on the board in
App Lab mode instead.

## Setup

1. **Import the app.** Download `ArduinoClaudeStudioApp.zip` from
   [`AIProjects/AppLabImports/`](../AppLabImports/) (GitHub's
   **Download raw file** button), then use **Import app** in App Lab.
2. **Run it.** The first run takes a few minutes: App Lab installs the
   Python packages (Claude Agent SDK, FastAPI) and the Modulino libraries.
3. **Open the page.** The app's console in App Lab prints a link like
   `http://<board-name>.local:8765/?code=Ab3dE...`. Replace `<board-name>`
   with your board's name (or use its IP address) and open it on a computer
   on the same network. The `code` is an access code, so only people with
   the link can use the page.

   **If the page doesn't open** ("can't resolve" or "site can't be reached"),
   your computer can't find the board by name. Either:
   - use the board's **IP address** instead of `<board-name>.local` (find it
     in your router's device list, or run `hostname -I` on the board), or
   - go over the **USB cable** with ADB: on the computer run
     `adb forward tcp:8765 tcp:8765`, then open
     `http://127.0.0.1:8765/?code=<access code>`. On Linux, first add the
     UNO Q USB permission rule from Arduino's UNO Q user manual
     ("Linux Host Setup") and replug the board, or `adb devices` won't list
     it.
4. **Connect Claude.** The page asks for one of:
   - an **Anthropic API key** (`sk-ant-api…`, from console.anthropic.com), or
   - a **Claude Code token** (`sk-ant-oat…`), to use your Claude
     subscription: on a computer with Claude Code, run `claude setup-token`
     and paste the token it shows.

   It's stored on the board in this app's `.studio` folder.

## Using it

1. Ask Claude something like "Blink the LED faster" or "Show the Modulino
   Distance reading every half second".
2. Claude edits `sketch.ino`. Check it in the editor.
3. In App Lab: **Stop**, then **Run** Claude Studio.
4. Watch **Sketch output**, or ask Claude "Is it working?" and it reads the
   output.

Rules Claude follows in the sketch (keep them if you edit it yourself):
- Keep `#include <Arduino_RouterBridge.h>`, `Bridge.begin();` and the
  `studioLog()` helper: they connect the sketch to Claude Studio.
- Use `studioLog("...")` to show things in Sketch output.
- Modulinos are on `Wire1`: `Modulino.begin(Wire1)`. The Arduino_Modulino
  library is already in `sketch.yaml`.

## Privacy and safety

- `.studio/` in the app folder holds the access code, your Claude key or
  token, and Claude's conversation. **Delete `.studio` before you export or
  share this app.**
- Claude can read and edit files in the sketch folder without asking.
  Anything else (shell commands, web access) shows an Allow / Deny prompt.
- Each chat message uses your Claude API credits or subscription; the chat
  shows the cost of each request.
- The page loads its editor from public CDNs, so the browser needs internet.

## Files

| File | Role |
|---|---|
| `app.yaml` | App name, icon, and port 8765 for the page |
| `python/main.py` | Starts the web server and receives `studioLog()` lines through the Bridge |
| `python/studio.py` | Web server, access code and Claude session (Claude Agent SDK) |
| `python/static/` | The web page |
| `python/requirements.txt` | Python packages App Lab installs |
| `sketch/sketch.ino` | The playground sketch Claude writes |
| `sketch/sketch.yaml` | Board platform and libraries |
