# Requirements: AirPlay Now Playing Controller

**Defined:** 2026-03-29
**Core Value:** The control buttons on the touchscreen display must actually control AirPlay playback on the Pi.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Playback Control

- [ ] **CTRL-04**: User can increase volume from touchscreen (via ALSA amixer)
- [ ] **CTRL-05**: User can decrease volume from touchscreen (via ALSA amixer)
- [ ] **CTRL-06**: User can toggle mute from touchscreen (via ALSA amixer)

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
| **CTRL-01**: Play/pause control | DACP permanently broken on modern iOS (confirmed Phase 1 verification, issue #1822) |
| **CTRL-02**: Next track control | DACP permanently broken on modern iOS (confirmed Phase 1 verification, issue #1822) |
| **CTRL-03**: Previous track control | DACP permanently broken on modern iOS (confirmed Phase 1 verification, issue #1822) |
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
| CTRL-01 | — | Out of Scope (DACP broken, Phase 1) |
| CTRL-02 | — | Out of Scope (DACP broken, Phase 1) |
| CTRL-03 | — | Out of Scope (DACP broken, Phase 1) |
| CTRL-04 | Phase 2 | Pending (via ALSA amixer) |
| CTRL-05 | Phase 2 | Pending (via ALSA amixer) |
| CTRL-06 | Phase 2 | Pending (via ALSA amixer) |
| SRVC-01 | Phase 3 | Pending |
| SRVC-02 | Phase 3 | Pending |
| SRVC-03 | Phase 3 | Pending |
| RELY-01 | Phase 4 | Pending |
| RELY-02 | Phase 4 | Pending |
| RELY-03 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 9 active (3 descoped to Out of Scope after Phase 1 verification)
- Mapped to phases: 9
- Unmapped: 0
- Out of Scope: CTRL-01, CTRL-02, CTRL-03 (DACP broken on modern iOS)

---
*Requirements defined: 2026-03-29*
*Last updated: 2026-03-29 after roadmap creation*
