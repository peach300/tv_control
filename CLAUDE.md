# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An LG WebOS TV control system with two components:

1. **`tv_server/tv_server.py`** — A Flask HTTP API server that runs as a Windows system tray app. It manages a persistent WebSocket connection to the TV via `bscpylgtv`, and exposes REST endpoints for controlling the TV (volume, input, buttons, apps) plus PC-side side effects (audio switching via `nircmd.exe`, DPI scaling via `SetDpi.exe`).

2. **`unified_remote/`** — A custom [Unified Remote](https://www.unifiedremote.com/) layout. `remote.lua` maps button actions to HTTP calls against the server. `layout.xml` defines the mobile UI.

## Running the server

From `tv_server/`:
```powershell
.\tv_control.ps1        # guards against double-launch, then runs: uvw run tv_server.py
```
Or directly:
```powershell
uvw run tv_server.py
```

The server uses a `.venv` at the repo root. `uvw` resolves it automatically.

## Configuration

All runtime config lives in `tv_server/config.yaml`. Key fields:

- `tv.ip` — TV's local IP address
- `tv.pc_input` / `tv.default_input` — HDMI input names (`HDMI_1`–`HDMI_4`)
- `tv.audio_source` / `pc.audio_source` — Windows audio device names passed to `nircmd.exe`
- `tv.resolution_scale` / `pc.resolution_scale` — DPI percent passed to `SetDpi.exe`
- `pc.monitor_index` — monitor index for `SetDpi.exe`
- `server.port` — Flask port (default `8765`)
- `idle.timeout_seconds` — auto-revert to PC mode after inactivity (`0` = disabled)

## Architecture notes

**Two-mode design:** The server tracks a `_current_mode` (`'tv'` or `'pc'`). `/tv/quick-toggle` atomically switches input, audio device, and DPI scale together. The tray icon also exposes TV/PC mode switching by calling the same HTTP endpoint internally.

**Async bridge:** `TVConnection` runs an asyncio event loop on a background thread. Flask routes call `tv.run(lambda c: ...)` which submits a coroutine via `run_coroutine_threadsafe` and blocks for up to `COMMAND_TIMEOUT` seconds.

**Reconnection:** On any command failure or keepalive miss, the client clears `_connected` and fires `_connect()` as a new task on the same loop. The tray icon color reflects state: green = connected, yellow = reconnecting, red = disconnected.

**Idle watchdog:** A daemon thread checks every 30s; if `_current_mode == 'tv'` and no `/tv/` request has succeeded in `idle.timeout_seconds`, it reverts to PC mode. Can be suppressed by TV media apps (`idle.tv_media_apps`) or a PC-side shell command (`idle.pc_media_check_cmd`, exit 0 = media playing).

**`apps.json`** — maps human-readable app names to WebOS app IDs. Not loaded at runtime; used as a reference when adding launch actions to the remote.

## Unified Remote installation

Copy `unified_remote/` contents into:
```
%PROGRAMDATA%\Unified Remote\Remotes\Custom\LG TV\
```
Restart the Unified Remote server. Requires the `luasocket` Lua module (`luarocks install luasocket`). The remote's `server_url` setting must point to `http://<PC-IP>:8765/`.
