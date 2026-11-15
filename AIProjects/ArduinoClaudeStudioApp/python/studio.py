"""Claude Studio - the web server and Claude session behind the App Lab app.

Runs inside the app's container on the UNO Q / VENTUNO Q. App Lab apps can
only see their own folder (/app), so Claude edits this app's own sketch in
/app/sketch; you flash it with Stop + Run in App Lab. The sketch reports back
with studioLog("..."), which arrives here through the Bridge.

Security:
- The page is reachable on your network (port 8765), so every request needs
  the access code printed in the app's console (stored in /app/.studio).
- Claude may read and edit files in the sketch folder; anything else asks you
  with Allow / Deny in the chat.
"""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import time
import uuid
import warnings
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

APP_DIR = Path(os.environ.get("STUDIO_APP_DIR", "/app"))
SKETCH_DIR = APP_DIR / "sketch"
STATE_DIR = APP_DIR / ".studio"
STATIC_DIR = Path(__file__).resolve().parent / "static"
MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-5-5")

warnings.filterwarnings("ignore", message="can_use_tool will not be invoked")


# ---------------- persistent state (access code, Claude credential) ----------------
def _state_file(name: str) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR / name


def access_code() -> str:
    f = _state_file("access_code")
    if not f.exists():
        f.write_text(secrets.token_urlsafe(9))
        f.chmod(0o600)
    return f.read_text().strip()


def load_credential() -> str | None:
    f = _state_file("claude_credential")
    return f.read_text().strip() if f.exists() else None


def save_credential(value: str) -> None:
    f = _state_file("claude_credential")
    f.write_text(value.strip())
    f.chmod(0o600)


def credential_env(value: str) -> dict[str, str]:
    """A Claude Code token (from `claude setup-token`) or an API key."""
    if value.startswith("sk-ant-oat"):
        return {"CLAUDE_CODE_OAUTH_TOKEN": value}
    return {"ANTHROPIC_API_KEY": value}


def claude_env(cred: str) -> dict[str, str]:
    """Environment for Claude Code. App Lab recreates the container on every
    Run, so Claude's config and conversations live in the app folder."""
    home = STATE_DIR / "home"
    (home / ".claude").mkdir(parents=True, exist_ok=True)
    return {**credential_env(cred), "HOME": str(home),
            "CLAUDE_CONFIG_DIR": str(home / ".claude")}


# ---------------- events to the browser ----------------
class Hub:
    def __init__(self) -> None:
        self.sockets: set[WebSocket] = set()
        self.loop: asyncio.AbstractEventLoop | None = None
        self.sketch_log: list[tuple[float, str]] = []

    async def send(self, event: dict[str, Any]) -> None:
        for ws in list(self.sockets):
            try:
                await ws.send_json(event)
            except Exception:
                self.sockets.discard(ws)

    def sketch_line(self, line: str) -> None:
        """Called from the Bridge thread when the sketch calls studioLog()."""
        self.sketch_log.append((time.time(), line))
        del self.sketch_log[:-2000]
        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self.send({"type": "sketch_line", "line": line}), self.loop)


hub = Hub()


# ---------------- Claude ----------------
SYSTEM_PROMPT_APPEND = """
You are the coding assistant inside Claude Studio, an Arduino App Lab app on
an Arduino UNO Q / VENTUNO Q. The user sees an editor, a "Sketch output"
panel and this chat in their browser.

Your working directory is this app's sketch folder. You write the
microcontroller code in sketch.ino (Arduino, Zephyr core). You can't compile
or flash it yourself: when the code is ready, tell the user to press Stop and
then Run in App Lab, which compiles and flashes it (Claude Studio restarts
with this chat). If it fails to compile, App Lab shows the error and the user
can paste it here.

Rules for sketch.ino:
- Keep `#include <Arduino_RouterBridge.h>`, the studioLog() helper and
  `Bridge.begin();` at the start of setup(). Use studioLog("...") (it takes a
  String) for anything the user should see; it appears in Sketch output.
  Don't use Serial or Monitor for that.
- Modulino nodes connect to the Qwiic connector, which is Wire1:
  #include <Arduino_Modulino.h>, then Modulino.begin(Wire1). The
  Arduino_Modulino library is already in sketch.yaml.
- To use another library, add it to sketch.yaml under libraries, as
  "- Name (version)".
- Don't block in loop() for long; prefer millis() timing.

Use mcp__studio__read_sketch_output to see what the running sketch printed
with studioLog, e.g. after the user has flashed it.
"""

ALLOWED_TOOLS = ["Read", "Glob", "Grep", "Edit", "Write", "TodoWrite",
                 "mcp__studio__read_sketch_output"]


def _short(value: Any, limit: int = 3000) -> str:
    s = value if isinstance(value, str) else json.dumps(value, indent=2, default=str)
    return s if len(s) <= limit else s[:limit] + f"\n... ({len(s) - limit} more characters)"


class ChatSession:
    def __init__(self, ws: WebSocket) -> None:
        self.ws = ws
        self.client: Any = None
        self.busy = False
        self.file: str | None = None
        self._pending: dict[str, asyncio.Future] = {}
        self._tool_names: dict[str, str] = {}

    async def send(self, event: dict[str, Any]) -> None:
        try:
            await self.ws.send_json(event)
        except Exception:
            pass

    @staticmethod
    def _session_file() -> Path:
        return _state_file("session_id")

    def _tools(self) -> list[Any]:
        from claude_agent_sdk import tool

        @tool("read_sketch_output", "Read the lines the running sketch sends with "
              "studioLog(). Waits a few seconds to collect new lines.", {
                  "seconds": Annotated[float, "How long to listen, 1-30"],
              })
        async def read_sketch_output(args: dict[str, Any]) -> dict[str, Any]:
            seconds = max(1.0, min(30.0, float(args.get("seconds") or 5)))
            start = time.time()
            await asyncio.sleep(seconds)
            new = [l for t, l in hub.sketch_log if t >= start]
            text = ("\n".join(new[-300:]) if new else
                    "No new output. Recent lines:\n" +
                    "\n".join(l for _, l in hub.sketch_log[-50:])
                    if hub.sketch_log else
                    "No output yet. The sketch may not be flashed or may not call studioLog().")
            return {"content": [{"type": "text", "text": _short(text, 8000)}]}

        return [read_sketch_output]

    async def _can_use_tool(self, name: str, tool_input: dict[str, Any], ctx: Any) -> Any:
        from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny
        req_id = uuid.uuid4().hex
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        self._pending[req_id] = fut
        await self.send({"type": "permission_request", "id": req_id,
                         "tool": name, "input": _short(tool_input, 2000)})
        try:
            allow = await fut
        finally:
            self._pending.pop(req_id, None)
        return PermissionResultAllow() if allow else PermissionResultDeny(
            message="The user denied this action in Claude Studio.")

    def answer_permission(self, req_id: str, allow: bool) -> None:
        fut = self._pending.get(req_id)
        if fut and not fut.done():
            fut.set_result(allow)

    async def _connect(self) -> Any:
        from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, create_sdk_mcp_server
        if self.client is None:
            cred = load_credential()
            if not cred:
                raise RuntimeError("Add your Claude API key or token first (⚙ button).")
            sf = self._session_file()
            resume = sf.read_text().strip() if sf.exists() else None
            options = ClaudeAgentOptions(
                cwd=str(SKETCH_DIR),
                model=MODEL,
                system_prompt={"type": "preset", "preset": "claude_code",
                               "append": SYSTEM_PROMPT_APPEND},
                mcp_servers={"studio": create_sdk_mcp_server("studio", tools=self._tools())},
                allowed_tools=ALLOWED_TOOLS,
                permission_mode="default",
                can_use_tool=self._can_use_tool,
                setting_sources=[],
                env=claude_env(cred),
                resume=resume or None,
            )
            self.client = ClaudeSDKClient(options=options)
            try:
                await self.client.connect()
            except Exception:
                # the saved conversation may be gone; start a new one
                self.client = None
                if resume:
                    sf.unlink(missing_ok=True)
                    return await self._connect()
                raise
        return self.client

    async def close(self) -> None:
        for fut in self._pending.values():
            if not fut.done():
                fut.set_result(False)
        if self.client is not None:
            try:
                await self.client.disconnect()
            except Exception:
                pass
            self.client = None

    async def reset(self) -> None:
        await self.close()
        self._session_file().unlink(missing_ok=True)
        await self.send({"type": "chat_reset"})

    async def interrupt(self) -> None:
        if self.client is not None and self.busy:
            await self.client.interrupt()

    async def ask(self, text: str) -> None:
        from claude_agent_sdk import (AssistantMessage, ResultMessage, SystemMessage,
                                      TextBlock, ToolResultBlock, ToolUseBlock, UserMessage)
        if self.busy:
            return
        self.busy = True
        await self.send({"type": "chat_busy", "busy": True})
        try:
            client = await self._connect()
            note = f"\n\n[Open file in the editor: {self.file or 'none'}]"
            await client.query(text + note)
            async for msg in client.receive_response():
                if isinstance(msg, SystemMessage) and msg.subtype == "init":
                    sid = msg.data.get("session_id")
                    if sid:
                        self._session_file().write_text(sid)
                elif isinstance(msg, AssistantMessage):
                    for b in msg.content:
                        if isinstance(b, TextBlock) and b.text.strip():
                            await self.send({"type": "assistant_text", "text": b.text})
                        elif isinstance(b, ToolUseBlock):
                            self._tool_names[b.id] = b.name
                            await self.send({"type": "tool_use", "id": b.id, "name": b.name,
                                             "input": _short(b.input, 2000)})
                elif isinstance(msg, UserMessage) and isinstance(msg.content, list):
                    for b in msg.content:
                        if isinstance(b, ToolResultBlock):
                            content = b.content
                            if isinstance(content, list):
                                content = "\n".join(c.get("text", "") for c in content
                                                    if isinstance(c, dict))
                            await self.send({"type": "tool_result", "id": b.tool_use_id,
                                             "is_error": bool(b.is_error),
                                             "content": _short(content or "")})
                            if self._tool_names.get(b.tool_use_id) in ("Write", "Edit"):
                                await hub.send({"type": "files_changed"})
                elif isinstance(msg, ResultMessage):
                    if msg.session_id:
                        self._session_file().write_text(msg.session_id)
                    await self.send({"type": "result", "is_error": msg.is_error,
                                     "cost_usd": msg.total_cost_usd,
                                     "duration_ms": msg.duration_ms})
        except Exception as exc:  # noqa: BLE001
            await self.send({"type": "chat_error", "error": f"{type(exc).__name__}: {exc}"})
            await self.close()
        finally:
            self.busy = False
            await self.send({"type": "chat_busy", "busy": False})


# ---------------- web server ----------------
app = FastAPI(title="Claude Studio")


@app.middleware("http")
async def require_code(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/"):
        code = request.headers.get("x-access-code") or request.cookies.get("studio_code")
        if not code or not secrets.compare_digest(code, access_code()):
            return JSONResponse({"detail": "Wrong or missing access code"}, status_code=401)
    return await call_next(request)


def sketch_path(rel: str) -> Path:
    p = (SKETCH_DIR / rel).resolve()
    if p != SKETCH_DIR.resolve() and SKETCH_DIR.resolve() not in p.parents:
        raise HTTPException(400, "Only files in the sketch folder can be opened")
    return p


@app.get("/api/info")
async def info() -> dict:
    return {"has_credential": bool(load_credential()), "model": MODEL}


@app.get("/api/files")
async def files() -> list[str]:
    return sorted(p.relative_to(SKETCH_DIR).as_posix() for p in SKETCH_DIR.rglob("*")
                  if p.is_file() and ".cache" not in p.parts and p.stat().st_size < 1_000_000)


@app.get("/api/file")
async def read_file(path: str) -> dict:
    p = sketch_path(path)
    if not p.is_file():
        raise HTTPException(404, "File not found")
    return {"path": path, "content": p.read_text(errors="replace")}


class FileBody(BaseModel):
    path: str
    content: str


@app.put("/api/file")
async def write_file(body: FileBody) -> dict:
    sketch_path(body.path).write_text(body.content)
    return {"ok": True}


class Credential(BaseModel):
    value: str


@app.put("/api/credential")
async def set_credential(body: Credential) -> dict:
    if not body.value.strip().startswith("sk-ant-"):
        raise HTTPException(400, "That doesn't look like a Claude API key or token (sk-ant-...)")
    save_credential(body.value)
    return {"ok": True}


@app.get("/api/sketch-output")
async def sketch_output() -> list[str]:
    return [l for _, l in hub.sketch_log[-500:]]


@app.websocket("/ws")
async def websocket(ws: WebSocket) -> None:
    code = ws.query_params.get("code") or ws.cookies.get("studio_code")
    if not code or not secrets.compare_digest(code, access_code()):
        await ws.close(code=4401)
        return
    await ws.accept()
    hub.loop = asyncio.get_running_loop()
    hub.sockets.add(ws)
    session = ChatSession(ws)
    task: asyncio.Task | None = None
    try:
        while True:
            msg = await ws.receive_json()
            kind = msg.get("type")
            if kind == "selection":
                session.file = msg.get("file")
            elif kind == "prompt":
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
        hub.sockets.discard(ws)
        if task and not task.done():
            task.cancel()
        await session.close()


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
