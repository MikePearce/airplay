---
phase: 2
slug: bridge-implementation
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-29
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Shell commands + manual verification |
| **Config file** | none |
| **Quick run command** | `python3 -c "import ast; ast.parse(open('bridge.py').read())"` |
| **Full suite command** | `mosquitto_pub -h localhost -t 'shairport-sync/remote' -m 'volumeup'` while bridge runs |
| **Estimated runtime** | ~10 seconds (automated) + manual touchscreen test |

---

## Sampling Rate

- **After every task commit:** Run quick syntax check
- **After every plan wave:** Manual end-to-end test on Pi
- **Before `/gsd:verify-work`:** Full touchscreen-to-volume test
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | CTRL-04/05/06 | automated | `python3 -c "import ast; ast.parse(open('bridge.py').read())" && grep -q "amixer.*sset.*PCM" bridge.py` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | CTRL-04/05/06 | automated | `! grep -q "btn-playpause" nowplaying.html && grep -q "volume-section" nowplaying.html` | ✅ | ⬜ pending |
| 02-01-03 | 01 | 1 | CTRL-04/05/06 | manual | User tests on Pi hardware | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `bridge.py` — created in Task 1
- [ ] `paho-mqtt` — must be installed on Pi (pip3 install paho-mqtt)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Volume up changes audio output | CTRL-04 | Requires Pi hardware + DAC | Tap volume up, listen for volume change |
| Volume down changes audio output | CTRL-05 | Requires Pi hardware + DAC | Tap volume down, listen for volume change |
| Mute toggles audio | CTRL-06 | Requires Pi hardware + DAC | Tap mute, listen for silence/audio |
| UI shows no playback buttons | UI cleanup | Requires visual inspection | Open nowplaying.html, verify no play/skip buttons |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or manual verify instructions
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
