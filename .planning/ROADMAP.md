# Roadmap: AirPlay Now Playing Controller

## Overview

Four phases deliver a working MQTT-to-ALSA bridge that makes the touchscreen volume control buttons functional. Phase 1 verified the hardware environment — D-Bus interface is present but DACP is permanently broken on modern iOS, so play/pause/next/prev are descoped. Phases 2-4 build, deploy, and harden a volume-only bridge (amixer sset PCM) in sequence.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Environment Verification** - Confirm D-Bus interface, AirPlay 2 compatibility, and MQTT flow on the actual Pi before writing any code (completed 2026-03-29)
- [ ] **Phase 2: Bridge Implementation** - Build the MQTT-to-ALSA bridge for volume control (volumeup, volumedown, mutetoggle) via amixer; grey out play/pause/skip buttons
- [ ] **Phase 3: Service Deployment** - Package the bridge as a systemd service with boot start, journald logging, and graceful error handling
- [ ] **Phase 4: Reliability Hardening** - Add MQTT auto-reconnect, configurable topic prefix, and startup connectivity warnings

## Phase Details

### Phase 1: Environment Verification
**Goal**: Confirmed working D-Bus interface and AirPlay 2 remote control on the actual Pi, with MQTT message flow verified end-to-end
**Depends on**: Nothing (first phase)
**Requirements**: None (precondition gate — unblocks all subsequent phases)
**Success Criteria** (what must be TRUE):
  1. `busctl list` on the Pi shows `org.gnome.ShairportSync` — D-Bus interface is compiled in and accessible
  2. `dbus-send` PlayPause from the pi user causes the streaming device to pause — AirPlay 2 remote control is functional
  3. `mosquitto_sub -t 'shairport-sync/#' -v` shows button press messages arriving when the touchscreen is tapped — MQTT topic alignment confirmed
  4. D-Bus policy grants the pi user `send_destination` access to `org.gnome.ShairportSync` without AccessDenied errors
**Plans:** 1/1 plans complete
Plans:
- [x] 01-01-PLAN.md — Verify D-Bus, AirPlay 2 control, and MQTT flow on real Pi hardware (PARTIAL PASS: D-Bus/MQTT pass, DACP fail — pivot to volume-only)

### Phase 2: Bridge Implementation
**Goal**: Volume control buttons work end-to-end — volumeup/volumedown/mutetoggle received from MQTT and executed via ALSA amixer on the Dragonfly Black DAC (PCM mixer). Play/pause/next/prev buttons greyed out in UI.
**Depends on**: Phase 1
**Requirements**: CTRL-04, CTRL-05, CTRL-06 (CTRL-01/02/03 descoped — DACP broken)
**Success Criteria** (what must be TRUE):
  1. Tapping volume up on the touchscreen increases the Pi's audio output volume via `amixer sset PCM`
  2. Tapping volume down on the touchscreen decreases the Pi's audio output volume via `amixer sset PCM`
  3. Tapping mute on the touchscreen toggles mute on the PCM mixer
  4. Play/pause and next/prev buttons are visually disabled or hidden in the UI
  5. The bridge continues running and does not crash when an amixer command fails
**Plans**: TBD

### Phase 3: Service Deployment
**Goal**: The bridge runs automatically at boot, survives reboots, and produces useful logs via journald
**Depends on**: Phase 2
**Requirements**: SRVC-01, SRVC-02, SRVC-03
**Success Criteria** (what must be TRUE):
  1. After a reboot, the bridge is running without any manual intervention — `systemctl status airplay-bridge` shows active
  2. Bridge log output is visible via `journalctl -u airplay-bridge -f` showing received commands and D-Bus results
  3. The bridge does not crash when Shairport-Sync is unavailable or returns a D-Bus error — it logs the error and continues
  4. The service restarts automatically if the bridge process dies
**Plans**: TBD

### Phase 4: Reliability Hardening
**Goal**: The bridge recovers automatically from MQTT disconnects, is configurable for different environments, and provides clear startup diagnostics
**Depends on**: Phase 3
**Requirements**: RELY-01, RELY-02, RELY-03
**Success Criteria** (what must be TRUE):
  1. Restarting Mosquitto while the bridge is running causes the bridge to reconnect automatically without requiring a service restart
  2. The MQTT topic prefix can be changed by setting an environment variable — no code edit required
  3. At startup, the bridge logs a clear warning if Mosquitto is unreachable or the D-Bus interface is not found, rather than silently failing
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Environment Verification | 1/1 | Complete (partial pass) | 2026-03-29 |
| 2. Bridge Implementation | 0/? | Not started | - |
| 3. Service Deployment | 0/? | Not started | - |
| 4. Reliability Hardening | 0/? | Not started | - |
