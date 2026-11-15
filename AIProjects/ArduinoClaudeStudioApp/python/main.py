"""Claude Studio - App Lab app entry point.

Starts the Claude Studio web server on port 8765 and receives the sketch's
studioLog() lines through the Bridge.

Open the link printed below (App Lab shows it in the app's console):
    http://<board-name>.local:8765/?code=<access code>
"""

import threading

import uvicorn
from arduino.app_utils import App, Bridge

import studio

PORT = 8765


def run_server() -> None:
    # 0.0.0.0 inside the container: App Lab maps port 8765 to the board
    uvicorn.run(studio.app, host="0.0.0.0", port=PORT, log_level="warning")


def studio_log(line: str) -> None:
    """Called by the sketch: studioLog("...") -> Bridge.notify("studio_log", ...)."""
    studio.hub.sketch_line(str(line))


Bridge.provide("studio_log", studio_log)
threading.Thread(target=run_server, daemon=True).start()

code = studio.access_code()
print("=" * 60)
print("Claude Studio is running. Open it from a computer on the same network:")
print(f"  http://<board-name>.local:{PORT}/?code={code}")
print("  If that name doesn't open, use the board's IP address instead:")
print(f"  http://<board IP>:{PORT}/?code={code}")
print("  Or over the USB cable: run  adb forward tcp:8765 tcp:8765  on the")
print(f"  computer, then open  http://127.0.0.1:{PORT}/?code={code}")
print(f"Access code: {code}")
print("=" * 60, flush=True)

App.run()
