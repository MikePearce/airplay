---
phase: 01-environment-verification
plan: 01
subsystem: infra
tags: [dbus, shairport-sync, mqtt, alsa, amixer, raspberry-pi, airplay]

# Dependency graph
requires:
  - phase: none
    provides: first phase
provides:
  - "Verified D-Bus interface compiled in and registered on system bus"
  - "Confirmed DACP playback control permanently broken on modern iOS — play/pause/next/prev descoped"
  - "Confirmed ALSA amixer volume control works as alternative to D-Bus volume"
  - "Confirmed MQTT topic flow from touchscreen to broker"
  - "Phase 2 pivot decision: volume-only bridge via ALSA amixer instead of D-Bus RemoteControl"
affects: [02-bridge-implementation, 03-service-deployment, 04-reliability-hardening]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Volume control via amixer sset PCM (not D-Bus) — Dragonfly Black DAC with PCM mixer"
    - "MQTT topic contract: shairport-sync/remote receives playpause, nextitem, previtem, mutetoggle, volumeup, volumedown"

key-files:
  created:
    - ".planning/phases/01-environment-verification/VERIFICATION-CHECKLIST.md"
    - ".planning/phases/01-environment-verification/01-01-SUMMARY.md"
  modified: []

key-decisions:
  - "Pivot to volume-only bridge — DACP broken permanently on modern iOS, confirmed on real hardware"
  - "Volume control via ALSA amixer sset PCM instead of D-Bus VolumeUp/VolumeDown/SetAirplayVolume"
  - "CTRL-01, CTRL-02, CTRL-03 descoped to Out of Scope — play/pause/next/prev impossible without working DACP"
  - "CTRL-04, CTRL-05, CTRL-06 proceed with ALSA amixer implementation instead of D-Bus"

patterns-established:
  - "Verification-first gating: hardware test before code prevents wasted implementation effort"
  - "ALSA mixer path: amixer sset PCM <value> controls volume on the Dragonfly Black DAC"

requirements-completed: []

# Metrics
duration: 8min
completed: 2026-03-29
---

# Phase 1 Plan 01: Environment Verification Summary

**D-Bus interface confirmed present; DACP playback control permanently broken on modern iOS; pivot to volume-only bridge via ALSA amixer with PCM mixer on Dragonfly Black DAC**

## Performance

- **Duration:** ~8 min (checklist creation) + user verification time on Pi
- **Started:** 2026-03-29T16:56:38Z
- **Completed:** 2026-03-29T17:10:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created comprehensive six-step verification checklist with dependency-ordered diagnostics
- Confirmed D-Bus interface compiled in, registered on system bus, and policy correctly configured
- Confirmed MQTT topic flow from touchscreen to broker is working
- Identified that DACP is completely non-functional on modern iOS — not just play/pause but also D-Bus VolumeUp/VolumeDown and SetAirplayVolume all fail
- Discovered working alternative: ALSA `amixer sset PCM` controls local output volume on the Dragonfly Black DAC
- Secured user decision to pivot to volume-only bridge with ALSA amixer

## Environment Details

| Property | Value |
|----------|-------|
| Username | mike |
| Shairport-Sync version | 5.0.2 |
| Compile flags | OpenSSL-Avahi-ALSA-soxr-metadata-mqtt-dbus-sysconfdir:/etc |
| AirPlay 2 | Removed (recompiled from source without AirPlay 2) |
| Pi OS | Debian 13 (trixie) |
| DAC | Dragonfly Black (PCM mixer control via ALSA) |

## Verification Results

| # | Success Criterion | Result | Notes |
|---|------------------|--------|-------|
| 1 | `busctl list` shows `org.gnome.ShairportSync` | PASS | D-Bus interface compiled in and registered |
| 2 | `dbus-send PlayPause` causes device to pause | FAIL | `method return` received but device does not pause; `Available` property on RemoteControl is `false` even in AirPlay 1 mode |
| 3 | `mosquitto_sub` shows button press messages | PASS | `playpause`, `nextitem`, `previtem` arrive on `shairport-sync/remote` |
| 4 | No `AccessDenied` from D-Bus calls | PASS | `<policy context="default">` grants access to all users including `mike` |

### DACP Failure Analysis

The user had already recompiled Shairport-Sync from source without AirPlay 2 (`--without-airplay2`) based on 01-RESEARCH.md Path B guidance. Despite this:

- `dbus-send PlayPause` returns `method return` (no error) but playback does NOT pause
- The `Available` property on `org.gnome.ShairportSync.RemoteControl` reads `false` even during active AirPlay streaming
- `VolumeUp` and `VolumeDown` via D-Bus also do nothing
- `SetAirplayVolume` via D-Bus also does nothing
- DACP is completely non-functional regardless of AirPlay 1 vs AirPlay 2 mode

This confirms the DACP breakage is more extensive than originally documented — it affects all remote control operations, not just play/pause/next/prev. The D-Bus interface itself works (bus registration, policy, method calls complete without error) but the downstream DACP dispatch has no valid target.

### Working Alternative: ALSA Volume Control

- `amixer sset PCM 50%` successfully changes the local output volume
- The Pi has a Dragonfly Black DAC with a PCM mixer control accessible via ALSA
- This is independent of D-Bus, DACP, and AirPlay entirely — it controls the local audio output directly
- Volume changes are audible immediately during active AirPlay streaming

## Task Commits

Each task was committed atomically:

1. **Task 1: Create verification checklist document** - `603eff2` (docs)
2. **Task 2: Run verification checklist and analyze results** - this summary (docs)

## Files Created/Modified

- `.planning/phases/01-environment-verification/VERIFICATION-CHECKLIST.md` - Six-step diagnostic checklist with copy-pasteable commands
- `.planning/phases/01-environment-verification/01-01-SUMMARY.md` - This summary with verification findings

## Decisions Made

1. **Pivot to volume-only bridge** — DACP is permanently broken on modern iOS. Play/pause/next/prev control is impossible without a working DACP path. The user chose to accept volume-only control rather than further recompilation attempts.

2. **Volume via ALSA amixer instead of D-Bus** — D-Bus VolumeUp/VolumeDown and SetAirplayVolume are all non-functional (they route through DACP). Direct ALSA mixer control via `amixer sset PCM` works reliably on the Dragonfly Black DAC.

3. **Descope CTRL-01, CTRL-02, CTRL-03** — Play/pause, next track, and previous track requirements moved to Out of Scope. No viable implementation path exists on current iOS.

4. **CTRL-04, CTRL-05, CTRL-06 implementation change** — Volume up, volume down, and mute toggle proceed but use ALSA amixer subprocess calls instead of D-Bus method calls. The bridge architecture changes from MQTT-to-D-Bus to MQTT-to-ALSA for volume commands.

## Deviations from Plan

None for Task 1 — plan executed exactly as written.

Task 2 findings represent the expected "fail path" documented in the plan. The DACP failure was more extensive than anticipated (all D-Bus remote control operations broken, not just play/pause), but this was the exact scenario Phase 1 was designed to detect.

## Issues Encountered

- DACP breakage is more severe than documented in 01-RESEARCH.md. Even with AirPlay 2 removed (recompiled with `--without-airplay2`), the `RemoteControl.Available` property is `false` and no remote commands work. This suggests the DACP path is broken at the iOS sender level, not just the AirPlay 2 protocol level.
- D-Bus volume methods (VolumeUp, VolumeDown, SetAirplayVolume) are also non-functional, which was not anticipated. These were assumed to be ALSA-local but they apparently also route through DACP or require an active remote control session.

## User Setup Required

None - no external service configuration required.

## Impact on Subsequent Phases

### Phase 2: Bridge Implementation

- **Architecture change:** Bridge is now MQTT-to-ALSA (subprocess `amixer` calls) instead of MQTT-to-D-Bus
- **Reduced scope:** Only 3 commands need implementation (volumeup, volumedown, mutetoggle) instead of 6
- **Technology change:** Python `subprocess.run(["amixer", "sset", "PCM", ...])` replaces `jeepney` D-Bus library
- **Dependency change:** `jeepney` may no longer be needed if no D-Bus calls remain; only `paho-mqtt` required
- **UI change:** Play/pause/next/prev buttons should be greyed out or hidden in `nowplaying.html`

### Phase 3: Service Deployment

- No fundamental change — systemd service still needed
- Error handling shifts from D-Bus errors to amixer subprocess errors

### Phase 4: Reliability Hardening

- D-Bus connectivity check at startup may be removed or reduced to informational
- MQTT reconnect logic unchanged

## Next Phase Readiness

Phase 2 is PARTIALLY UNBLOCKED:
- Volume control bridge can proceed using ALSA amixer
- Play/pause/next/prev are permanently descoped
- Phase 2 planning must reflect the pivot: MQTT-to-ALSA architecture, reduced command set, UI button changes
- Requirements CTRL-01, CTRL-02, CTRL-03 should be moved to Out of Scope in REQUIREMENTS.md
- Requirements CTRL-04, CTRL-05, CTRL-06 remain active but implementation method changes

---
*Phase: 01-environment-verification*
*Completed: 2026-03-29*
