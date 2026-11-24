"""Modulino Arcade - Python side of the App Lab app.

The sketch runs the games (buttons, buzzer, LED matrix) and reports through
the Bridge. This script keeps the high scores (saved in the app folder) and
serves the browser page with the Web UI brick (port 7000):
- shows what's happening, each round and the final score,
- shows the high scores,
- has buttons that start a game on the board.
"""

import json
import time
from pathlib import Path

from arduino.app_bricks.web_ui import WebUI
from arduino.app_utils import App, Bridge

GAMES = {1: "Reaction", 2: "Simon"}
# Reaction: lower average ms is better. Simon: longer sequence is better.
LOWER_IS_BETTER = {1: True, 2: False}
MAX_SCORES = 10

SCORES_FILE = Path(__file__).resolve().parent.parent / "highscores.json"

ui = WebUI()
state = {"status": "Starting…", "modules": {"buttons": None, "buzzer": None}, "rounds": []}


def load_scores() -> dict:
    try:
        return json.loads(SCORES_FILE.read_text())
    except (OSError, ValueError):
        return {"1": [], "2": []}


scores = load_scores()


def save_scores() -> None:
    try:
        SCORES_FILE.write_text(json.dumps(scores, indent=2))
    except OSError as exc:
        print(f"Could not save high scores: {exc}")


def push_state() -> None:
    ui.send_message("state", {**state, "scores": scores, "games": GAMES})


# ---------------- from the sketch ----------------
def arcade_status(text: str) -> None:
    state["status"] = str(text)
    print(text)
    push_state()


def arcade_modules(buttons_found: bool, buzzer_found: bool) -> None:
    state["modules"] = {"buttons": bool(buttons_found), "buzzer": bool(buzzer_found)}
    if not buttons_found:
        state["status"] = ("Modulino Buttons NOT found: check the Qwiic cable, then unplug "
                           "the board's power and plug it back in.")
    print(f"Modulino Buttons found: {bool(buttons_found)}, Buzzer found: {bool(buzzer_found)}")
    push_state()


def arcade_round(game: int, round_no: int, value: int) -> None:
    game = int(game)
    if int(round_no) == 1:
        state["rounds"] = []
    text = (f"Round {round_no}: {value} ms" if game == 1
            else f"Repeated a sequence of {round_no}")
    state["rounds"].append(text)
    push_state()


def arcade_over(game: int, score: int) -> None:
    game, score = int(game), int(score)
    name = GAMES.get(game, f"Game {game}")
    table = scores.setdefault(str(game), [])
    table.append({"score": score, "time": time.strftime("%Y-%m-%d %H:%M")})
    table.sort(key=lambda e: e["score"], reverse=not LOWER_IS_BETTER.get(game, False))
    del table[MAX_SCORES:]
    save_scores()

    best = table[0]["score"] == score
    unit = " ms average" if game == 1 else ""
    state["status"] = f"{name} over: {score}{unit}" + ("  🏆 New high score!" if best else "")
    print(state["status"])
    push_state()


Bridge.provide("arcade_status", arcade_status)
Bridge.provide("arcade_modules", arcade_modules)
Bridge.provide("arcade_round", arcade_round)
Bridge.provide("arcade_over", arcade_over)


# ---------------- from the browser ----------------
def on_start_game(client, data) -> None:
    game = int((data or {}).get("game", 0))
    if game in GAMES:
        state["rounds"] = []
        Bridge.call("start_game", game)


def on_clear_scores(client, data) -> None:
    game = str((data or {}).get("game", ""))
    if game in scores:
        scores[game] = []
        save_scores()
        push_state()


def on_connect(connection) -> None:
    push_state()


ui.on_message("start_game", on_start_game)
ui.on_message("clear_scores", on_clear_scores)
ui.on_connect(on_connect)

print("Modulino Arcade: open http://<board-name>.local:7000 (or the board's IP address, port 7000)")
App.run()
