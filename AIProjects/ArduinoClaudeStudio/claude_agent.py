"""Claude side of Arduino Claude Studio.

One ChatSession per browser tab. It runs Claude Code through the Claude
Agent SDK with the workspace as its working directory, gives Claude a few
Arduino tools (list boards, compile, upload, read serial) and streams
everything Claude does back to the browser.

Permissions:
- Reading files and editing files inside the workspace are allowed.
- The Arduino tools and `arduino-cli` shell commands are allowed.
- Anything else (other shell commands, web access, ...) is shown in the
  WebUI as an Allow / Deny prompt.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
import warnings
from typing import Annotated, Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolPermissionContext,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    create_sdk_mcp_server,
    tool,
)

from applab import AppLabCli, valid_app_name
from arduino import ArduinoCli, Hub, SerialMonitor

# can_use_tool is meant to handle only the tools that ALLOWED_TOOLS doesn't
# cover, so the SDK's "shadowed" warning about those tools is expected.
warnings.filterwarnings("ignore", message="can_use_tool will not be invoked")

# Model used for chat; override with the CLAUDE_MODEL environment variable.
DEFAULT_MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-5-5")

SYSTEM_PROMPT_APPEND = """
You are the coding assistant inside Arduino Claude Studio, a local WebUI for
writing Arduino sketches and running them on a board connected to this
computer. The user sees an editor, a build log and a serial monitor next to
this chat.

Workspace rules:
- Your working directory is the sketch workspace. Each sketch is a folder
  whose main file has the same name: Blink/Blink.ino.
- Create and edit sketches with your file tools; the editor refreshes
  automatically.

Running code (use these tools, not your own shell commands, so the user sees
the output in the build log and serial monitor):
- mcp__arduino__list_boards: connected boards, their ports and FQBNs.
- mcp__arduino__compile: compile a sketch. Fix errors and compile again
  until it builds.
- mcp__arduino__upload: compile and upload to the board.
- mcp__arduino__serial_read: read the board's serial output for a few
  seconds, to check the sketch behaves as intended.
- Install missing libraries or cores with `arduino-cli lib install "<name>"`
  or `arduino-cli core install <core>`.

Default to the board, port and baud rate from the "Current selection" note in
the user's message. If no board is selected, call list_boards. Before
uploading, make sure the sketch compiles.

Hardware notes: on the Arduino UNO Q and VENTUNO Q (FQBN arduino:zephyr:...)
the Qwiic connector is Wire1, so Modulino sketches call Modulino.begin(Wire1).
Modulino sketches need the Arduino_Modulino library.
"""

# Tools that run without asking. Everything else goes to the WebUI prompt.
ALLOWED_TOOLS = [
    "Read", "Glob", "Grep", "Edit", "Write", "TodoWrite",
    "Bash(arduino-cli:*)",
    "mcp__arduino__list_boards",
    "mcp__arduino__compile",
    "mcp__arduino__upload",
    "mcp__arduino__serial_read",
]


APPLAB_PROMPT_APPEND = """
You are the coding assistant inside Arduino Claude Studio, running directly on
an Arduino UNO Q / VENTUNO Q in App Lab mode. The user sees an editor, a run
log, the app's Python log and the microcontroller's serial monitor next to
this chat.

Your working directory is the board's apps folder (~/ArduinoApps). Each
project is an App Lab app folder:
- app.yaml: name, description, icon, bricks (list; [] if none).
- python/main.py: required. Runs on Linux in a container. Pattern:
    from arduino.app_utils import App, Bridge
    def on_reading(value: int): print(value)
    Bridge.provide("on_reading", on_reading)   # sketch calls it
    App.run()                                   # or App.run(user_loop=loop)
  Bridge.call("name", args) calls a function the sketch provides.
- python/requirements.txt: optional pip packages.
- sketch/sketch.ino: optional, runs on the microcontroller (Zephyr core):
    #include <Arduino_RouterBridge.h>
    Bridge.begin(); Bridge.provide("name", fn); Bridge.notify("name", args...);
    Monitor.begin(); Monitor.println(...);   // shows in the serial monitor
- sketch/sketch.yaml: required with a sketch:
    profiles:
      default:
        platforms:
          - platform: arduino:zephyr
        libraries:
          - Arduino_Modulino (0.7.0)      # only if used, with its dependencies
    default_profile: default
  For Arduino_Modulino 0.7.0 also list these dependencies:
  ArduinoGraphics (1.1.4), Arduino_HS300x (1.0.0), Arduino_LPS22HB (1.0.2),
  Arduino_LSM6DSOX (1.1.2), Arduino_LTR381RGB (1.0.0),
  STM32duino VL53L4CD (1.0.5), STM32duino VL53L4ED (1.0.1), each written as
  "- dependency: Name (version)".
- Modulinos connect to the Qwiic connector, which is Wire1:
  #include <Arduino_Modulino.h> and Modulino.begin(Wire1).

Tools (use these, not shell commands, so the user sees the output):
- mcp__applab__list_apps: the user's apps and their status.
- mcp__applab__create_app: create a new app with App Lab's template, then
  edit its files.
- mcp__applab__run_app: compile and flash the sketch and start the app (like
  Run in App Lab). Stops any other running app first. Read the output: fix
  compile errors and run again until it starts.
- mcp__applab__stop_app: stop the running app.
- mcp__applab__read_app_logs: the running app's Python output.
- mcp__applab__serial_read: the microcontroller's Monitor output.

Only edit apps inside the apps folder. Don't edit or run examples. Starting an
app takes a while (it compiles the sketch); that's normal.
"""

APPLAB_ALLOWED_TOOLS = [
    "Read", "Glob", "Grep", "Edit", "Write", "TodoWrite",
    "mcp__applab__list_apps",
    "mcp__applab__create_app",
    "mcp__applab__run_app",
    "mcp__applab__stop_app",
    "mcp__applab__read_app_logs",
    "mcp__applab__serial_read",
]


def _text(s: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": s}]}


def _short(value: Any, limit: int = 4000) -> str:
    s = value if isinstance(value, str) else json.dumps(value, indent=2, default=str)
    return s if len(s) <= limit else s[:limit] + f"\n... ({len(s) - limit} more characters)"


class ChatSession:
    def __init__(self, ws: Any, hub: Hub, cli: ArduinoCli | None,
                 monitor: SerialMonitor | None, applab: AppLabCli | None = None) -> None:
        self.ws = ws
        self.hub = hub
        self.cli = cli
        self.monitor = monitor
        self.applab = applab   # set in App Lab mode (running on the board)
        self.selection: dict[str, Any] = {}  # fqbn, port, baud, file from the UI
        self.client: ClaudeSDKClient | None = None
        self.session_id: str | None = None
        self.busy = False
        self._pending: dict[str, asyncio.Future] = {}  # permission requests
        self._tool_names: dict[str, str] = {}          # tool_use_id -> name

    # ---------- sending to this browser ----------
    async def send(self, event: dict[str, Any]) -> None:
        try:
            await self.ws.send_json(event)
        except Exception:
            pass

    # ---------- Arduino tools for Claude ----------
    def _tools(self) -> list[Any]:
        sel = self.selection

        @tool("list_boards", "List the Arduino boards connected to this computer "
              "with their serial port and FQBN.", {})
        async def list_boards(args: dict[str, Any]) -> dict[str, Any]:
            boards = await self.cli.list_boards()
            return _text(json.dumps(boards, indent=2) if boards else
                         "No boards detected. Ask the user to plug the board in.")

        @tool("compile", "Compile a sketch with arduino-cli. Output also appears "
              "in the user's build log.", {
                  "sketch": Annotated[str, "Sketch folder relative to the workspace, e.g. Blink"],
                  "fqbn": Annotated[str, "Board FQBN; empty to use the selected board"],
              })
        async def compile_sketch(args: dict[str, Any]) -> dict[str, Any]:
            fqbn = args.get("fqbn") or sel.get("fqbn")
            if not fqbn:
                return _text("No board selected. Call list_boards or ask the user.")
            code, out = await self.cli.compile(args["sketch"], fqbn)
            return _text(("Compiled OK.\n" if code == 0 else "Compile FAILED.\n") + _short(out, 8000))

        @tool("upload", "Compile and upload a sketch to the connected board. "
              "Output also appears in the user's build log.", {
                  "sketch": Annotated[str, "Sketch folder relative to the workspace"],
                  "fqbn": Annotated[str, "Board FQBN; empty to use the selected board"],
                  "port": Annotated[str, "Serial port; empty to use the selected port"],
              })
        async def upload_sketch(args: dict[str, Any]) -> dict[str, Any]:
            fqbn = args.get("fqbn") or sel.get("fqbn")
            port = args.get("port") or sel.get("port")
            if not fqbn or not port:
                return _text("Board or port not selected. Call list_boards or ask the user.")
            code, out = await self.cli.upload(args["sketch"], fqbn, port, self.monitor)
            return _text(("Uploaded OK.\n" if code == 0 else "Upload FAILED.\n") + _short(out, 8000))

        @tool("serial_read", "Read what the board prints on its serial port for a "
              "few seconds (opens the serial monitor if needed).", {
                  "seconds": Annotated[float, "How long to listen, 1-30"],
                  "baud": Annotated[int, "Baud rate; 0 to use the selected one (default 9600)"],
              })
        async def serial_read(args: dict[str, Any]) -> dict[str, Any]:
            seconds = max(1.0, min(30.0, float(args.get("seconds") or 5)))
            port = sel.get("port")
            baud = int(args.get("baud") or sel.get("baud") or 9600)
            if not self.monitor.is_open_on(port or "") or self.monitor.baud != baud:
                if not port:
                    return _text("No port selected. Call list_boards or ask the user.")
                await self.monitor.open(port, baud)
            lines = await self.monitor.read_for(seconds)
            if not lines:
                return _text(f"No serial output in {seconds:.0f} s at {baud} baud.")
            return _text(_short("\n".join(lines[-300:]), 8000))

        return [list_boards, compile_sketch, upload_sketch, serial_read]

    # ---------- App Lab tools for Claude (App Lab mode) ----------
    def _applab_tools(self) -> list[Any]:
        lab = self.applab
        assert lab is not None

        @tool("list_apps", "List the user's App Lab apps (folder, name, status).", {})
        async def list_apps(args: dict[str, Any]) -> dict[str, Any]:
            return _text(json.dumps(await lab.list_apps(), indent=2))

        @tool("create_app", "Create a new App Lab app from App Lab's template. "
              "Returns its folder; then edit its files.", {
                  "name": Annotated[str, "App name: letters, digits, spaces, _ or -"],
                  "description": Annotated[str, "One-line description"],
              })
        async def create_app(args: dict[str, Any]) -> dict[str, Any]:
            name = (args.get("name") or "").strip()
            if not valid_app_name(name):
                return _text("Invalid name. Use letters, digits, spaces, _ or -, starting with a letter.")
            folder = await lab.new_app(name, args.get("description") or "")
            await self.hub.send({"type": "files_changed"})
            files = sorted(p.relative_to(lab.workspace).as_posix()
                           for p in (lab.workspace / folder).rglob("*") if p.is_file())
            return _text(f"Created app folder {folder}. Files:\n" + "\n".join(files))

        @tool("run_app", "Compile and flash the app's sketch and start the app, like "
              "Run in App Lab. Stops any other running app first.", {
                  "app": Annotated[str, "App folder name in the apps directory"],
              })
        async def run_app(args: dict[str, Any]) -> dict[str, Any]:
            code, out = await lab.start(args["app"])
            head = "App started.\n" if code == 0 else "App FAILED to start.\n"
            return _text(head + _short(out, 8000))

        @tool("stop_app", "Stop the running app.", {})
        async def stop_app(args: dict[str, Any]) -> dict[str, Any]:
            code, out = await lab.stop()
            return _text(_short(out, 2000))

        @tool("read_app_logs", "Read the running app's Python output for a few seconds.", {
            "seconds": Annotated[float, "How long to listen, 1-30"],
        })
        async def read_app_logs(args: dict[str, Any]) -> dict[str, Any]:
            seconds = max(1.0, min(30.0, float(args.get("seconds") or 5)))
            lines = await lab.read_logs(seconds)
            return _text(_short("\n".join(lines[-300:]), 8000) if lines else "No log output.")

        @tool("serial_read", "Read the microcontroller's serial (Monitor) output for a "
              "few seconds.", {
                  "seconds": Annotated[float, "How long to listen, 1-30"],
              })
        async def serial_read(args: dict[str, Any]) -> dict[str, Any]:
            seconds = max(1.0, min(30.0, float(args.get("seconds") or 5)))
            lines = await lab.read_serial(seconds)
            return _text(_short("\n".join(lines[-300:]), 8000) if lines
                         else f"No serial output in {seconds:.0f} s.")

        return [list_apps, create_app, run_app, stop_app, read_app_logs, serial_read]

    # ---------- permission prompt in the WebUI ----------
    async def _can_use_tool(self, name: str, tool_input: dict[str, Any],
                            ctx: ToolPermissionContext) -> Any:
        req_id = uuid.uuid4().hex
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        self._pending[req_id] = fut
        await self.send({"type": "permission_request", "id": req_id,
                         "tool": name, "input": _short(tool_input, 2000)})
        try:
            allow = await fut
        finally:
            self._pending.pop(req_id, None)
        if allow:
            return PermissionResultAllow()
        return PermissionResultDeny(message="The user denied this action in the WebUI.")

    def answer_permission(self, req_id: str, allow: bool) -> None:
        fut = self._pending.get(req_id)
        if fut and not fut.done():
            fut.set_result(allow)

    # ---------- Claude session ----------
    async def _ensure_client(self) -> ClaudeSDKClient:
        if self.client is None:
            if self.applab is not None:
                workspace, prompt = self.applab.workspace, APPLAB_PROMPT_APPEND
                servers = {"applab": create_sdk_mcp_server("applab", tools=self._applab_tools())}
                allowed = APPLAB_ALLOWED_TOOLS
            else:
                assert self.cli is not None
                workspace, prompt = self.cli.workspace, SYSTEM_PROMPT_APPEND
                servers = {"arduino": create_sdk_mcp_server("arduino", tools=self._tools())}
                allowed = ALLOWED_TOOLS
            options = ClaudeAgentOptions(
                cwd=str(workspace),
                model=DEFAULT_MODEL,
                system_prompt={"type": "preset", "preset": "claude_code",
                               "append": prompt},
                mcp_servers=servers,
                allowed_tools=allowed,
                permission_mode="default",
                can_use_tool=self._can_use_tool,
                # Don't load settings files: their allow rules or hooks could
                # bypass the WebUI's permission prompt.
                setting_sources=[],
                resume=self.session_id,
            )
            self.client = ClaudeSDKClient(options=options)
            await self.client.connect()
        return self.client

    async def reset(self) -> None:
        await self.close()
        self.session_id = None
        await self.send({"type": "chat_reset"})

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

    async def interrupt(self) -> None:
        if self.client is not None and self.busy:
            await self.client.interrupt()

    async def ask(self, text: str) -> None:
        if self.busy:
            await self.send({"type": "chat_error", "error": "Claude is still working."})
            return
        self.busy = True
        await self.send({"type": "chat_busy", "busy": True})
        try:
            client = await self._ensure_client()
            await client.query(self._with_context(text))
            async for msg in client.receive_response():
                await self._forward(msg)
        except Exception as exc:  # noqa: BLE001 - show any failure in the UI
            await self.send({"type": "chat_error", "error": f"{type(exc).__name__}: {exc}"})
            await self.close()  # start a fresh client next time
        finally:
            self.busy = False
            await self.send({"type": "chat_busy", "busy": False})

    def _with_context(self, text: str) -> str:
        s = self.selection
        if self.applab is not None:
            return text + (f"\n\n[Current selection in the WebUI - open file: "
                           f"{s.get('file') or 'none'}]")
        note = (
            "\n\n[Current selection in the WebUI - "
            f"open file: {s.get('file') or 'none'}; "
            f"board FQBN: {s.get('fqbn') or 'none'}; "
            f"port: {s.get('port') or 'none'}; "
            f"baud: {s.get('baud') or 9600}]"
        )
        return text + note

    async def _forward(self, msg: Any) -> None:
        if isinstance(msg, SystemMessage):
            if msg.subtype == "init":
                self.session_id = msg.data.get("session_id", self.session_id)
            return
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock) and block.text.strip():
                    await self.send({"type": "assistant_text", "text": block.text})
                elif isinstance(block, ToolUseBlock):
                    self._tool_names[block.id] = block.name
                    await self.send({"type": "tool_use", "id": block.id,
                                     "name": block.name, "input": _short(block.input, 2000)})
            return
        if isinstance(msg, UserMessage) and isinstance(msg.content, list):
            for block in msg.content:
                if isinstance(block, ToolResultBlock):
                    name = self._tool_names.get(block.tool_use_id, "")
                    content = block.content
                    if isinstance(content, list):
                        content = "\n".join(c.get("text", "") for c in content
                                            if isinstance(c, dict))
                    await self.send({"type": "tool_result", "id": block.tool_use_id,
                                     "is_error": bool(block.is_error),
                                     "content": _short(content or "", 3000)})
                    if name in ("Write", "Edit", "NotebookEdit") or name.startswith("Bash"):
                        await self.hub.send({"type": "files_changed"})
            return
        if isinstance(msg, ResultMessage):
            self.session_id = msg.session_id or self.session_id
            await self.send({"type": "result", "is_error": msg.is_error,
                             "cost_usd": msg.total_cost_usd,
                             "duration_ms": msg.duration_ms, "turns": msg.num_turns})
