"""Arduino side of Arduino Claude Studio.

Wraps `arduino-cli` (board detection, compile, upload, libraries) and a
serial monitor, and broadcasts their output to every connected browser
through the shared Hub. The same functions are used by the WebUI buttons
and by the tools Claude calls, so you always see what Claude runs.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import threading
import time
from pathlib import Path
from typing import Any, Awaitable, Callable

try:
    import serial  # pyserial
except ImportError:  # pragma: no cover - reported at runtime
    serial = None

Broadcast = Callable[[dict[str, Any]], Awaitable[None]]


class Hub:
    """Fan-out of events to every connected browser websocket."""

    def __init__(self) -> None:
        self._sockets: set[Any] = set()

    def add(self, ws: Any) -> None:
        self._sockets.add(ws)

    def remove(self, ws: Any) -> None:
        self._sockets.discard(ws)

    async def send(self, event: dict[str, Any]) -> None:
        dead = []
        for ws in list(self._sockets):
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._sockets.discard(ws)


def find_arduino_cli(name: str = "arduino-cli") -> str | None:
    """Find arduino-cli on PATH or in the places installers usually put it.

    Arduino's install script puts it in ./bin of the folder you ran it from,
    which often isn't on PATH, so look there too.
    """
    if Path(name).expanduser().is_file():
        return str(Path(name).expanduser())
    if found := shutil.which(name):
        return found
    exe = name + (".exe" if os.name == "nt" else "")
    home = Path.home()
    here = Path(__file__).resolve().parent
    candidates = [
        Path.cwd() / "bin", here / "bin", home / "bin", home / ".local" / "bin",
        home / "Downloads" / "bin", Path("/usr/local/bin"), Path("/opt/homebrew/bin"),
        Path("/snap/bin"), home / "go" / "bin",
        home / "AppData" / "Local" / "Programs" / "Arduino CLI",
        Path("C:/Program Files/Arduino CLI"),
    ]
    for folder in candidates:
        if (folder / exe).is_file():
            return str(folder / exe)
    return None


class ArduinoCli:
    """Runs arduino-cli and streams its output to the Hub."""

    def __init__(self, workspace: Path, hub: Hub, cli: str = "arduino-cli") -> None:
        self.workspace = workspace
        self.hub = hub
        self.cli = find_arduino_cli(cli) or cli
        self.lock = asyncio.Lock()  # one compile/upload at a time

    def available(self) -> bool:
        return Path(self.cli).is_file() or shutil.which(self.cli) is not None

    def sketch_path(self, sketch: str) -> Path:
        """Resolve a sketch folder (or .ino file) inside the workspace."""
        p = (self.workspace / sketch).resolve()
        if p.is_file():
            p = p.parent
        root = self.workspace.resolve()
        if p != root and root not in p.parents:
            raise ValueError("Sketch must be inside the workspace")
        if not p.is_dir():
            raise ValueError(f"Sketch folder not found: {sketch}")
        if not (p / f"{p.name}.ino").exists():
            raise ValueError(
                f"{sketch}: the folder must contain {p.name}.ino "
                "(Arduino needs the .ino file to match its folder name)"
            )
        return p

    async def _json(self, *args: str) -> Any:
        proc = await asyncio.create_subprocess_exec(
            self.cli, *args, "--format", "json",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        out, err = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(err.decode(errors="replace").strip() or "arduino-cli failed")
        return json.loads(out or b"{}")

    async def list_boards(self) -> list[dict[str, Any]]:
        """Connected boards/ports: [{port, protocol, label, name, fqbn}]."""
        data = await self._json("board", "list")
        ports = data.get("detected_ports", data) if isinstance(data, dict) else data
        result = []
        for entry in ports or []:
            port = entry.get("port", {})
            boards = entry.get("matching_boards") or [{}]
            for b in boards:
                result.append({
                    "port": port.get("address", ""),
                    "protocol": port.get("protocol", ""),
                    "label": port.get("label", ""),
                    "name": b.get("name", ""),
                    "fqbn": b.get("fqbn", ""),
                })
        return result

    async def list_installed_boards(self) -> list[dict[str, str]]:
        """Every board from installed cores: [{name, fqbn}]."""
        data = await self._json("board", "listall")
        return [{"name": b.get("name", ""), "fqbn": b.get("fqbn", "")}
                for b in data.get("boards", [])]

    async def run(self, args: list[str], title: str) -> tuple[int, str]:
        """Run arduino-cli, streaming each output line to the browser.

        Returns (exit code, full output) so Claude also gets the log.
        """
        await self.hub.send({"type": "build_start", "title": title,
                             "command": " ".join([self.cli, *args])})
        lines: list[str] = []
        proc = await asyncio.create_subprocess_exec(
            self.cli, *args,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            cwd=str(self.workspace),
        )
        assert proc.stdout is not None
        async for raw in proc.stdout:
            line = raw.decode(errors="replace").rstrip("\n")
            lines.append(line)
            await self.hub.send({"type": "build_line", "line": line})
        code = await proc.wait()
        await self.hub.send({"type": "build_end", "title": title, "ok": code == 0})
        return code, "\n".join(lines)

    async def compile(self, sketch: str, fqbn: str) -> tuple[int, str]:
        path = self.sketch_path(sketch)
        async with self.lock:
            return await self.run(["compile", "--fqbn", fqbn, str(path)],
                                  f"Compile {path.name} for {fqbn}")

    async def upload(self, sketch: str, fqbn: str, port: str,
                     serial_monitor: "SerialMonitor") -> tuple[int, str]:
        path = self.sketch_path(sketch)
        async with self.lock:
            # The port can't be used for uploading while the monitor has it open
            reopen = serial_monitor.is_open_on(port)
            baud = serial_monitor.baud
            if reopen:
                await serial_monitor.close()
            code, out = await self.run(
                ["compile", "--upload", "--fqbn", fqbn, "--port", port, str(path)],
                f"Upload {path.name} to {port}",
            )
            if reopen:
                await asyncio.sleep(1.5)  # board resets after upload
                try:
                    await serial_monitor.open(port, baud)
                except Exception as exc:  # noqa: BLE001
                    await self.hub.send({"type": "serial_status", "open": False,
                                         "error": str(exc)})
            return code, out


class SerialMonitor:
    """One serial port at a time; lines go to the browser and a short buffer
    that Claude can read with the serial_read tool."""

    def __init__(self, hub: Hub) -> None:
        self.hub = hub
        self.port: str | None = None
        self.baud = 9600
        self._serial: Any = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._buffer: list[tuple[float, str]] = []  # (time, line), last ~2000

    def is_open_on(self, port: str) -> bool:
        return self._serial is not None and self.port == port

    async def open(self, port: str, baud: int) -> None:
        if serial is None:
            raise RuntimeError("pyserial is not installed (pip install pyserial)")
        await self.close()
        self._loop = asyncio.get_running_loop()
        self._serial = serial.Serial(port, baud, timeout=0.2)
        self.port, self.baud = port, baud
        self._stop.clear()
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()
        await self.hub.send({"type": "serial_status", "open": True,
                             "port": port, "baud": baud})

    async def close(self) -> None:
        if self._serial is None:
            return
        self._stop.set()
        if self._thread:
            await asyncio.to_thread(self._thread.join, 2)
        try:
            self._serial.close()
        except Exception:
            pass
        self._serial = None
        await self.hub.send({"type": "serial_status", "open": False, "port": self.port})

    async def write(self, text: str) -> None:
        if self._serial is None:
            raise RuntimeError("Serial monitor is not open")
        await asyncio.to_thread(self._serial.write, text.encode())

    def _reader(self) -> None:
        pending = b""
        while not self._stop.is_set():
            try:
                chunk = self._serial.read(256)
            except Exception as exc:  # unplugged, etc.
                self._emit({"type": "serial_status", "open": False, "error": str(exc)})
                self._serial = None
                return
            if not chunk:
                continue
            pending += chunk
            while b"\n" in pending:
                line, pending = pending.split(b"\n", 1)
                text = line.decode(errors="replace").rstrip("\r")
                self._buffer.append((time.time(), text))
                del self._buffer[:-2000]
                self._emit({"type": "serial_line", "line": text})

    def _emit(self, event: dict[str, Any]) -> None:
        if self._loop:
            asyncio.run_coroutine_threadsafe(self.hub.send(event), self._loop)

    async def read_for(self, seconds: float) -> list[str]:
        """Collect the lines that arrive during the next `seconds`."""
        if self._serial is None:
            raise RuntimeError("Serial monitor is not open")
        start = time.time()
        await asyncio.sleep(seconds)
        return [line for t, line in self._buffer if t >= start]
