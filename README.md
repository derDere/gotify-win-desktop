# gotify-win-desktop

A simple Windows tray client for [Gotify](https://gotify.net) that listens to one or more Gotify WebSocket streams and shows native Windows notifications. It includes a tray menu, a configuration window, silent mode, and quick links to your Gotify servers.

## Features
- **Tray app:** Runs in the Windows system tray via `pystray`.
- **Multiple servers:** Connect to multiple Gotify streams in parallel.
- **Notifications:** Uses Windows notifications; `title` and `message` come from the Gotify payload.
- **Silent mode:** Temporarily suppress notifications for a chosen duration.
- **Config window:** Edit URLs and timeouts; see connection status (green/yellow/red).
- **Servers menu:** Quick open to your Gotify web UI.

## Requirements
- **Windows**
- **Python 3.11+** (3.11 or newer)

## Quick Start (venv)
Use a virtual environment to run the app without affecting your system Python.

```powershell
# From the repo root
python -m venv .venv

# Activate the venv (PowerShell)
. .\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run the app
python .\main.py
```

After launch, the app places an icon in the system tray and starts listening to the configured Gotify servers.

## Configuration
The app reads and writes its settings in `~/gotify-win-client-config.yaml` in your user profile.

Keys:
- `urls`: List of Gotify WebSocket stream URLs. Each line can optionally start with a name in square brackets.
	- Format examples:
		- `wss://your.gotify.server/stream?token=YOUR_CLIENT_TOKEN`
		- `[Work]wss://gotify.example.com/stream?token=ABC123`
- `notify_timeout`: Notification display duration in seconds.
- `silent_time`: Silent-mode duration in minutes.
- `ignore_ssl_errors` (optional): If set to `true`, SSL certificate verification is disabled for WebSocket connections.

You can edit `~/gotify-win-client-config.yaml` manually or use the tray’s **Show Window** to open the configuration UI:
- Edit URLs (one per line; optional `[Name]` prefix).
- Pick notification timeout and silent duration from presets.
- Status dot shows aggregate connection health:
	- Green: all connections online
	- Yellow: some online
	- Red: none online

## Tray Menu
- **Show Window:** Open the configuration window.
- **Silent / Silent Off:** Toggle silent mode. When silent is active, notifications are suppressed until the shown time; connections stay active.
- **Servers:** Lists detected server hosts from your URLs; opens `https://{host}` in your default browser.
- **Exit:** Stop the app and remove the tray icon.

## Tokens
Use a **Gotify client token** for each server stream (`/stream?token=...`). Users familiar with Gotify will know how to create and manage tokens.

## Tips
- Multiple servers are supported; add as many `urls` as you need.
- If your server uses a self-signed certificate and you trust it, set `ignore_ssl_errors: true` (not recommended for production).

## Build
Use the provided PowerShell script to build a single-file Windows EXE with PyInstaller.

```powershell
# From repo root
./build.ps1
```

The output appears under `dist/`. The EXE uses the tray icon from `notify_client.ico`.

## Install (no admin)
After building, the output is `GotifyClient.exe` in `dist/`.
Run it with `--install` to copy it to your user programs folder and add a Startup shortcut.

```powershell
# From dist
./GotifyClient.exe --install
```

This places `GotifyClient.exe` in `%LOCALAPPDATA%\Programs\GotifyWinClient` and creates `GotifyClient.lnk` in your Startup folder (`shell:startup`).

The installer also places `notify_client.ico` next to the EXE so the shortcut shows the right icon.

## Uninstall
Remove from Programs and Startup:

```powershell
./GotifyClient.exe --uninstall
```

## Setup Helper Script
The build process copies `setup.ps1` into `dist/` next to `GotifyClient.exe`.

Run it for a guided install/uninstall:

```powershell
./setup.ps1
```

Behavior:
- If already installed, prompts to uninstall.
- If not installed, performs install (`--install`).

Note: This app now uses `winotify` for native Windows toasts. `build.ps1` installs dependencies from `requirements.txt` which includes `winotify`. If `pip install -r requirements.txt` fails to find `winotify`, ensure your Python/pip are up-to-date and you are on a supported Windows environment (Windows 10/11). If you still see issues, run the setup and build on a clean Python 3.11 virtual environment.

## Troubleshooting
- If you see `401 Unauthorized`, the app backs off reconnect attempts automatically.
- Notifications rely on Windows; ensure Focus Assist / Do Not Disturb is off if you don’t see toasts.

## License
GNU General Public License v3.0 (GPL-3.0). See [LICENSE](LICENSE). Project name: gotify-win-desktop.

