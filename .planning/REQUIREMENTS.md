# Requirements: AirPlay Now Playing Controller

**Defined:** 2026-03-29
**Core Value:** The control buttons on the touchscreen display must actually control AirPlay playback on the Pi.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Playback Control

- [ ] **CTRL-01**: User can play/pause playback from touchscreen
- [ ] **CTRL-02**: User can skip to next track from touchscreen
- [ ] **CTRL-03**: User can skip to previous track from touchscreen
- [ ] **CTRL-04**: User can increase volume from touchscreen
- [ ] **CTRL-05**: User can decrease volume from touchscreen
- [ ] **CTRL-06**: User can toggle mute from touchscreen

### Service

- [ ] **SRVC-01**: Bridge service starts automatically at boot via systemd
- [ ] **SRVC-02**: Bridge service handles D-Bus errors gracefully without crashing
- [ ] **SRVC-03**: Bridge service logs received commands and D-Bus results to journald

### Reliability

- [ ] **RELY-01**: Bridge service reconnects automatically if Mosquitto restarts
- [ ] **RELY-02**: MQTT topic prefix is configurable via environment variable
- [ ] **RELY-03**: Bridge logs a clear warning at startup if Mosquitto or D-Bus is unreachable

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Reliability

- **RELY-04**: MQTT Last Will and Testament for bridge health monitoring
- **RELY-05**: Configurable D-Bus bus type (system vs session) via environment variable

## Out of Scope

| Feature | Reason |
|---------|--------|
| Absolute volume set (drag-to-value) | Shairport-Sync SetVolume has limited device support; AirPlay volume range is non-obvious |
| Bidirectional state sync | Shairport-Sync already publishes state to MQTT; bridge duplicating creates message loops |
| HTTP REST API | MQTT is the agreed IPC layer; no need for another protocol |
| Command queueing/retry | Commands are time-sensitive; retrying stale commands causes unexpected behavior |
| Multi-room support | Single Pi setup; explicitly out of scope |
| Non-AirPlay sources | Shairport-Sync only |
| UI redesign | Current display works fine |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CTRL-01 | — | Pending |
| CTRL-02 | — | Pending |
| CTRL-03 | — | Pending |
| CTRL-04 | — | Pending |
| CTRL-05 | — | Pending |
| CTRL-06 | — | Pending |
| SRVC-01 | — | Pending |
| SRVC-02 | — | Pending |
| SRVC-03 | — | Pending |
| RELY-01 | — | Pending |
| RELY-02 | — | Pending |
| RELY-03 | — | Pending |

**Coverage:**
- v1 requirements: 12 total
- Mapped to phases: 0
- Unmapped: 12 ⚠️

---
*Requirements defined: 2026-03-29*
*Last updated: 2026-03-29 after initial definition*
