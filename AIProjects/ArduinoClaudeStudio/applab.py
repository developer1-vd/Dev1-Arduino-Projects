"""App Lab mode: run Arduino Claude Studio directly on an Arduino UNO Q or
VENTUNO Q and drive App Lab's own engine, `arduino-app-cli`.

In this mode the workspace is the board's apps folder (~/ArduinoApps), each
project is an App Lab app (app.yaml + python/main.py + optional sketch), and
"running" an app means `arduino-app-cli app start`, which compiles and
flashes the sketch to the microcontroller and starts the Python side, exactly
like pressing Run in App Lab.

Only one app can run at a time, so starting one stops whichever is running.
"""

from __future__ import annotations

import asyncio
import base64
import json
import re
import shutil
import time
from pathlib import Path
from typing import Any

from arduino import Hub


def app_id(folder: str) -> str:
    """App Lab ID for a folder in ~/ArduinoApps."""
    return "user:" + folder


def decode_id(encoded: Any) -> str:
    """arduino-app-cli prints IDs base64url-encoded ("user:MyApp" -> "dXNlcjpNeUFwcA")."""
    s = str(encoded or "")
    if ":" in s:
        return s
    try:
        decoded = base64.urlsafe_b64decode(s + "=" * (-len(s) % 4)).decode()
    except Exception:
        return s
    return decoded if ":" in decoded else s


class AppLabCli:
    def __init__(self, apps_dir: Path, hub: Hub, cli: str = "arduino-app-cli") -> None:
        self.workspace = apps_dir
        self.hub = hub
        self.cli = cli
        self.lock = asyncio.Lock()          # one start/stop at a time
        self._logs_task: asyncio.Task | None = None
        self._logs: list[tuple[float, str]] = []
        self._monitor: asyncio.subprocess.Process | None = None
        self._monitor_task: asyncio.Task | None = None
        self._serial: list[tuple[float, str]] = []

    def available(self) -> bool:
        return shutil.which(self.cli) is not None

    # ---------- helpers ----------
    def app_folder(self, name_or_path: str) -> str:
        """Accept 'MyApp', 'user:MyApp' or a file inside the app; return the folder name."""
        s = name_or_path.removeprefix("user:").strip("/")
        first = s.split("/")[0]
        p = (self.workspace / first).resolve()
        root = self.workspace.resolve()
        if p == root or root not in p.parents:
            raise ValueError("App must be a folder in the apps directory")
        if not (p / "app.yaml").is_file():
            raise ValueError(f"{first} is not an App Lab app (no app.yaml)")
        return first

    async def _run_json(self, *args: str) -> Any:
        proc = await asyncio.create_subprocess_exec(
            self.cli, *args, "--format", "json",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        out, err = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError((err or out).decode(errors="replace").strip()
                               or f"{self.cli} failed")
        return json.loads(out or b"{}")

    async def _stream(self, args: list[str], title: str) -> tuple[int, str]:
        """Run a command, streaming its output to the build log."""
        await self.hub.send({"type": "build_start", "title": title,
                             "command": " ".join([self.cli, *args])})
        lines: list[str] = []
        proc = await asyncio.create_subprocess_exec(
            self.cli, *args,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
        assert proc.stdout is not None
        async for raw in proc.stdout:
            # progress bars redraw with \r; keep the last state of each line
            line = raw.decode(errors="replace").rstrip("\n").split("\r")[-1]
            if line.strip():
                lines.append(line)
                await self.hub.send({"type": "build_line", "line": line})
        code = await proc.wait()
        await self.hub.send({"type": "build_end", "title": title, "ok": code == 0})
        return code, "\n".join(lines)

    # ---------- apps ----------
    async def list_apps(self) -> list[dict[str, Any]]:
        """User apps with their status: [{folder, name, status}]."""
        data = await self._run_json("app", "list")
        status: dict[str, str] = {}
        try:
            ps = await self._run_json("app", "ps", "--all")
            for a in ps.get("apps") or []:
                status[decode_id(a.get("id"))] = a.get("status", "")
        except Exception:
            pass
        apps = []
        for a in data.get("apps") or []:
            aid = decode_id(a.get("id"))
            if not aid.startswith("user:"):
                continue
            apps.append({"folder": aid.removeprefix("user:"),
                         "name": a.get("name", ""),
                         "status": status.get(aid, a.get("status", "")) or "stopped"})
        return apps

    async def running_app(self) -> str | None:
        ps = await self._run_json("app", "ps")
        for a in ps.get("apps") or []:
            if a.get("status") in ("running", "starting"):
                return decode_id(a.get("id"))
        return None

    async def new_app(self, name: str, description: str = "", icon: str = "") -> str:
        args = ["app", "new", name]
        if description:
            args += ["--description", description]
        if icon:
            args += ["--icon", icon]
        res = await self._run_json(*args)
        return Path(res.get("path", "")).name

    async def start(self, app: str) -> tuple[int, str]:
        folder = self.app_folder(app)
        async with self.lock:
            running = await self.running_app()
            if running and running != app_id(folder):
                await self._stream(["app", "stop", running], f"Stop {running}")
            elif running == app_id(folder):
                # restart so changes to the sketch or Python are picked up
                await self._stream(["app", "stop", running], f"Stop {running}")
            code, out = await self._stream(["app", "start", app_id(folder)],
                                           f"Run {folder}")
        if code == 0:
            await self.follow_logs(folder)
        await self.hub.send({"type": "apps_changed"})
        return code, out

    async def stop(self, app: str | None = None) -> tuple[int, str]:
        async with self.lock:
            target = app_id(self.app_folder(app)) if app else await self.running_app()
            if not target:
                return 0, "No app is running."
            res = await self._stream(["app", "stop", target], f"Stop {target}")
        await self.stop_logs()
        await self.hub.send({"type": "apps_changed"})
        return res

    # ---------- Python logs of the running app ----------
    async def follow_logs(self, folder: str) -> None:
        await self.stop_logs()
        self._logs_task = asyncio.create_task(self._follow(folder))

    async def stop_logs(self) -> None:
        if self._logs_task and not self._logs_task.done():
            self._logs_task.cancel()
        self._logs_task = None

    async def _follow(self, folder: str) -> None:
        proc = await asyncio.create_subprocess_exec(
            self.cli, "app", "logs", app_id(folder), "--follow", "--tail", "50",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
        await self.hub.send({"type": "log_status", "app": folder, "open": True})
        try:
            assert proc.stdout is not None
            async for raw in proc.stdout:
                line = raw.decode(errors="replace").rstrip("\n")
                self._logs.append((time.time(), line))
                del self._logs[:-2000]
                await self.hub.send({"type": "log_line", "line": line})
        except asyncio.CancelledError:
            pass
        finally:
            if proc.returncode is None:
                proc.terminate()
            await self.hub.send({"type": "log_status", "app": folder, "open": False})

    async def read_logs(self, seconds: float) -> list[str]:
        start = time.time()
        await asyncio.sleep(seconds)
        recent = [l for t, l in self._logs if t >= start]
        return recent or [l for _, l in self._logs[-100:]]

    # ---------- microcontroller serial monitor ----------
    async def open_monitor(self) -> None:
        if self._monitor and self._monitor.returncode is None:
            return
        self._monitor = await asyncio.create_subprocess_exec(
            self.cli, "monitor",
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        self._monitor_task = asyncio.create_task(self._read_monitor())
        await self.hub.send({"type": "serial_status", "open": True,
                             "port": "the microcontroller", "baud": ""})

    async def _read_monitor(self) -> None:
        proc = self._monitor
        assert proc and proc.stdout
        pending = b""
        try:
            while True:
                chunk = await proc.stdout.read(256)
                if not chunk:
                    break
                pending += chunk
                while b"\n" in pending:
                    line, pending = pending.split(b"\n", 1)
                    text = line.decode(errors="replace").rstrip("\r")
                    self._serial.append((time.time(), text))
                    del self._serial[:-2000]
                    await self.hub.send({"type": "serial_line", "line": text})
        finally:
            await self.hub.send({"type": "serial_status", "open": False})

    async def close_monitor(self) -> None:
        if self._monitor and self._monitor.returncode is None:
            self._monitor.terminate()
            await self._monitor.wait()
        self._monitor = None

    async def send_monitor(self, text: str) -> None:
        if not self._monitor or self._monitor.returncode is not None or not self._monitor.stdin:
            raise RuntimeError("Serial monitor is not open")
        self._monitor.stdin.write(text.encode())
        await self._monitor.stdin.drain()

    async def read_serial(self, seconds: float) -> list[str]:
        await self.open_monitor()
        start = time.time()
        await asyncio.sleep(seconds)
        return [l for t, l in self._serial if t >= start]


def valid_app_name(name: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9 _-]{0,63}", name))
