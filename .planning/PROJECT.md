# AirPlay Now Playing Controller

## What This Is

A "now playing" kiosk display for a Raspberry Pi with a 1024x600 touchscreen, showing AirPlay track metadata from Shairport-Sync via MQTT. Needs a backend bridge to translate MQTT volume commands into ALSA mixer calls, and a UI update to remove non-functional playback controls.

## Core Value

Volume control from the touchscreen must work. Play/pause/skip are permanently broken due to Apple removing DACP from modern iOS — UI should reflect this.

## Requirements

### Validated

- ✓ Display current track title, artist, album — existing
- ✓ Display album artwork from AirPlay stream — existing
- ✓ Show playback progress with elapsed/total time — existing
- ✓ Show current volume level — existing
- ✓ Show idle clock screen when nothing is playing — existing
- ✓ Show AirPlay client name ("Playing from") — existing

### Active

- [ ] Volume up/down/mute control from touchscreen (via ALSA amixer)
- [ ] Remove or grey out play/pause/skip buttons in UI

### Out of Scope

- Play/pause control — DACP permanently broken on modern iOS (Phase 1 verified)
- Next/previous track control — DACP permanently broken on modern iOS (Phase 1 verified)
- Multi-room/multi-speaker support — single Pi setup
- Non-AirPlay sources — Shairport-Sync only

## Context

- Raspberry Pi running Mosquitto (MQTT broker) and Shairport-Sync (AirPlay receiver)
- Shairport-Sync publishes metadata to MQTT topics under `shairport-sync/#`
- Shairport-Sync 5.0.2 compiled from source with AirPlay2, dbus-interface, mqtt, metadata, ALSA, soxr
- D-Bus interface is present but DACP remote control is non-functional (Available=false on modern iOS)
- Volume control works via ALSA: `amixer sset PCM` on Dragonfly Black DAC
- Frontend is a single HTML file connecting to Mosquitto via WebSocket on port 9001
- Frontend publishes commands to `shairport-sync/remote` — bridge will listen for volume commands
- Pi runs Debian 13 (trixie), user `mike`, Mosquitto on 9001/1883, no auth

## Constraints

- **Platform**: Raspberry Pi — lightweight service, minimal dependencies
- **Tech stack**: Must integrate with Mosquitto (MQTT) and ALSA (amixer) for volume control
- **DACP limitation**: Apple removed DACP-ID from AirPlay sessions in iOS 17.4+ — play/pause/skip cannot be controlled from the Pi

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| MQTT→D-Bus bridge approach | Frontend already publishes to MQTT; Shairport-Sync already exposes D-Bus | ⚠️ Revisit — DACP broken |
| Pivot to ALSA volume-only | D-Bus RemoteControl non-functional on modern iOS; amixer works locally | ✓ Good |
| Remove play/pause/skip from UI | Buttons would do nothing; better UX to remove them | — Pending |

---
*Last updated: 2026-03-29 after Phase 1 verification — pivot to volume-only*
