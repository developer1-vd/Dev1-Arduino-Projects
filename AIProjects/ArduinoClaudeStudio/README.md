# Arduino Claude Studio

A local WebUI for writing Arduino code with Claude Code and running it on a
board connected to your computer.

- **Editor:** your sketches, with syntax highlighting.
- **Compile / Upload buttons:** uses `arduino-cli`. You can also pick the
  board and port from the toolbar.
- **Serial monitor:** read the board's output and send text to it.
- **Claude chat:** Claude Code, running locally through the Claude Agent SDK.
  It can write and edit sketches, compile them, fix errors, upload to the
  board and read the serial output to check the result. Everything it runs
  appears in the build log and serial monitor, and the editor updates when it
  changes a file.

```
┌ Board ▾  Port ▾  ↻                          Save  ✓ Compile  → Upload ┐
├───────────┬─────────────────────────────────┬────────────────────────┤
│ Sketches  │ Blink/Blink.ino                 │ Claude                 │
│  Blink    │ void setup() { ... }            │ > make the LED blink   │
│  ...      │                                 │   twice as fast        │
│           ├─────────────────────────────────┤ ▸ Edit Blink.ino  ✓    │
│           │ Build log | Serial monitor      │ ▸ arduino.upload  ✓    │
│           │ Sketch uses 52000 bytes ...     │ Done in 14 s           │
└───────────┴─────────────────────────────────┴────────────────────────┘
```

It has two modes, picked automatically:

| Mode | Runs on | Projects | Run with |
|---|---|---|---|
| **Computer mode** | Windows / macOS / Linux, board plugged in over USB | Arduino sketches | `arduino-cli` |
| **App Lab mode** | The Arduino UNO Q / VENTUNO Q itself | App Lab apps (sketch + Python) in `~/ArduinoApps` | App Lab's engine, `arduino-app-cli` |

App Lab mode is described in [On the UNO Q / VENTUNO Q (App Lab mode)](#on-the-uno-q--ventuno-q-app-lab-mode).
It isn't an app you import into App Lab: App Lab apps run in a container
that can't compile, flash or start apps, so Studio runs next to App Lab on
the board instead.

## Requirements (computer mode)

1. **Python 3.10+**
2. **arduino-cli**: install it from <https://arduino.github.io/arduino-cli/latest/installation/>,
   then install the core for your board, for example:
   ```bash
   arduino-cli core update-index
   ```
   ```bash
   arduino-cli core install arduino:renesas_uno
   ```
   For the UNO Q / VENTUNO Q microcontroller: `arduino-cli core install arduino:zephyr`.
   You can also just ask Claude in the app to install a core or library.
3. **Claude access:** either log in once with Claude Code (`claude` then
   `/login`), or set an `ANTHROPIC_API_KEY` environment variable. The Claude
   Agent SDK includes Claude Code, so you don't need to install it
   separately.

## Run it

macOS / Linux:
```bash
./run.sh
```

Windows:
```bat
run.bat
```

The first run creates a `.venv` folder and installs the Python packages
(`claude-agent-sdk`, `fastapi`, `uvicorn[standard]`, `pyserial`). Then open
<http://127.0.0.1:8765>.

Manual alternative:
```bash
pip install -r requirements.txt
```
```bash
python app.py
```

### Settings (environment variables)

| Variable | Default | What it does |
|---|---|---|
| `MODE` | `auto` | `arduino` (computer mode), `applab` (on the board) or `auto` (App Lab mode if `arduino-app-cli` is installed). |
| `WORKSPACE` | `./workspace` (`~/ArduinoApps` in App Lab mode) | Folder with your sketches. Point it at another folder to work on those, e.g. `WORKSPACE=../../ModulinoProjects ./run.sh`. |
| `PORT` | `8765` | Web server port. |
| `CLAUDE_MODEL` | `claude-opus-5-5` | Model for the chat. |
| `ARDUINO_CLI` | `arduino-cli` | Path to `arduino-cli` if it isn't on your PATH. |

## Using it

1. Plug in the board and press **↻**. The connected board and its port are
   selected automatically. You can also pick a board from the
   "All installed boards" list.
2. Open a sketch on the left, or press **＋** for a new one. A sketch is a
   folder whose `.ino` file has the same name, like `Blink/Blink.ino`.
3. Use **Compile** and **Upload**, and the **Serial monitor** tab, as in the
   Arduino IDE. Upload closes the serial monitor while uploading and reopens
   it afterwards.
4. Or ask Claude, for example:
   - "Make a sketch that fades the LED on pin 9 and upload it."
   - "This doesn't compile, fix it."
   - "Upload Blink and check from the serial output that it's working."
   - "Install the Arduino_Modulino library and write a sketch that shows the
     Modulino Distance reading."

Claude always gets the selected board, port, baud rate and open file with
your message. **New chat** starts a fresh conversation, and **Stop**
interrupts Claude.

## On the UNO Q / VENTUNO Q (App Lab mode)

Run Studio on the board's Linux and it switches to App Lab mode by itself
(it finds `arduino-app-cli`). Then:

- The file list shows your App Lab apps from `~/ArduinoApps`, the same apps
  you see in App Lab. **＋** creates a new app from App Lab's template.
- **▶ Run app** runs the app of the open file, exactly like Run in App Lab:
  it compiles and flashes the sketch and starts the Python side. Any other
  running app is stopped first, because only one app can run at a time.
  **■ Stop app** stops it.
- **Run log** shows the start output (compile errors appear here), **App log**
  shows the Python output, and **Serial monitor** shows the
  microcontroller's `Monitor` output.
- Claude can create apps, write the sketch and Python, run them, fix errors
  and read the logs and serial output to check the result.

### Setup on the board

You need a terminal on the board: open one on the board's desktop
(single-board-computer mode), or connect from your computer with
`ssh arduino@<board-name>.local` (the board name is the one you set in App
Lab, and the password is the board's password).

1. Get the project onto the board (if the repository is private, `git clone`
   asks for your GitHub login; or copy the `ArduinoClaudeStudio` folder over
   with `scp -r`):
   ```bash
   git clone https://github.com/developer1-vd/Dev1-Arduino-Projects.git
   ```
   ```bash
   cd Dev1-Arduino-Projects/AIProjects/ArduinoClaudeStudio
   ```
2. If `python3 -m venv` complains that venv is missing, install it:
   ```bash
   sudo apt install -y python3-venv
   ```
3. Give it access to Claude, either with an API key:
   ```bash
   export ANTHROPIC_API_KEY=<your key>
   ```
   or by installing Claude Code and logging in once (`claude`, then `/login`):
   ```bash
   curl -fsSL https://claude.ai/install.sh | bash
   ```
4. Start it:
   ```bash
   ./run.sh
   ```

### Open it in your browser

On the board's own desktop, open <http://127.0.0.1:8765>.

From your computer, Studio is reachable only through an SSH tunnel, so
nobody else on your network can use it. Run this on your computer, keep it
open, then open <http://127.0.0.1:8765>:

```bash
ssh -L 8765:127.0.0.1:8765 arduino@<board-name>.local
```

### Notes for App Lab mode

- Leave App Lab itself idle while Studio runs an app, or stop the app in one
  before starting it in the other. They control the same board.
- Starting an app takes a while (it compiles the Modulino libraries); that's
  the same wait as in App Lab.
- On the board Studio uses Claude through the network, and the board needs
  internet access (the same Wi-Fi you set up in App Lab).

## What Claude may do

Claude runs on your computer, so the app limits what it can do without
asking:

| Allowed without asking | Asks you first (Allow / Deny in the chat) |
|---|---|
| Read, search and edit files in the workspace | Any other shell command |
| Computer mode: `arduino-cli` commands (compile, upload, install libraries and cores) | Web access and other tools |
| Computer mode: the Arduino tools (list boards, compile, upload, read serial) | |
| App Lab mode: the App Lab tools (list, create, run and stop apps, read logs and serial) | |

Claude Code settings files (`~/.claude/settings.json` and project settings)
are not loaded, so their allow rules or hooks can't bypass these prompts.
The web server only listens on `127.0.0.1`, so only this computer can use
it.

## How it works

| File | Role |
|---|---|
| `app.py` | FastAPI server: file API, compile/upload/serial endpoints, and a WebSocket for chat and live output. |
| `claude_agent.py` | One Claude Code session per browser tab through `ClaudeSDKClient`. It adds Arduino tools as an in-process MCP server and turns permission requests into Allow/Deny prompts. |
| `arduino.py` | `arduino-cli` wrapper and serial monitor. Output is streamed to every open browser tab. |
| `applab.py` | App Lab mode: drives `arduino-app-cli` (list, create, start and stop apps, Python logs, microcontroller monitor). |
| `static/` | The WebUI (CodeMirror editor, chat, consoles). Loaded from CDNs, so the browser needs internet. |
| `workspace/` | Your sketches (starts with `Blink`). |

Claude's Arduino tools (`mcp__arduino__*`) are the same functions the
buttons use, so anything Claude compiles or uploads shows up in the build log.

## Notes

- **Cost:** each chat message uses your Claude plan or API credits. The
  chat shows the cost of each request.
- **UNO Q / VENTUNO Q from your computer:** in computer mode, `arduino-cli`
  programs the board's microcontroller only. To work on App Lab apps with a
  Python side, run Studio on the board in App Lab mode.
- **Serial port busy:** only one program can use the port at a time. Close
  the Arduino IDE's Serial Monitor (or any other serial program) before
  uploading from here.
