#!/usr/bin/env bash
# Game mode for the Arduino UNO Q and VENTUNO Q (Linux side, ARM64).
#
#   ./gamemode.sh setup              install Feral GameMode and add cloud-gaming
#                                    shortcuts (GeForce NOW, Xbox Cloud Gaming)
#   ./gamemode.sh setup --minecraft  also install Prism Launcher (Minecraft Java)
#   ./gamemode.sh on                 game mode on: CPU at full speed, running
#                                    App Lab app stopped
#   ./gamemode.sh off                back to normal (restores the CPU setting)
#   ./gamemode.sh status             show what's on
#   ./gamemode.sh play <command>     run a game with game mode for its duration
#
# Add --dry-run to any command to print what it would do without changing
# anything. Run it as the normal "arduino" user; it asks for sudo when needed.
#
# What it can't do: the board's processor is ARM64, so Windows/x86_64 games
# (Fortnite, Roblox, ...) don't run on it directly. Cloud gaming streams them
# instead, which is why setup adds those shortcuts.

set -euo pipefail

STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/board-gamemode"
APPS_DIR="$HOME/.local/share/applications"
DRY_RUN=0

say()  { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; exit 1; }

# run a command, or just print it with --dry-run
run() {
  if [ "$DRY_RUN" = 1 ]; then
    printf '   [dry-run] %s\n' "$*"
  else
    "$@"
  fi
}

sudo_run() {
  if [ "$(id -u)" = 0 ]; then run "$@"; else run sudo "$@"; fi
}

cpu_governor_files() {
  ls /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor 2>/dev/null || true
}

check_board() {
  local arch
  arch="$(uname -m)"
  if [ "$arch" != "aarch64" ]; then
    warn "This is meant for the UNO Q / VENTUNO Q (aarch64); this machine is $arch."
  fi
  if ! command -v apt-get >/dev/null 2>&1; then
    die "apt-get not found: this script expects the board's Debian-based Linux."
  fi
}

find_browser() {
  local b
  for b in chromium chromium-browser google-chrome firefox firefox-esr x-www-browser; do
    if command -v "$b" >/dev/null 2>&1; then echo "$b"; return; fi
  done
}

write_shortcut() {  # name, url, icon-name
  local name="$1" url="$2" icon="$3" browser file
  browser="$(find_browser)"
  file="$APPS_DIR/$(echo "$name" | tr ' ' '-' | tr 'A-Z' 'a-z').desktop"
  local exec_line
  case "$browser" in
    chromium|chromium-browser|google-chrome) exec_line="$browser --app=$url --start-fullscreen" ;;
    firefox|firefox-esr) exec_line="$browser --kiosk $url" ;;
    *) exec_line="xdg-open $url" ;;
  esac
  say "Shortcut: $name -> $url"
  if [ "$DRY_RUN" = 1 ]; then
    printf '   [dry-run] write %s (Exec=%s)\n' "$file" "$exec_line"
    return
  fi
  mkdir -p "$APPS_DIR"
  cat > "$file" <<EOF
[Desktop Entry]
Type=Application
Name=$name
Comment=Cloud gaming in the browser (game mode on while it runs)
Exec=$(readlink -f "$0") play $exec_line
Icon=$icon
Categories=Game;
Terminal=false
EOF
  chmod +x "$file"
}

cmd_setup() {
  local minecraft=0
  for arg in "$@"; do
    case "$arg" in
      --minecraft) minecraft=1 ;;
      *) die "Unknown option for setup: $arg" ;;
    esac
  done
  check_board

  say "Installing Feral GameMode (gamemoded, gamemoderun)"
  sudo_run apt-get update
  sudo_run apt-get install -y gamemode

  local browser
  browser="$(find_browser || true)"
  if [ -z "$browser" ]; then
    say "No web browser found: installing Chromium for cloud gaming"
    sudo_run apt-get install -y chromium || sudo_run apt-get install -y chromium-browser \
      || warn "Couldn't install Chromium; install a browser yourself."
  fi

  write_shortcut "GeForce NOW" "https://play.geforcenow.com" "applications-games"
  write_shortcut "Xbox Cloud Gaming" "https://www.xbox.com/play" "applications-games"

  if [ "$minecraft" = 1 ]; then
    say "Installing Prism Launcher (Minecraft Java Edition, ARM64) with Flatpak"
    sudo_run apt-get install -y flatpak
    run flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
    run flatpak install --user -y flathub org.prismlauncher.PrismLauncher
    say "Start it from the menu (Prism Launcher) or: ./gamemode.sh play flatpak run org.prismlauncher.PrismLauncher"
    say "You need a Minecraft Java account; performance depends on the board's graphics drivers."
  fi

  say "Done. Turn game mode on with: ./gamemode.sh on"
}

stop_running_app() {
  if ! command -v arduino-app-cli >/dev/null 2>&1; then return; fi
  local running
  running="$(arduino-app-cli app ps --format json 2>/dev/null \
    | python3 -c 'import sys,json,base64
for a in json.load(sys.stdin).get("apps") or []:
    if a.get("status") in ("running","starting"):
        s=str(a.get("id","")); s=s if ":" in s else base64.urlsafe_b64decode(s+"="*(-len(s)%4)).decode()
        print(s); break' 2>/dev/null || true)"
  if [ -n "$running" ]; then
    say "Stopping App Lab app $running to free memory and CPU"
    run arduino-app-cli app stop "$running" || warn "Couldn't stop $running"
    [ "$DRY_RUN" = 1 ] || echo "$running" > "$STATE_DIR/stopped_app"
  fi
}

cmd_on() {
  [ "$DRY_RUN" = 1 ] || mkdir -p "$STATE_DIR"
  if [ -f "$STATE_DIR/on" ]; then
    say "Game mode is already on."
    return
  fi

  local files first
  files="$(cpu_governor_files)"
  if [ -n "$files" ]; then
    first="$(echo "$files" | head -1)"
    [ "$DRY_RUN" = 1 ] || cat "$first" > "$STATE_DIR/governor"
    say "CPU: $(cat "$first") -> performance"
    for f in $files; do
      echo performance | sudo_run tee "$f" >/dev/null || warn "Couldn't set $f"
    done
  else
    warn "No CPU frequency control found; skipping the CPU setting."
  fi

  stop_running_app

  if command -v gamemoded >/dev/null 2>&1; then
    say "Feral GameMode is installed: games started with './gamemode.sh play ...' get it too."
  fi
  [ "$DRY_RUN" = 1 ] || date > "$STATE_DIR/on"
  say "Game mode ON."
}

cmd_off() {
  local files governor=""
  [ -f "$STATE_DIR/governor" ] && governor="$(cat "$STATE_DIR/governor")"
  files="$(cpu_governor_files)"
  if [ -n "$files" ] && [ -n "$governor" ]; then
    say "CPU: back to $governor"
    for f in $files; do
      echo "$governor" | sudo_run tee "$f" >/dev/null || warn "Couldn't set $f"
    done
  fi
  if [ -f "$STATE_DIR/stopped_app" ]; then
    say "The App Lab app $(cat "$STATE_DIR/stopped_app") was stopped for game mode;"
    say "start it again from App Lab (or: arduino-app-cli app start $(cat "$STATE_DIR/stopped_app"))."
  fi
  [ "$DRY_RUN" = 1 ] || rm -f "$STATE_DIR/on" "$STATE_DIR/governor" "$STATE_DIR/stopped_app"
  say "Game mode OFF."
}

cmd_status() {
  local files
  if [ -f "$STATE_DIR/on" ]; then echo "Game mode: ON since $(cat "$STATE_DIR/on")"; else echo "Game mode: off"; fi
  files="$(cpu_governor_files)"
  [ -n "$files" ] && echo "CPU governor: $(cat "$(echo "$files" | head -1)")"
  if command -v gamemoded >/dev/null 2>&1; then echo "Feral GameMode: installed"; else echo "Feral GameMode: not installed (run setup)"; fi
  if [ -f "$APPS_DIR/geforce-now.desktop" ]; then echo "Cloud-gaming shortcuts: installed"; else echo "Cloud-gaming shortcuts: not installed (run setup)"; fi
  if command -v flatpak >/dev/null 2>&1 && flatpak info --user org.prismlauncher.PrismLauncher >/dev/null 2>&1; then
    echo "Prism Launcher (Minecraft): installed"
  fi
}

cmd_play() {
  [ "$#" -gt 0 ] || die "Usage: ./gamemode.sh play <command> [args...]"
  local was_on=0
  [ -f "$STATE_DIR/on" ] && was_on=1
  [ "$was_on" = 1 ] || cmd_on
  local status=0
  if command -v gamemoderun >/dev/null 2>&1; then
    run gamemoderun "$@" || status=$?
  else
    run "$@" || status=$?
  fi
  [ "$was_on" = 1 ] || cmd_off
  return "$status"
}

main() {
  local args=()
  for a in "$@"; do
    if [ "$a" = "--dry-run" ]; then DRY_RUN=1; else args+=("$a"); fi
  done
  set -- "${args[@]+"${args[@]}"}"
  local cmd="${1:-help}"
  shift || true
  case "$cmd" in
    setup)  cmd_setup "$@" ;;
    on)     cmd_on ;;
    off)    cmd_off ;;
    status) cmd_status ;;
    play)   cmd_play "$@" ;;
    *)      sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//' ;;
  esac
}

main "$@"
