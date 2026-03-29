# Roadmap: AirPlay Now Playing Controller

## Overview

Four phases deliver a working MQTT-to-D-Bus bridge that makes the touchscreen control buttons functional. Phase 1 verifies the hardware environment before writing any code — two showstopper blockers (D-Bus interface absent, AirPlay 2 DACP broken) can only be confirmed on the real Pi. Phases 2-4 build, deploy, and harden the bridge in sequence.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Environment Verification** - Confirm D-Bus interface, AirPlay 2 compatibility, and MQTT flow on the actual Pi before writing any code
- [ ] **Phase 2: Bridge Implementation** - Build the MQTT-to-D-Bus bridge that maps all six touchscreen commands to Shairport-Sync D-Bus methods
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
**Plans:** 1 plan
Plans:
- [ ] 01-01-PLAN.md — Verify D-Bus, AirPlay 2 control, and MQTT flow on real Pi hardware

### Phase 2: Bridge Implementation
**Goal**: Touchscreen control buttons work end-to-end — all six commands received from MQTT and forwarded to Shairport-Sync via D-Bus
**Depends on**: Phase 1
**Requirements**: CTRL-01, CTRL-02, CTRL-03, CTRL-04, CTRL-05, CTRL-06
**Success Criteria** (what must be TRUE):
  1. Tapping play/pause on the touchscreen pauses and resumes AirPlay playback
  2. Tapping next/previous on the touchscreen skips tracks on the streaming device
  3. Tapping volume up/down on the touchscreen changes the AirPlay volume level
  4. Tapping mute on the touchscreen toggles mute on the AirPlay stream
  5. The bridge continues running and does not crash when a D-Bus call fails (e.g., no active AirPlay session)
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
| 1. Environment Verification | 0/1 | Not started | - |
| 2. Bridge Implementation | 0/? | Not started | - |
| 3. Service Deployment | 0/? | Not started | - |
| 4. Reliability Hardening | 0/? | Not started | - |
