# AirPlay Now Playing Controller

## What This Is

A "now playing" kiosk display for a Raspberry Pi with a 1024x600 touchscreen, showing AirPlay track metadata from Shairport-Sync via MQTT. Currently displays track info but cannot control playback — needs a backend bridge to translate MQTT commands into D-Bus calls to Shairport-Sync.

## Core Value

The control buttons (play/pause, next/prev, volume) on the touchscreen display must actually control AirPlay playback on the Pi.

## Requirements

### Validated

- ✓ Display current track title, artist, album — existing
- ✓ Display album artwork from AirPlay stream — existing
- ✓ Show playback progress with elapsed/total time — existing
- ✓ Show current volume level — existing
- ✓ Show idle clock screen when nothing is playing — existing
- ✓ Show AirPlay client name ("Playing from") — existing

### Active

- [ ] Play/pause control from touchscreen
- [ ] Next/previous track control from touchscreen
- [ ] Volume up/down/mute control from touchscreen

### Out of Scope

- Additional UI features or redesign — current display works fine
- Multi-room/multi-speaker support — single Pi setup
- Non-AirPlay sources — Shairport-Sync only

## Context

- Raspberry Pi running Mosquitto (MQTT broker) and Shairport-Sync (AirPlay receiver)
- Shairport-Sync publishes metadata to MQTT topics under `shairport-sync/#`
- Shairport-Sync exposes a D-Bus interface for playback control
- Frontend is a single HTML file connecting to Mosquitto via WebSocket on port 9001
- Frontend already publishes commands to `shairport-sync/remote` — nothing is listening
- The bridge service needs to subscribe to that MQTT topic and call D-Bus methods on Shairport-Sync

## Constraints

- **Platform**: Raspberry Pi — lightweight service, minimal dependencies
- **Tech stack**: Must integrate with Mosquitto (MQTT) and Shairport-Sync (D-Bus)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| MQTT→D-Bus bridge approach | Frontend already publishes to MQTT; Shairport-Sync already exposes D-Bus | — Pending |

---
*Last updated: 2025-03-29 after initialization*
