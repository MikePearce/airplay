# Project Research Summary

**Project:** AirPlay Bridge (MQTT-to-D-Bus bridge for Shairport-Sync)
**Domain:** Embedded service integration — MQTT command routing to D-Bus on Raspberry Pi
**Researched:** 2026-03-29
**Confidence:** HIGH

## Executive Summary

This project is a small, single-purpose background service running on a Raspberry Pi that translates MQTT command messages published by a touchscreen frontend (`nowplaying.html`) into D-Bus method calls on Shairport-Sync's `org.gnome.ShairportSync` interface. The architecture is well-understood: Python 3.11 (system default on Pi OS Bookworm) with `paho-mqtt` for MQTT subscription and `jeepney` for pure-Python D-Bus calls, supervised by a systemd unit file. There are no complex distributed systems concerns, no database, no API surface — this is an event loop wiring two existing IPC mechanisms together.

The single biggest risk is the AirPlay 2 / iOS 17.4+ breakage: since Apple removed the DACP-ID from modern AirPlay 2 sessions, playback control commands (play, pause, next, previous) are silently ignored by the streaming device even though the D-Bus call itself completes without error. This is confirmed as a permanent, unresolvable upstream change. The only confirmed workaround is compiling Shairport-Sync without AirPlay 2 support. This must be verified on the actual target device before any bridge code is written — discovering it late would invalidate the core premise of the project.

The recommended build sequence is environment-first: confirm the D-Bus interface exists and is accessible before writing Python. Then implement the D-Bus caller in isolation, add MQTT subscription, wire them together, and finally package as a systemd service. All six commands the frontend already publishes map cleanly to documented D-Bus methods at LOW implementation complexity. The entire service is plausibly a single ~100-line Python file.

## Key Findings

### Recommended Stack

The correct stack is Python 3.11 + `paho-mqtt` 2.1.0 + `jeepney` 0.9.0, deployed in a venv at `/opt/airplay-bridge/venv` under a systemd unit. `jeepney` is preferred over `dbus-python` (marked "Inactive" by maintainers, requires C headers) and `dasbus` (pulls in PyGObject/GLib overhead unnecessary for three method calls). `paho-mqtt` 2.x with `CallbackAPIVersion.VERSION2` is required — VERSION1 is deprecated and will be removed in paho 3.0. Pi OS Bookworm enforces PEP 668, so a venv is mandatory; `--break-system-packages` must never be used.

**Core technologies:**
- Python 3.11: service runtime — ships on Pi OS Bookworm, no install needed
- paho-mqtt 2.1.0: MQTT subscription — canonical Eclipse client, stable callback API, piwheels pre-built
- jeepney 0.9.0: D-Bus method calls — pure Python, zero C dependencies, works in a venv without system packages
- systemd unit file: process supervision — correct Pi OS pattern for long-lived services, handles boot and restart

**Supporting tools:**
- `mosquitto_pub` / `mosquitto_sub`: manual testing of MQTT traffic without the frontend
- `dbus-send` / `busctl`: verify D-Bus interface exists and is accessible before writing code
- `journalctl -u airplay-bridge -f`: read service logs

### Expected Features

All six commands the frontend already publishes (`playpause`, `nextitem`, `previtem`, `mutetoggle`, `volumeup`, `volumedown`) map to documented D-Bus methods at LOW complexity. The MVP is achievable in a single file. Every table-stakes feature is LOW complexity and LOW risk.

**Must have (table stakes):**
- Play/pause toggle — maps to `RemoteControl.PlayPause`
- Next track — maps to `RemoteControl.Next`
- Previous track — maps to `RemoteControl.Previous`
- Volume up / down — maps to `RemoteControl.VolumeUp` / `VolumeDown`
- Mute toggle — maps to `RemoteControl.ToggleMute`
- D-Bus error handling (no crash on unavailability) — wrap calls in try/except, log and continue
- systemd service with boot start — standard Pi OS pattern
- Logging to journald via stdout — zero-config with systemd

**Should have (reliability improvements for v1.x):**
- MQTT auto-reconnect — paho built-in, configure `reconnect_on_failure=True`
- Configurable MQTT topic via environment variable — needed for debugging and multi-instance
- Startup connectivity check with clear log output — reduces first-debug confusion
- MQTT Last Will and Testament — bridge health visibility

**Defer (v2+):**
- Multi-room / multi-instance support — explicitly out of scope
- Absolute volume control via `SetVolume` — fragile device support, defer until upstream improves
- HTTP REST API — not needed while MQTT is the IPC layer
- Command queueing / retry — stateful commands are time-sensitive; retry causes incorrect playback changes

### Architecture Approach

The bridge is a single Python process with two event sources: paho-mqtt's background thread (via `loop_start()`) receives MQTT messages and calls into a command map; D-Bus calls are made synchronously from the `on_message` callback via jeepney's blocking connection. No GLib main loop is required with jeepney (unlike pydbus/dasbus), making the event loop straightforwardly `client.loop_forever()`. The full project structure is three files: `bridge.py`, `bridge.service`, `requirements.txt`.

**Major components:**
1. `nowplaying.html` (existing) — publishes command strings to `shairport-sync/remote` over WebSocket to Mosquitto
2. `Mosquitto` (existing) — routes MQTT messages; bridge connects to `localhost:1883` (not WebSocket port 9001)
3. `bridge.py` (new) — subscribes to `shairport-sync/remote`; maps payload strings to D-Bus method calls on `org.gnome.ShairportSync`
4. `Shairport-Sync` (existing, requires D-Bus compile flag) — exposes `org.gnome.ShairportSync` on the system bus

**Critical D-Bus details:**
- Service name: `org.gnome.ShairportSync`; object path: `/org/gnome/ShairportSync`
- RemoteControl interface: `org.gnome.ShairportSync.RemoteControl`
- System bus default; requires D-Bus policy file granting the bridge user `send_destination` access
- Shairport-Sync must be compiled `--with-dbus-interface` — apt packages frequently omit this

### Critical Pitfalls

1. **AirPlay 2 / iOS 17.4+ silent command drop** — D-Bus calls complete without error but the Apple device ignores them because DACP-ID is absent from modern AirPlay 2 sessions. Confirmed permanent by Shairport-Sync maintainer (issue #1822, closed "not planned"). Verify with `dbus-send` on the actual target device before writing any bridge code. Only workaround: compile Shairport-Sync `--without-airplay2`.

2. **D-Bus interface not compiled in** — `apt install shairport-sync` frequently ships without `--with-dbus-interface`. `org.gnome.ShairportSync` simply will not appear on the bus. Verify with `busctl list | grep shairport` on day one; compile from source if missing.

3. **D-Bus policy access denied** — The system bus requires a policy file granting the bridge's Linux user `send_destination` access to `org.gnome.ShairportSync`. Without it, every D-Bus call returns `AccessDenied`. Install `shairport-sync-dbus-policy.conf` and add the bridge user. Alternative: switch to session bus (`dbus_service_bus = "session"` in `shairport-sync.conf`) to avoid policy file entirely.

4. **Commands silently dropped outside active AirPlay session** — `RemoteControl` methods are no-ops when no client is streaming (no DACP target). Bridge must not crash; log and discard is the correct response. Do not rely on D-Bus returning an error to detect this state.

5. **MQTT topic mismatch** — A single character difference between what the frontend publishes and what the bridge subscribes to causes silent delivery failure with no error anywhere. Verify with `mosquitto_sub -t 'shairport-sync/#' -v` before integration testing.

## Implications for Roadmap

Based on research, the natural phase structure follows the pitfall-to-phase mapping: environment must be verified before code is written, because the two critical blockers (D-Bus interface absent, AirPlay 2 DACP broken) would invalidate all bridge work if discovered late.

### Phase 1: Environment Verification
**Rationale:** Two showstopper blockers (D-Bus interface not compiled in, AirPlay 2 remote control broken) can only be discovered by testing against the real hardware before writing code. Discovering either blocker after building the bridge wastes all implementation effort.
**Delivers:** Confirmed working D-Bus interface accessible by the bridge user; confirmed play/pause response on the target iPhone; confirmed MQTT message flow from frontend through Mosquitto.
**Addresses pitfalls:** Pitfalls 1, 2, 3 (AirPlay 2 DACP, missing D-Bus compile flag, D-Bus policy access denied)
**Exit criteria:** `dbus-send` PlayPause from the `pi` user causes the iPhone to pause; `busctl list` shows `org.gnome.ShairportSync`; `mosquitto_sub` shows frontend button presses arriving on the correct topic.

### Phase 2: Bridge Implementation (MVP)
**Rationale:** With environment confirmed, implement the core service. All six command mappings are LOW complexity. Build the minimal file that makes touchscreen buttons work end-to-end.
**Delivers:** `bridge.py` — subscribes to `shairport-sync/remote`, maps all six commands to D-Bus methods, handles D-Bus errors without crashing, logs to stdout.
**Addresses pitfalls:** Pitfalls 4, 5 (session-idle graceful handling, MQTT topic alignment)
**Uses:** paho-mqtt 2.1.0 with `CallbackAPIVersion.VERSION2`, jeepney 0.9.0, `loop_forever()` pattern
**Features:** All P1 table-stakes features from FEATURES.md

### Phase 3: Systemd Service Deployment
**Rationale:** Once the bridge code works interactively, package it for production. Systemd supervision, boot start, and restart-on-failure transform a script into a reliable service.
**Delivers:** `bridge.service` unit file; venv at `/opt/airplay-bridge/`; service enabled and confirmed surviving reboot and Mosquitto/Shairport-Sync restarts.
**Addresses pitfalls:** Service start-order race, bridge dying silently, bridge not recovering from dependency restarts
**Key configuration:** `After=network.target mosquitto.service`, `Requires=mosquitto.service`, `Restart=on-failure`, `RestartSec=5`, `User=pi`

### Phase 4: Reliability Hardening (v1.x)
**Rationale:** After the happy path is confirmed in production, add the robustness features that matter for day-to-day kiosk operation. These are all LOW complexity but should not block the initial deployment.
**Delivers:** MQTT auto-reconnect configuration; configurable topic via environment variable; startup connectivity check with clear log output; MQTT Last Will and Testament.
**Features:** All P2 features from FEATURES.md's "Add After Validation" list.

### Phase Ordering Rationale

- Phase 1 before all others: the AirPlay 2 DACP issue can only be detected on real hardware. If play/pause does not work via `dbus-send`, the project's entire premise needs reassessment before a line of bridge code is written.
- Phase 2 before Phase 3: confirms the logic works interactively before adding systemd complexity that can obscure Python errors.
- Phase 3 before Phase 4: reliability hardening only makes sense after the service is running in its final deployment environment.
- All six MQTT-to-D-Bus command mappings belong in Phase 2 together — they are identical in structure and share the same risks; splitting them across phases adds no value.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** AirPlay 2 DACP status on the specific device/OS version in use — research confirmed the breakage is real but device-specific testing is required. If commands do not work, research the `--without-airplay2` compile path.
- **Phase 1:** Shairport-Sync compile from source — if the installed binary lacks `--with-dbus-interface`, source compilation instructions and dependencies need to be researched for the specific Pi OS version.

Phases with standard patterns (skip research-phase):
- **Phase 2:** Well-documented. The jeepney connection pattern, paho callback pattern, and command map are all verified and specific code examples exist in STACK.md and ARCHITECTURE.md.
- **Phase 3:** Standard systemd service deployment. The exact unit file content is documented in STACK.md.
- **Phase 4:** All reliability features use paho built-in mechanisms; no novel integration required.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Core choices verified against official PyPI pages, official Raspberry Pi OS documentation, and Shairport-Sync official repo. jeepney pattern confirmed with working code example. |
| Features | HIGH (core) / MEDIUM (AirPlay 2 reliability) | The six command mappings are definitively documented in the official Shairport-Sync repo. AirPlay 2 DACP breakage is confirmed by maintainer but device-specific behaviour (exactly which iOS/macOS versions are affected) is MEDIUM confidence. |
| Architecture | HIGH | Single-file service pattern confirmed by multiple independent community implementations. Data flow verified against official docs. Anti-patterns confirmed with official issue references. |
| Pitfalls | HIGH | All five critical pitfalls traced to official Shairport-Sync GitHub issues, closed by maintainers, with confirmed status. |

**Overall confidence:** HIGH

### Gaps to Address

- **AirPlay 2 device-specific behaviour:** Research confirms DACP is broken on iOS 17.4+ and macOS 14.4+, but the exact scope depends on the project owner's actual streaming device. This must be tested in Phase 1 before any further work. If it fails, the project needs to decide whether to compile without AirPlay 2 support or document the limitation and ship volume-only control.
- **Shairport-Sync compile flags on the existing Pi install:** Research cannot determine from documentation alone whether the installed Shairport-Sync binary was compiled with `--with-dbus-interface`. This must be verified with `busctl list` in Phase 1.
- **D-Bus session bus vs system bus choice:** Default is system bus but session bus avoids policy file complexity. If Phase 1 reveals D-Bus policy issues, switching to session bus is a valid trade-off. This decision should be made during Phase 1 based on what the Pi's actual configuration shows.

## Sources

### Primary (HIGH confidence)
- https://github.com/mikebrady/shairport-sync/blob/master/documents/sample%20dbus%20commands — D-Bus service name, object path, interface, method list
- https://github.com/mikebrady/shairport-sync/blob/master/MQTT.md — MQTT topic structure, `enable_remote` default off
- https://github.com/mikebrady/shairport-sync/issues/1822 — AirPlay 2 / DACP breakage, iOS 17.4+, closed "not planned"
- https://github.com/mikebrady/shairport-sync/issues/1858 — MQTT Remote Control does nothing on Apple Music iOS
- https://github.com/mikebrady/shairport-sync/issues/223 — canonical resolution: use D-Bus directly
- https://pypi.org/project/paho-mqtt/ — version 2.1.0, CallbackAPIVersion breaking change
- https://pypi.org/project/jeepney/ — version 0.9.0, pure Python, actively maintained
- https://pypi.org/project/dbus-python/ — version 1.4.0, status "Inactive" confirmed
- https://www.raspberrypi.com/news/bookworm-the-new-version-of-raspberry-pi-os/ — Python 3.11 default, venv requirement on Bookworm

### Secondary (MEDIUM confidence)
- https://github.com/pimoroni/pirate-audio/blob/master/examples/shairport-sync-control.py — working Python D-Bus control example for Shairport-Sync
- https://github.com/mikebrady/shairport-sync/discussions/1862 — system vs session bus behaviour, permission requirements
- https://github.com/parautenbach/hass-shairport-sync — confirms MQTT→D-Bus pattern is viable
- https://github.com/idcrook/shairport-sync-mqtt-display — prior art: Python + paho + D-Bus control
- https://jwnmulder.github.io/dbus2mqtt/examples/home_assistant_media_player/ — dbus2mqtt media player pattern
- https://github.com/victronenergy/dbus-mqtt — reference MQTT↔D-Bus bridge architecture

### Tertiary (LOW confidence — needs validation on device)
- AirPlay 2 DACP behaviour on specific iOS/macOS versions — confirmed broken in general, device-specific results require testing

---
*Research completed: 2026-03-29*
*Ready for roadmap: yes*
