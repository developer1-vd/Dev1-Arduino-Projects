"""Arduino Claude Studio - a local WebUI for coding Arduino with Claude Code.

Run:  python app.py            (then open http://127.0.0.1:8765)

Two modes, picked automatically:
  arduino  On your computer: sketches in WORKSPACE, compiled and uploaded with
           arduino-cli to a board plugged in over USB.
  applab   On an Arduino UNO Q / VENTUNO Q (arduino-app-cli is present): the
           workspace is ~/ArduinoApps and projects are App Lab apps, run with
           App Lab's own engine.

Options (environment variables):
  MODE          arduino, applab or auto (default: auto)
  WORKSPACE     folder with your sketches (default: ./workspace, or
                ~/ArduinoApps in App Lab mode)
  PORT          web server port (default: 8765)
  CLAUDE_MODEL  model for the chat (default: claude-opus-5-5)
  ARDUINO_CLI   path to arduino-cli (default: arduino-cli on PATH)

The server only listens on 127.0.0.1: it can edit files and run arduino-cli
on this computer, so it must not be reachable from the network.
"""

from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from applab import AppLabCli, valid_app_name
from arduino import ArduinoCli, Hub, SerialMonitor
from claude_agent import ChatSession

HERE = Path(__file__).resolve().parent
APP_CLI = os.environ.get("ARDUINO_APP_CLI", "arduino-app-cli")
MODE = os.environ.get("MODE", "auto").lower()
if MODE == "auto":
    MODE = "applab" if shutil.which(APP_CLI) else "arduino"

default_ws = Path.home() / "ArduinoApps" if MODE == "applab" else HERE / "workspace"
WORKSPACE = Path(os.environ.get("WORKSPACE", default_ws)).resolve()
WORKSPACE.mkdir(parents=True, exist_ok=True)

SKIP_DIRS = {".git", "build", "__pycache__", "node_modules", ".claude", ".cache"}
MAX_FILE_BYTES = 1_000_000

hub = Hub()
cli = ArduinoCli(WORKSPACE, hub, os.environ.get("ARDUINO_CLI", "arduino-cli"))
monitor = SerialMonitor(hub)
applab = AppLabCli(WORKSPACE, hub, APP_CLI) if MODE == "applab" else None
app = FastAPI(title="Arduino Claude Studio")


def safe_path(rel: str) -> Path:
    """Resolve a path from the browser, refusing anything outside the workspace."""
    p = (WORKSPACE / rel).resolve()
    if p != WORKSPACE and WORKSPACE not in p.parents:
        raise HTTPException(400, "Path is outside the workspace")
    return p


# ---------------- files ----------------
@app.get("/api/info")
async def info() -> dict:
    return {"workspace": str(WORKSPACE), "mode": MODE,
            "arduino_cli": applab.available() if applab else cli.available(),
            "arduino_cli_path": "" if applab else cli.cli}


@app.get("/api/files")
async def list_files() -> list[str]:
    files = []
    for p in sorted(WORKSPACE.rglob("*")):
        rel = p.relative_to(WORKSPACE)
        if any(part in SKIP_DIRS or part.startswith(".") for part in rel.parts):
            continue
        if p.is_file() and p.stat().st_size <= MAX_FILE_BYTES:
            files.append(rel.as_posix())
    return files


@app.get("/api/file")
async def read_file(path: str) -> dict:
    p = safe_path(path)
    if not p.is_file():
        raise HTTPException(404, "File not found")
    return {"path": path, "content": p.read_text(errors="replace")}


class FileBody(BaseModel):
    path: str
    content: str


@app.put("/api/file")
async def write_file(body: FileBody) -> dict:
    p = safe_path(body.path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body.content)
    return {"ok": True}


class NewSketch(BaseModel):
    name: str


@app.post("/api/sketch")
async def new_sketch(body: NewSketch) -> dict:
    name = "".join(c for c in body.name if c.isalnum() or c in "_-")
    if not name or not name[0].isalpha():
        raise HTTPException(400, "Use letters, digits, _ or -, starting with a letter")
    folder = safe_path(name)
    ino = folder / f"{name}.ino"
    if ino.exists():
        raise HTTPException(409, "That sketch already exists")
    folder.mkdir(parents=True, exist_ok=True)
    ino.write_text("void setup() {\n  Serial.begin(9600);\n}\n\nvoid loop() {\n\n}\n")
    return {"path": ino.relative_to(WORKSPACE).as_posix()}


# ---------------- boards, compile, upload ----------------
@app.get("/api/boards")
async def boards() -> dict:
    if not cli.available():
        raise HTTPException(500, "arduino-cli not found - see README")
    connected, installed = await asyncio.gather(
        cli.list_boards(), cli.list_installed_boards(), return_exceptions=True)
    return {
        "connected": connected if isinstance(connected, list) else [],
        "installed": installed if isinstance(installed, list) else [],
    }


class BuildBody(BaseModel):
    sketch: str
    fqbn: str
    port: str | None = None


@app.post("/api/compile")
async def compile_sketch(body: BuildBody) -> dict:
    try:
        code, _ = await cli.compile(body.sketch, body.fqbn)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": code == 0}


@app.post("/api/upload")
async def upload_sketch(body: BuildBody) -> dict:
    if not body.port:
        raise HTTPException(400, "Select a port first")
    try:
        code, _ = await cli.upload(body.sketch, body.fqbn, body.port, monitor)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": code == 0}


# ---------------- App Lab mode: apps ----------------
def need_applab() -> AppLabCli:
    if applab is None:
        raise HTTPException(400, "Only available in App Lab mode")
    return applab


@app.get("/api/apps")
async def list_apps() -> list[dict]:
    try:
        return await need_applab().list_apps()
    except RuntimeError as exc:
        raise HTTPException(500, str(exc)) from exc


class AppName(BaseModel):
    name: str


@app.post("/api/apps/new")
async def new_app(body: AppName) -> dict:
    lab = need_applab()
    if not valid_app_name(body.name):
        raise HTTPException(400, "Use letters, digits, spaces, _ or -, starting with a letter")
    try:
        folder = await lab.new_app(body.name)
    except RuntimeError as exc:
        raise HTTPException(400, str(exc)) from exc
    main = WORKSPACE / folder / "python" / "main.py"
    return {"folder": folder,
            "path": main.relative_to(WORKSPACE).as_posix() if main.exists() else f"{folder}/app.yaml"}


class AppRef(BaseModel):
    app: str | None = None


@app.post("/api/apps/run")
async def run_app(body: AppRef) -> dict:
    if not body.app:
        raise HTTPException(400, "Open a file of the app first")
    try:
        code, _ = await need_applab().start(body.app)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": code == 0}


@app.post("/api/apps/stop")
async def stop_app(body: AppRef) -> dict:
    try:
        code, _ = await need_applab().stop(body.app or None)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": code == 0}


# ---------------- serial monitor ----------------
class SerialOpen(BaseModel):
    port: str
    baud: int = 9600


@app.post("/api/serial/open")
async def serial_open(body: SerialOpen) -> dict:
    try:
        if applab:
            await applab.open_monitor()
        else:
            await monitor.open(body.port, body.baud)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True}


@app.post("/api/serial/close")
async def serial_close() -> dict:
    if applab:
        await applab.close_monitor()
    else:
        await monitor.close()
    return {"ok": True}


class SerialSend(BaseModel):
    text: str


@app.post("/api/serial/send")
async def serial_send(body: SerialSend) -> dict:
    try:
        if applab:
            await applab.send_monitor(body.text)
        else:
            await monitor.write(body.text)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True}


# ---------------- websocket: chat + live events ----------------
@app.websocket("/ws")
async def websocket(ws: WebSocket) -> None:
    await ws.accept()
    hub.add(ws)
    session = ChatSession(ws, hub, cli, monitor, applab)
    task: asyncio.Task | None = None
    try:
        while True:
            msg = await ws.receive_json()
            kind = msg.get("type")
            if kind == "selection":
                session.selection.update({k: msg.get(k) for k in ("fqbn", "port", "baud", "file")})
            elif kind == "prompt":
                # Run in the background so permission answers and Stop still arrive
                task = asyncio.create_task(session.ask(msg.get("text", "")))
            elif kind == "interrupt":
                await session.interrupt()
            elif kind == "permission":
                session.answer_permission(msg.get("id", ""), bool(msg.get("allow")))
            elif kind == "reset":
                await session.reset()
    except WebSocketDisconnect:
        pass
    finally:
        hub.remove(ws)
        if task and not task.done():
            task.cancel()
        await session.close()


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(HERE / "static" / "index.html")


app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8765"))
    print(f"Arduino Claude Studio ({MODE} mode): http://127.0.0.1:{port}")
    print(f"Workspace: {WORKSPACE}")
    if MODE == "arduino":
        if cli.available():
            print(f"arduino-cli: {cli.cli}")
        else:
            print("arduino-cli NOT found. Add its folder to PATH, or start with")
            print("  ARDUINO_CLI=/full/path/to/arduino-cli ./run.sh")
    if MODE == "applab":
        print("On your computer, open it through an SSH tunnel:")
        print(f"  ssh -L {port}:127.0.0.1:{port} arduino@<board-name>.local")
    uvicorn.run(app, host="127.0.0.1", port=port)
