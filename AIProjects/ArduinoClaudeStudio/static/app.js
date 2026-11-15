// Arduino Claude Studio - browser side.
"use strict";

const $ = (id) => document.getElementById(id);
const state = {
  mode: "arduino",     // "arduino" (computer + arduino-cli) or "applab" (on the board)
  file: null,          // path of the open file
  savedContent: "",
  boardsInstalled: [],
  serialOpen: false,
  busy: false,
};

// ---------------- helpers ----------------
async function api(method, url, body) {
  const res = await fetch(url, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}

function store(key, value) {
  try { localStorage.setItem("acs." + key, value); } catch (_) { /* private mode */ }
}
function recall(key) {
  try { return localStorage.getItem("acs." + key); } catch (_) { return null; }
}

function appendLine(el, text, cls) {
  const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
  const span = document.createElement("span");
  if (cls) span.className = cls;
  span.textContent = text + "\n";
  el.appendChild(span);
  while (el.childNodes.length > 5000) el.removeChild(el.firstChild);
  if (atBottom) el.scrollTop = el.scrollHeight;
}

function currentSketch() {
  // The sketch is the folder of the open file (Blink/Blink.ino -> Blink)
  if (!state.file) return null;
  const parts = state.file.split("/");
  return parts.length > 1 ? parts.slice(0, -1).join("/") : null;
}

// ---------------- editor ----------------
const editor = CodeMirror($("editor"), {
  theme: "material-darker",
  mode: "text/x-c++src",
  lineNumbers: true,
  indentUnit: 2,
  tabSize: 2,
  matchBrackets: true,
  readOnly: "nocursor",
  value: "// Open a sketch on the left, or ask Claude to write one.",
});
editor.on("change", () => { $("dirty").hidden = editor.getValue() === state.savedContent; });

function modeFor(path) {
  if (path.endsWith(".py")) return "python";
  if (/\.(ino|cpp|c|h|hpp)$/.test(path)) return "text/x-c++src";
  return "text/plain";
}

async function openFile(path, { keepCursor = false } = {}) {
  if (state.file && state.file !== path && editor.getValue() !== state.savedContent) {
    if (!confirm(`Discard unsaved changes to ${state.file}?`)) return;
  }
  const { content } = await api("GET", "/api/file?path=" + encodeURIComponent(path));
  const cursor = editor.getCursor();
  state.file = path;
  state.savedContent = content;
  editor.setOption("readOnly", false);
  editor.setOption("mode", modeFor(path));
  editor.setValue(content);
  if (keepCursor) editor.setCursor(cursor);
  editor.clearHistory();
  $("current-file").textContent = path;
  $("dirty").hidden = true;
  store("file", path);
  highlightFile();
  sendSelection();
}

async function saveFile() {
  if (!state.file) return;
  const content = editor.getValue();
  await api("PUT", "/api/file", { path: state.file, content });
  state.savedContent = content;
  $("dirty").hidden = true;
}

// ---------------- file list ----------------
async function loadFiles() {
  const files = await api("GET", "/api/files");
  const list = $("file-list");
  list.innerHTML = "";
  let folder = null;
  for (const f of files) {
    const parts = f.split("/");
    const dir = parts.length > 1 ? parts.slice(0, -1).join("/") : "";
    if (dir !== folder) {
      folder = dir;
      if (dir) {
        const li = document.createElement("li");
        li.className = "folder";
        li.textContent = dir;
        list.appendChild(li);
      }
    }
    const li = document.createElement("li");
    li.className = "file";
    li.textContent = parts[parts.length - 1];
    li.title = f;
    li.dataset.path = f;
    li.onclick = () => openFile(f).catch((e) => alert(e.message));
    list.appendChild(li);
  }
  highlightFile();
  return files;
}

function highlightFile() {
  for (const li of document.querySelectorAll("#file-list li.file")) {
    li.classList.toggle("active", li.dataset.path === state.file);
  }
}

$("new-sketch").onclick = async () => {
  const applab = state.mode === "applab";
  const name = prompt(applab ? "New App Lab app name:" : "New sketch name (letters, digits, _ or -):");
  if (!name) return;
  try {
    const { path } = applab ? await api("POST", "/api/apps/new", { name })
                            : await api("POST", "/api/sketch", { name });
    await loadFiles();
    await openFile(path);
  } catch (e) { alert(e.message); }
};

// Claude changed files: refresh the list, and the open file if it's unchanged here
async function onFilesChanged() {
  await loadFiles();
  if (!state.file) return;
  if (editor.getValue() !== state.savedContent) return; // don't clobber the user's edits
  try {
    const { content } = await api("GET", "/api/file?path=" + encodeURIComponent(state.file));
    if (content !== state.savedContent) await openFile(state.file, { keepCursor: true });
  } catch (_) { /* file was deleted */ }
}

// ---------------- boards ----------------
async function loadBoards() {
  $("build-status").textContent = "Looking for boards…";
  let data;
  try {
    data = await api("GET", "/api/boards");
  } catch (e) {
    $("build-status").textContent = e.message;
    return;
  }
  $("build-status").textContent = "";
  const boardSel = $("board"), portSel = $("port");
  const prevBoard = boardSel.value || recall("fqbn") || "";
  const prevPort = portSel.value || recall("port") || "";

  boardSel.innerHTML = '<option value="">Select a board…</option>';
  portSel.innerHTML = '<option value="">No port</option>';
  const seen = new Set();

  if (data.connected.length) {
    const group = document.createElement("optgroup");
    group.label = "Connected";
    for (const b of data.connected) {
      if (b.fqbn && !seen.has(b.fqbn)) {
        seen.add(b.fqbn);
        group.appendChild(new Option(`${b.name} (${b.port})`, b.fqbn));
      }
      if (b.port && ![...portSel.options].some((o) => o.value === b.port)) {
        portSel.appendChild(new Option(`${b.port}${b.name ? " – " + b.name : ""}`, b.port));
      }
    }
    if (group.children.length) boardSel.appendChild(group);
  }
  const all = document.createElement("optgroup");
  all.label = "All installed boards";
  for (const b of data.installed) {
    if (b.fqbn && !seen.has(b.fqbn)) { seen.add(b.fqbn); all.appendChild(new Option(b.name, b.fqbn)); }
  }
  boardSel.appendChild(all);

  if (prevBoard && [...boardSel.options].some((o) => o.value === prevBoard)) boardSel.value = prevBoard;
  else if (data.connected[0]?.fqbn) boardSel.value = data.connected[0].fqbn;
  if (prevPort && [...portSel.options].some((o) => o.value === prevPort)) portSel.value = prevPort;
  else if (data.connected[0]?.port) portSel.value = data.connected[0].port;
  sendSelection();
}

$("refresh").onclick = loadBoards;
$("board").onchange = () => { store("fqbn", $("board").value); sendSelection(); };
$("port").onchange = () => { store("port", $("port").value); sendSelection(); };
$("baud").onchange = () => { store("baud", $("baud").value); sendSelection(); };

// ---------------- compile / upload ----------------
async function build(kind) {
  const sketch = currentSketch();
  if (!sketch) return alert("Open a sketch file first (e.g. Blink/Blink.ino).");
  if (!$("board").value) return alert("Select a board first.");
  if (kind === "upload" && !$("port").value) return alert("Select a port first.");
  showTab("build");
  if (editor.getValue() !== state.savedContent) await saveFile();
  try {
    await api("POST", "/api/" + kind, { sketch, fqbn: $("board").value, port: $("port").value });
  } catch (e) {
    appendLine($("build"), e.message, "line-error");
  }
}
$("compile").onclick = () => build("compile");
$("upload").onclick = () => build("upload");
$("save").onclick = () => saveFile().catch((e) => alert(e.message));
document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "s") { e.preventDefault(); saveFile(); }
});

// ---------------- App Lab mode: run / stop apps ----------------
function currentApp() {
  return state.file ? state.file.split("/")[0] : null;
}

async function loadAppStatus() {
  try {
    const apps = await api("GET", "/api/apps");
    const running = apps.find((a) => a.status === "running" || a.status === "starting");
    $("app-status").textContent = running ? `Running: ${running.name || running.folder} (${running.status})`
                                          : "No app running";
  } catch (e) { $("app-status").textContent = e.message; }
}

$("run-app").onclick = async () => {
  const app = currentApp();
  if (!app) return alert("Open a file of the app you want to run.");
  showTab("build");
  if (editor.getValue() !== state.savedContent) await saveFile();
  $("app-status").textContent = `Starting ${app}…`;
  try { await api("POST", "/api/apps/run", { app }); }
  catch (e) { appendLine($("build"), e.message, "line-error"); }
  loadAppStatus();
};
$("stop-app").onclick = async () => {
  try { await api("POST", "/api/apps/stop", {}); }
  catch (e) { appendLine($("build"), e.message, "line-error"); }
  loadAppStatus();
};

// ---------------- bottom tabs + serial ----------------
function showTab(name) {
  for (const t of document.querySelectorAll(".tab")) t.classList.toggle("active", t.dataset.tab === name);
  $("build").hidden = name !== "build";
  $("applog").hidden = name !== "applog";
  $("serial-pane").hidden = name !== "serial";
}
for (const t of document.querySelectorAll(".tab")) t.onclick = () => showTab(t.dataset.tab);

$("serial-toggle").onclick = async () => {
  try {
    if (state.serialOpen) await api("POST", "/api/serial/close");
    else {
      if (state.mode === "arduino" && !$("port").value) return alert("Select a port first.");
      await api("POST", "/api/serial/open", { port: $("port").value || "", baud: Number($("baud").value) });
    }
  } catch (e) { appendLine($("serial"), e.message, "line-error"); }
};
$("serial-clear").onclick = () => { $("serial").innerHTML = ""; };
$("serial-input").onkeydown = async (e) => {
  if (e.key !== "Enter") return;
  try {
    await api("POST", "/api/serial/send", { text: e.target.value + "\n" });
    e.target.value = "";
  } catch (err) { appendLine($("serial"), err.message, "line-error"); }
};

// ---------------- chat ----------------
const messages = $("messages");
const toolEls = {};

function addMsg(cls, text, markdown = false) {
  const div = document.createElement("div");
  div.className = "msg " + cls;
  if (markdown) div.innerHTML = DOMPurify.sanitize(marked.parse(text));
  else div.textContent = text;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
  return div;
}

function toolLabel(name, input) {
  const short = name.replace(/^mcp__(arduino|applab)__/, "$1.");
  let detail = "";
  try {
    const obj = JSON.parse(input);
    detail = obj.file_path || obj.command || obj.sketch || obj.pattern || "";
  } catch (_) { /* not JSON */ }
  return detail ? `${short}  ${detail}` : short;
}

function addTool(ev) {
  const d = document.createElement("details");
  d.className = "tool";
  d.innerHTML = '<summary><span class="label"></span><span class="status">…</span></summary><pre></pre>';
  d.querySelector(".label").textContent = toolLabel(ev.name, ev.input);
  d.querySelector("pre").textContent = ev.input;
  messages.appendChild(d);
  toolEls[ev.id] = d;
  messages.scrollTop = messages.scrollHeight;
}

function finishTool(ev) {
  const d = toolEls[ev.id];
  if (!d) return;
  const status = d.querySelector(".status");
  status.textContent = ev.is_error ? "✗" : "✓";
  status.className = "status " + (ev.is_error ? "line-error" : "line-ok");
  d.querySelector("pre").textContent += "\n\n── result ──\n" + ev.content;
}

function addPermission(ev) {
  const div = document.createElement("div");
  div.className = "permission";
  div.innerHTML = '<div><strong>Claude wants to use <code class="t"></code></strong></div>' +
    '<pre></pre><div class="buttons"><button class="deny">Deny</button>' +
    '<button class="allow primary">Allow</button></div>';
  div.querySelector(".t").textContent = ev.tool;
  div.querySelector("pre").textContent = ev.input;
  const answer = (allow) => {
    send({ type: "permission", id: ev.id, allow });
    div.querySelector(".buttons").textContent = allow ? "Allowed" : "Denied";
  };
  div.querySelector(".allow").onclick = () => answer(true);
  div.querySelector(".deny").onclick = () => answer(false);
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

function setBusy(busy) {
  state.busy = busy;
  $("send").disabled = busy;
  $("stop").hidden = !busy;
  $("chat-status").textContent = busy ? "Claude is working…" : "";
}

$("chat-form").onsubmit = (e) => {
  e.preventDefault();
  const text = $("prompt").value.trim();
  if (!text || state.busy) return;
  if (state.file && editor.getValue() !== state.savedContent) saveFile();
  addMsg("user", text);
  send({ type: "prompt", text });
  $("prompt").value = "";
};
$("prompt").onkeydown = (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("chat-form").requestSubmit(); }
};
$("stop").onclick = () => send({ type: "interrupt" });
$("new-chat").onclick = () => send({ type: "reset" });

// ---------------- websocket ----------------
let ws;
function send(obj) { if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj)); }

function sendSelection() {
  send({ type: "selection", fqbn: $("board").value, port: $("port").value,
         baud: Number($("baud").value), file: state.file });
}

function connect() {
  ws = new WebSocket((location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws");
  ws.onopen = () => { sendSelection(); };
  ws.onclose = () => {
    setBusy(false);
    $("chat-status").textContent = "Disconnected – reconnecting…";
    setTimeout(connect, 2000);
  };
  ws.onmessage = (e) => {
    const ev = JSON.parse(e.data);
    switch (ev.type) {
      case "assistant_text": addMsg("assistant", ev.text, true); break;
      case "tool_use": addTool(ev); break;
      case "tool_result": finishTool(ev); break;
      case "permission_request": addPermission(ev); break;
      case "chat_busy": setBusy(ev.busy); break;
      case "chat_error": addMsg("error", ev.error); break;
      case "chat_reset": messages.innerHTML = ""; addMsg("info", "New conversation"); break;
      case "result": {
        const cost = ev.cost_usd != null ? ` · $${ev.cost_usd.toFixed(4)}` : "";
        addMsg("info", `Done in ${(ev.duration_ms / 1000).toFixed(1)} s${cost}`);
        break;
      }
      case "files_changed": onFilesChanged(); break;
      case "build_start":
        showTab("build");
        $("build").innerHTML = "";
        appendLine($("build"), `▶ ${ev.title}\n$ ${ev.command}`, "line-head");
        $("build-status").textContent = ev.title + "…";
        break;
      case "build_line":
        appendLine($("build"), ev.line, /error|fatal/i.test(ev.line) ? "line-error" : "");
        break;
      case "build_end":
        appendLine($("build"), ev.ok ? "✓ Done" : "✗ Failed", ev.ok ? "line-ok" : "line-error");
        $("build-status").textContent = `${ev.title}: ${ev.ok ? "done" : "failed"}`;
        break;
      case "serial_line": appendLine($("serial"), ev.line); break;
      case "log_line": appendLine($("applog"), ev.line); break;
      case "log_status":
        if (ev.open) { $("applog").innerHTML = ""; showTab("applog"); }
        appendLine($("applog"), ev.open ? `── ${ev.app} Python log ──` : "── log ended ──", "line-head");
        break;
      case "apps_changed": loadAppStatus(); break;
      case "serial_status":
        state.serialOpen = ev.open;
        $("serial-toggle").textContent = ev.open ? "Close" : "Open";
        appendLine($("serial"), ev.open ? `── connected to ${ev.port}${ev.baud ? ` at ${ev.baud} baud` : ""} ──`
          : `── disconnected${ev.error ? ": " + ev.error : ""} ──`, ev.error ? "line-error" : "line-head");
        break;
    }
  };
}

// ---------------- start ----------------
(async function init() {
  const savedBaud = recall("baud");
  if (savedBaud) $("baud").value = savedBaud;
  const info = await api("GET", "/api/info");
  state.mode = info.mode;
  document.body.classList.add("mode-" + info.mode);
  $("workspace-path").textContent = info.workspace;
  if (info.mode === "applab") {
    $("files-title").textContent = "Apps";
    $("new-sketch").title = "New App Lab app";
    $("build-tab").textContent = "Run log";
    loadAppStatus();
  }
  if (!info.arduino_cli) {
    const tool = info.mode === "applab" ? "arduino-app-cli" : "arduino-cli";
    appendLine($("build"), `${tool} was not found. Install it and restart (see README).`, "line-error");
  }
  connect();
  const files = await loadFiles();
  const last = recall("file");
  const first = files.includes(last) ? last : files.find((f) => f.endsWith(".ino"));
  if (first) await openFile(first);
  addMsg("info", "Ask Claude to write a sketch, fix a compile error, or upload and check the serial output.");
  if (info.arduino_cli && info.mode === "arduino") loadBoards();
})();
