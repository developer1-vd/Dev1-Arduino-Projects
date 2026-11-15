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

## Requirements

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
| `WORKSPACE` | `./workspace` | Folder with your sketches. Point it at another folder to work on those, e.g. `WORKSPACE=../../ModulinoProjects ./run.sh`. |
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

## What Claude may do

Claude runs on your computer, so the app limits what it can do without
asking:

| Allowed without asking | Asks you first (Allow / Deny in the chat) |
|---|---|
| Read, search and edit files in the workspace | Any other shell command |
| `arduino-cli` commands (compile, upload, install libraries and cores) | Web access and other tools |
| The app's Arduino tools: list boards, compile, upload, read serial | |

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
| `static/` | The WebUI (CodeMirror editor, chat, consoles). Loaded from CDNs, so the browser needs internet. |
| `workspace/` | Your sketches (starts with `Blink`). |

Claude's Arduino tools (`mcp__arduino__*`) are the same functions the
buttons use, so anything Claude compiles or uploads shows up in the build log.

## Notes

- **Cost:** each chat message uses your Claude plan or API credits. The
  chat shows the cost of each request.
- **UNO Q / VENTUNO Q:** `arduino-cli` (and so this app) programs the
  board's microcontroller only. App Lab apps with a Python side still run
  from Arduino App Lab.
- **Serial port busy:** only one program can use the port at a time. Close
  the Arduino IDE's Serial Monitor (or any other serial program) before
  uploading from here.
