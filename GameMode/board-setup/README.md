# Game mode for the UNO Q / VENTUNO Q

`gamemode.sh` sets the board's Linux side up for gaming and switches a
**game mode** on and off. Run it on the board's desktop (single-board-computer
mode: monitor, keyboard and mouse connected) or over SSH.

## What it does

| Command | What happens |
|---|---|
| `./gamemode.sh setup` | Installs Feral GameMode and adds **GeForce NOW** and **Xbox Cloud Gaming** shortcuts to the app menu (installs Chromium if there's no browser). |
| `./gamemode.sh setup --minecraft` | Also installs **Prism Launcher** for Minecraft Java Edition (ARM64, via Flatpak). |
| `./gamemode.sh on` | CPU to full speed (`performance`), and stops the running App Lab app to free memory. |
| `./gamemode.sh off` | Restores the CPU setting. Start your App Lab app again from App Lab. |
| `./gamemode.sh play <command>` | Runs a game with game mode on, and turns it off afterwards. The shortcuts use this. |
| `./gamemode.sh status` | Shows what's installed and whether game mode is on. |

Add `--dry-run` to any command to see what it would do without changing
anything.

## Which games work

The board's processor is ARM64, not x86_64, so Windows/PC games don't run on
it directly.

| Game | How |
|---|---|
| Fortnite | **Cloud gaming only** (GeForce NOW or Xbox Cloud Gaming shortcut). Needs fast Wi-Fi or Ethernet and an account for the service. |
| Roblox | Cloud gaming where the service offers it; check its game list. |
| Minecraft Java | `setup --minecraft`, then Prism Launcher. Needs a Minecraft account; how well it runs depends on the board's graphics drivers. |
| Board games | The [Modulino Arcade](../ModulinoArcadeApp/) App Lab app: Reaction and Simon on the LED matrix. |

## Install

```bash
git clone https://github.com/developer1-vd/Dev1-Arduino-Projects.git
```
```bash
cd Dev1-Arduino-Projects/GameMode/board-setup
```
```bash
./gamemode.sh setup
```

## Notes
- Not tested on a real board yet; try `--dry-run` first.
- `setup` uses `sudo` (the board's password) to install packages; `on` and
  `off` use it to change the CPU setting.
- A browser that's already open may hand the shortcut to the existing window
  and return straight away, so game mode can turn off early. Use
  `./gamemode.sh on` before playing and `off` after, if that happens.
