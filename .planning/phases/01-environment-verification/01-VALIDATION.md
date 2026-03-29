---
phase: 1
slug: environment-verification
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-29
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Manual verification (no code in this phase) |
| **Config file** | none |
| **Quick run command** | N/A — all checks are manual shell commands on the Pi |
| **Full suite command** | Run verification script on Pi |
| **Estimated runtime** | ~5 minutes (requires active AirPlay session) |

---

## Sampling Rate

- **After every task commit:** N/A — no code commits in this phase
- **After every plan wave:** User runs commands on Pi and pastes output
- **Before `/gsd:verify-work`:** All success criteria confirmed via pasted output
- **Max feedback latency:** N/A (manual)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | Gate | manual | `shairport-sync -V` | N/A | ⬜ pending |
| 01-01-02 | 01 | 1 | Gate | manual | `busctl list \| grep -i shairport` | N/A | ⬜ pending |
| 01-01-03 | 01 | 1 | Gate | manual | `dbus-send` PlayPause | N/A | ⬜ pending |
| 01-01-04 | 01 | 1 | Gate | manual | `mosquitto_sub` test | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No test framework needed — this phase produces a verification script, not application code.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| D-Bus interface presence | Gate | Requires Pi hardware | Run `busctl list \| grep -i shairport` on Pi |
| Playback control | Gate | Requires active AirPlay session + physical device | Play music from iPhone, run `dbus-send` PlayPause, observe pause |
| MQTT message flow | Gate | Requires touchscreen + Mosquitto | Tap button on touchscreen, observe message in `mosquitto_sub` |
| D-Bus policy access | Gate | Requires specific user context on Pi | Run D-Bus command as custom user, check for AccessDenied |

*All phase behaviors are manual — this is a hardware verification gate.*

---

## Validation Sign-Off

- [x] All tasks have manual verify instructions
- [x] No automated tests needed (no code produced)
- [x] Wave 0 not applicable
- [x] No watch-mode flags
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
