# Gotify Windows Desktop Client

A lightweight Windows tray client for Gotify that listens to one or more Gotify WebSocket streams and shows native Windows notifications.

This repository contains a small Python app that is typically packaged into a single EXE using PyInstaller (see `build.ps1`). It targets Windows 10/11 and uses the Windows native toast API for notifications.

**Note:** This README has been updated to match the current `main.py` implementation (config names, CLI flags, TTS behavior, and install/uninstall flow).

**Release:** [GotifyClient Windows](https://github.com/derDere/gotify-win-desktop/releases)

**Highlights**
- Tray app using `pystray` with a configuration window (Tkinter).
- Connects to multiple Gotify WebSocket streams concurrently.
- Native Windows toast notifications via `winotify`.
- Optional sound behavior: system sound (default), play a custom MP3, or use OpenAI TTS to read notifications aloud.
- Silent mode to temporarily suppress toasts while keeping connections active.
- Simple installer (`--install`) and uninstaller (`--uninstall`) to place the EXE under `%LOCALAPPDATA%\\Programs\\GotifyWinClient` and add/remove a Startup shortcut.

Supported Python packages are listed in `requirements.txt` (pystray, websocket-client, plyer, pillow, pyyaml, winotify, pygame, openai, numpy).

Requirements

- **Windows 10 or 11**
- **Python 3.11+** (development/install requires a compatible Python version)

Quick Start (development)

- Create and activate a virtual environment (PowerShell):

```powershell
python -m venv .venv
. .\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
python .\\main.py
```

When run, the app places an icon in the system tray and opens a configuration window from the tray menu.

Configuration

- The app stores user configuration in `~/gotify-win-client-config.yaml` (user home directory). If this file is missing, the app will copy the repository `config.yaml` (if present) to that location.

- Config keys used by the app (defaults shown in `main.py`):
	- `urls` (list): WebSocket stream URLs. Each entry may optionally include a display name prefix in square brackets: `[Work]wss://gotify.example/stream?token=...`
	- `notify_timeout` (int): Notification display timeout in seconds (default: 30).
	- `silent_time` (int): Silent mode duration in minutes when enabling from the tray (default: 10).
	- `ignore_ssl_errors` (bool): If true, SSL certificate verification is disabled for WebSocket connections.
	- `sound` (string): One of `windows` (default), `sound_file`, or `tts`.
	- `voice` (string): Voice name used by TTS (when `sound` is `tts`).
	- `instructions` (string): Spoken instructions / voice style for TTS.

URLs format examples

- Simple URL (no display name):
	- `wss://your.gotify.server/stream?token=CLIENT_TOKEN`

- With display name (shown in tray/status):
	- `[Home]wss://gotify.example.com/stream?token=ABC123`

Tray and UI

- Right-click the tray icon to open the menu. Menu entries:
	- Show Window — open the configuration UI.
	- Silent — enable silent mode for the configured `silent_time` minutes.
	- Silent Off — immediately clear silent mode.
	- Servers — quick links to the detected server hosts (opens https://{host}).
	- Exit — stop the app and remove the tray icon.

- The configuration window lets you edit `urls`, choose notification timeout, toggle `ignore_ssl_errors`, select sound behavior, and set TTS voice/instructions.

Text-to-Speech (TTS)

- When `sound` is set to `tts`, the app uses OpenAI TTS to synthesize notification audio and caches MP3 files under a `sounds_cache` directory next to the EXE (or next to the script in development).

- Requirements for TTS:
	- Set the `OPENAI_API_KEY` environment variable with a valid OpenAI API key before running the app.

- TTS-related config keys:
	- `voice` — e.g., `coral` (default), `alloy`, `ash`, `ballad`, `echo`, `fable`, `nova`, `onyx`, `sage`, `shimmer`.
	- `instructions` — text describing speaking style or instructions for the voice.

TTS examples (suggested `instructions` values)

- Concise, friendly assistant:
	- "Speak in a friendly, conversational tone with clear enunciation. Keep it brief."

- Formal briefing:
	- "Read aloud in a clear, neutral voice as if presenting an alert. Use proper nouns and spell out acronyms."

- Energetic notification:
	- "Speak in an upbeat, energetic tone with slight emphasis on short phrases."

- Calm, soft voice:
	- "Speak softly and slowly with a calm, reassuring tone."

Build / Packaging

- The provided `build.ps1` script creates a Windows venv, installs dependencies, and builds a single-file, windowed EXE using PyInstaller (name: `GotifyClient.exe`). The script attempts to include `notify_client.ico` and `sound_file.mp3` as data files.

```powershell
# From the repo root (PowerShell)
./build.ps1
```

Install / Uninstall (no admin required)

- After building, run the EXE with `--install` to copy the EXE and assets to `%LOCALAPPDATA%\\Programs\\GotifyWinClient` and create a Startup shortcut.

```powershell
# From dist folder (where GotifyClient.exe is located)
./GotifyClient.exe --install
```

- To remove the installed files and the Startup shortcut:

```powershell
./GotifyClient.exe --uninstall
```

Notes and differences from older README

- The config filename is `gotify-win-client-config.yaml` in the user's home directory (not `~/gotify.yaml`).
- The tray app uses `winotify` for native Windows toasts (ensure you're on Windows 10/11).
- TTS uses OpenAI's AsyncOpenAI TTS API and requires `OPENAI_API_KEY` (set as an environment variable).
- The app supports `sound_file.mp3` next to the EXE for custom sound playback; place your MP3 in the same folder, or configure the `sound` key.

Troubleshooting

- If notifications are not visible, check Windows Focus Assist / Do Not Disturb settings.
- If WebSocket connections repeatedly fail due to TLS/SSL, you can toggle `ignore_ssl_errors` to true (only for trusted/self-signed servers).
- If TTS fails, confirm `OPENAI_API_KEY` is set and your network allows outgoing connections to OpenAI.

License

GNU General Public License v3.0 (GPL-3.0). See LICENSE.

