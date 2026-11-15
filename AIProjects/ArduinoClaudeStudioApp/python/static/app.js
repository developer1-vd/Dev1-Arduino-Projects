// Claude Studio (App Lab app) - browser side.
"use strict";

const $ = (id) => document.getElementById(id);
const state = { file: null, savedContent: "", busy: false };

// ---------------- access code ----------------
function getCode() {
  const fromUrl = new URLSearchParams(location.search).get("code");
  if (fromUrl) {
    setCode(fromUrl);
    history.replaceState(null, "", location.pathname); // don't leave it in the address bar
    return fromUrl;
  }
  try { return localStorage.getItem("studio.code"); } catch (_) { return null; }
}
function setCode(code) {
  try { localStorage.setItem("studio.code", code); } catch (_) { /* private mode */ }
  document.cookie = `studio_code=${encodeURIComponent(code)}; path=/; SameSite=Strict`;
}
function askCode() {
  return new Promise((resolve) => {
    const d = $("code-dialog");
    d.onclose = () => { const c = $("code-input").value.trim(); setCode(c); resolve(c); };
    d.showModal();
  });
}
let code = getCode();

async function api(method, url, body) {
  const res = await fetch(url, {
    method,
    headers: { "x-access-code": code || "", ...(body ? { "Content-Type": "application/json" } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401) {
    code = await askCode();
    return api(method, url, body);
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}

// ---------------- editor + files ----------------
const editor = CodeMirror($("editor"), {
  theme: "material-darker", mode: "text/x-c++src", lineNumbers: true,
  indentUnit: 2, tabSize: 2, readOnly: "nocursor", value: "",
});
editor.on("change", () => { $("dirty").hidden = editor.getValue() === state.savedContent; });

async function openFile(path, keepCursor = false) {
  if (state.file && state.file !== path && editor.getValue() !== state.savedContent &&
      !confirm(`Discard unsaved changes to ${state.file}?`)) return;
  const { content } = await api("GET", "/api/file?path=" + encodeURIComponent(path));
  const cursor = editor.getCursor();
  state.file = path;
  state.savedContent = content;
  editor.setOption("readOnly", false);
  editor.setOption("mode", path.endsWith(".yaml") ? "yaml" : "text/x-c++src");
  editor.setValue(content);
  if (keepCursor) editor.setCursor(cursor);
  editor.clearHistory();
  $("current-file").textContent = "sketch/" + path;
  $("dirty").hidden = true;
  for (const li of document.querySelectorAll("#file-list li")) li.classList.toggle("active", li.dataset.path === path);
  send({ type: "selection", file: "sketch/" + path });
}

async function saveFile() {
  if (!state.file) return;
  const content = editor.getValue();
  await api("PUT", "/api/file", { path: state.file, content });
  state.savedContent = content;
  $("dirty").hidden = true;
}
$("save").onclick = () => saveFile().catch((e) => alert(e.message));
document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "s") { e.preventDefault(); saveFile(); }
});

async function loadFiles() {
  const files = await api("GET", "/api/files");
  const list = $("file-list");
  list.innerHTML = "";
  for (const f of files) {
    const li = document.createElement("li");
    li.className = "file";
    li.textContent = f;
    li.dataset.path = f;
    li.classList.toggle("active", f === state.file);
    li.onclick = () => openFile(f).catch((e) => alert(e.message));
    list.appendChild(li);
  }
  return files;
}

async function onFilesChanged() {
  await loadFiles();
  if (!state.file || editor.getValue() !== state.savedContent) return;
  const { content } = await api("GET", "/api/file?path=" + encodeURIComponent(state.file));
  if (content !== state.savedContent) await openFile(state.file, true);
}

// ---------------- sketch output ----------------
function appendLine(el, text, cls) {
  const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
  const span = document.createElement("span");
  if (cls) span.className = cls;
  span.textContent = text + "\n";
  el.appendChild(span);
  while (el.childNodes.length > 5000) el.removeChild(el.firstChild);
  if (atBottom) el.scrollTop = el.scrollHeight;
}
$("clear-output").onclick = () => { $("output").innerHTML = ""; };

// ---------------- Claude key ----------------
function askKey() {
  const d = $("key-dialog");
  $("key-input").value = "";
  d.onclose = async () => {
    if (d.returnValue !== "ok" || !$("key-input").value.trim()) return;
    try {
      await api("PUT", "/api/credential", { value: $("key-input").value.trim() });
      addMsg("info", "Claude key saved.");
    } catch (e) { alert(e.message); }
  };
  d.showModal();
}
$("settings").onclick = askKey;

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
}

function addTool(ev) {
  const d = document.createElement("details");
  d.className = "tool";
  d.innerHTML = '<summary><span class="label"></span><span class="status">…</span></summary><pre></pre>';
  let detail = "";
  try { const o = JSON.parse(ev.input); detail = o.file_path || o.command || o.pattern || ""; } catch (_) {}
  const name = ev.name.replace(/^mcp__studio__/, "studio.");
  d.querySelector(".label").textContent = detail ? `${name}  ${detail.replace(/^.*\/sketch\//, "sketch/")}` : name;
  d.querySelector("pre").textContent = ev.input;
  messages.appendChild(d);
  toolEls[ev.id] = d;
  messages.scrollTop = messages.scrollHeight;
}

function finishTool(ev) {
  const d = toolEls[ev.id];
  if (!d) return;
  const s = d.querySelector(".status");
  s.textContent = ev.is_error ? "✗" : "✓";
  s.className = "status " + (ev.is_error ? "line-error" : "line-ok");
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

$("chat-form").onsubmit = async (e) => {
  e.preventDefault();
  const text = $("prompt").value.trim();
  if (!text || state.busy) return;
  if (!info.has_credential) {
    const before = (await api("GET", "/api/info")).has_credential;
    if (!before) { askKey(); return; }
    info.has_credential = true;
  }
  if (state.file && editor.getValue() !== state.savedContent) await saveFile();
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
let info = {};
function send(obj) { if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj)); }

function connect() {
  const proto = location.protocol === "https:" ? "wss://" : "ws://";
  ws = new WebSocket(`${proto}${location.host}/ws?code=${encodeURIComponent(code || "")}`);
  ws.onopen = () => {
    $("chat-status").textContent = "";
    if (state.file) send({ type: "selection", file: "sketch/" + state.file });
  };
  ws.onclose = () => {
    setBusy(false);
    $("chat-status").textContent = "Disconnected – reconnecting… (normal while the app restarts)";
    setTimeout(connect, 3000);
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
      case "sketch_line": appendLine($("output"), ev.line); break;
    }
  };
}

// ---------------- start ----------------
(async function init() {
  if (!code) code = await askCode();
  info = await api("GET", "/api/info");
  connect();
  for (const line of await api("GET", "/api/sketch-output")) appendLine($("output"), line);
  const files = await loadFiles();
  if (files.includes("sketch.ino")) await openFile("sketch.ino");
  addMsg("info", "Ask Claude to write or change the sketch. Then Save, and Stop + Run the app in App Lab to flash it.");
  if (!info.has_credential) askKey();
})();
