// Modulino Arcade page. Talks to the Python side through the Web UI brick
// (Socket.IO): receives "state", sends "start_game" and "clear_scores".
"use strict";

const socket = io(`http://${window.location.host}`);
const $ = (id) => document.getElementById(id);

socket.on("connect", () => { $("conn").textContent = "connected"; $("conn").classList.add("on"); });
socket.on("disconnect", () => { $("conn").textContent = "disconnected"; $("conn").classList.remove("on"); });

socket.on("state", (s) => {
  $("status").textContent = s.status;
  const m = s.modules || {};
  $("modules").textContent = m.buttons === null || m.buttons === undefined ? "" :
    `Modulino Buttons: ${m.buttons ? "found" : "NOT found"} · Buzzer: ${m.buzzer ? "found" : "not found (silent)"}`;

  const rounds = $("rounds");
  rounds.innerHTML = "";
  for (const r of s.rounds || []) {
    const li = document.createElement("li");
    li.textContent = r;
    rounds.appendChild(li);
  }

  for (const game of ["1", "2"]) {
    const list = $("scores-" + game);
    list.innerHTML = "";
    const entries = (s.scores || {})[game] || [];
    if (!entries.length) {
      const li = document.createElement("li");
      li.className = "muted";
      li.textContent = "No scores yet";
      list.appendChild(li);
    }
    for (const e of entries) {
      const li = document.createElement("li");
      li.textContent = game === "1" ? `${e.score} ms` : `${e.score}`;
      const when = document.createElement("span");
      when.className = "when";
      when.textContent = e.time;
      li.appendChild(when);
      list.appendChild(li);
    }
  }
});

for (const b of document.querySelectorAll("[data-game]")) {
  b.onclick = () => socket.emit("start_game", { game: Number(b.dataset.game) });
}
for (const b of document.querySelectorAll("[data-clear]")) {
  b.onclick = () => {
    if (confirm("Clear these high scores?")) socket.emit("clear_scores", { game: b.dataset.clear });
  };
}
