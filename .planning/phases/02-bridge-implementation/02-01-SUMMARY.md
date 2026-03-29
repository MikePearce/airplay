---
phase: 02-bridge-implementation
plan: 01
subsystem: infra
tags: [python, mqtt, paho-mqtt, alsa, amixer, html, ui]

requires:
  - phase: 01-environment-verification
    provides: Confirmed amixer PCM mixer working on Dragonfly Black DAC, MQTT broker accessible at localhost:1883

provides:
  - bridge.py: Python MQTT-to-ALSA bridge subscribing to shairport-sync/remote and calling amixer
  - nowplaying.html: Updated frontend with playback controls removed, dedicated volume-down button added

affects:
  - 02-bridge-implementation
  - 03-display-integration

tech-stack:
  added: [paho-mqtt 2.x (CallbackAPIVersion.VERSION2)]
  patterns:
    - MQTT subscriber pattern using paho-mqtt v2 callback API
    - subprocess.run with capture_output for amixer commands
    - Graceful error handling — SubprocessError/OSError/TimeoutExpired caught, bridge never crashes

key-files:
  created: [bridge.py]
  modified: [nowplaying.html]

key-decisions:
  - "Volume-down button added to UI as dedicated button (not just via volume track click) for improved touchscreen UX"
  - "Playback controls fully removed (not greyed out) — DACP confirmed broken, cleaner UX without dead buttons"
  - "paho-mqtt v2 CallbackAPIVersion.VERSION2 used — future-proof against deprecation of v1 callback signatures"

patterns-established:
  - "Bridge pattern: decode MQTT payload -> lookup in COMMANDS dict -> subprocess.run amixer"
  - "Ignored payloads logged at DEBUG, unknown payloads at WARNING — no crash on unexpected input"

requirements-completed: [CTRL-04, CTRL-05, CTRL-06]

duration: 8min
completed: 2026-03-29
---

# Phase 2 Plan 01: Bridge Implementation Summary

**paho-mqtt v2 Python bridge maps volumeup/volumedown/mutetoggle MQTT commands to amixer sset PCM calls, with nowplaying.html stripped of all playback controls and a dedicated volume-down button added**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-29T18:39:34Z
- **Completed:** 2026-03-29T18:47:00Z
- **Tasks:** 2 of 3 (Task 3 is human-verify checkpoint — awaiting Pi hardware test)
- **Files modified:** 2

## Accomplishments
- bridge.py created: subscribes to shairport-sync/remote, maps 3 volume commands to amixer, ignores play/skip, never crashes on subprocess failure
- nowplaying.html updated: .controls div removed, associated CSS removed, iconPlay/iconPause JS references removed, setPlaying() simplified
- Volume-down button added between mute and volume track for dedicated tap target

## Task Commits

Each task was committed atomically:

1. **Task 1: Create MQTT-to-ALSA bridge** - `91cbe4e` (feat)
2. **Task 2: Remove playback controls from frontend UI** - `6bc6dc2` (feat)

Task 3 (human-verify) is a checkpoint — awaiting user confirmation on Pi hardware.

## Files Created/Modified
- `/Users/mikepearce/projects/airplay/bridge.py` - MQTT subscriber that calls amixer for volume control
- `/Users/mikepearce/projects/airplay/nowplaying.html` - Frontend with play/pause/skip removed, volume-down button added

## Decisions Made
- Volume-down button added as a dedicated HTML button (not relying solely on volume track click handler) — better touchscreen usability now that volume is the primary control
- Used paho-mqtt v2 API (CallbackAPIVersion.VERSION2) — avoids deprecation warnings present in v1-style callbacks
- Playback controls removed entirely (not greyed out) as specified — DACP is permanently broken on modern iOS

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required

**Hardware verification required.** To complete Task 3:

1. Copy bridge.py to the Pi: `scp bridge.py mike@192.168.1.182:~/`
2. SSH to the Pi and install paho-mqtt if not already: `pip3 install paho-mqtt`
3. Run the bridge: `python3 ~/bridge.py`
4. Copy updated nowplaying.html to the Pi display location
5. Open nowplaying.html on the touchscreen display
6. Verify: Play/pause and skip buttons are gone — only mute, volume-down, volume track, and volume-up visible
7. Start AirPlay playback to the Pi
8. Tap volume up, down, and mute — confirm audio changes and bridge logs show amixer commands executing

## Next Phase Readiness
- bridge.py is ready to deploy to Pi
- nowplaying.html is ready to deploy to Pi display
- Pending: Task 3 human-verify confirmation from user after Pi hardware test
- Once confirmed, Phase 2 complete and Phase 3 (display integration / systemd service) can begin

---
*Phase: 02-bridge-implementation*
*Completed: 2026-03-29*
