# Phase 2: Bridge Implementation - Research

**Researched:** 2026-03-29
**Domain:** MQTT-to-ALSA volume bridge + frontend UI update
**Confidence:** HIGH

## User Constraints (from Phase 1 findings)

### Locked Decisions
- Volume control via `amixer sset PCM` on Dragonfly Black DAC — confirmed working in Phase 1
- ALSA mixer control name: `PCM`
- MQTT topic: `shairport-sync/remote` on localhost:1883, no auth
- Frontend publishes: `volumeup`, `volumedown`, `mutetoggle` (plus `playpause`, `nextitem`, `previtem` which are no-ops)
- Play/pause/skip buttons must be visually disabled or removed from UI
- Pi: Debian 13 (trixie), user `mike`

## Bridge Architecture

### Technology
- **Python 3** with `paho-mqtt` for MQTT subscription
- **subprocess** calls to `amixer` for volume control (no D-Bus needed)
- Single-file script, ~50-80 lines

### Command Mapping

| MQTT Payload | Action | Command |
|-------------|--------|---------|
| `volumeup` | Increase volume by step | `amixer sset PCM 5%+` |
| `volumedown` | Decrease volume by step | `amixer sset PCM 5%-` |
| `mutetoggle` | Toggle mute | `amixer sset PCM toggle` |
| `playpause` | No-op | Log and ignore |
| `nextitem` | No-op | Log and ignore |
| `previtem` | No-op | Log and ignore |

### Volume Step Size
- 5% is a reasonable default step for volume up/down
- `amixer sset PCM 5%+` and `5%-` handle clamping at 0/100 automatically

### Mute Toggle
- `amixer sset PCM toggle` toggles between muted and unmuted
- Alternative: `amixer sset PCM mute` / `amixer sset PCM unmute` for explicit control

### Error Handling
- Wrap subprocess calls in try/except
- Log errors to stdout (journald captures this)
- Never crash on amixer failure — log and continue

## Frontend Changes

### Current State (nowplaying.html)
- Play/pause button: `.btn-playpause` (80px green circle)
- Skip buttons: `.btn-skip` (56px grey circles for prev/next)
- Volume section: `.volume-section` with volume track and up/down buttons
- `sendCmd()` publishes to `shairport-sync/remote` via MQTT

### Required Changes
1. Remove or visually disable play/pause button and skip buttons
2. Keep volume controls functional
3. Rearrange layout to fill space left by removed controls

### Approach Options
- **Option A: Remove entirely** — Delete the `.controls` div containing play/pause/skip. Simpler layout.
- **Option B: Grey out** — Add `opacity: 0.3; pointer-events: none` to playback buttons. Shows they exist but aren't functional.
- Recommendation: Remove entirely — cleaner UX, no confusion about non-functional buttons.

## Validation Architecture

Phase 2 is a code-writing phase with two components:
1. Python bridge script — testable by running and sending MQTT messages
2. HTML frontend changes — testable by visual inspection

### Testing Approach
- Bridge: `mosquitto_pub -t 'shairport-sync/remote' -m 'volumeup'` while bridge runs
- Frontend: Open in browser, verify buttons removed/disabled
- Integration: Full end-to-end from touchscreen tap to volume change

## Dependencies
- `paho-mqtt` Python package (install via pip in venv or apt)
- `amixer` (already present — part of alsa-utils)
- Mosquitto running on localhost:1883

## Risks
- LOW: amixer command syntax varies between ALSA versions — but we confirmed the exact command works in Phase 1
- LOW: paho-mqtt v2 has breaking API changes — use CallbackAPIVersion.VERSION2
