# Pitfalls Research

**Domain:** MQTT-to-D-Bus bridge for Shairport-Sync AirPlay control (Raspberry Pi)
**Researched:** 2026-03-29
**Confidence:** HIGH (critical pitfalls verified against official Shairport-Sync GitHub issues and docs)

---

## Critical Pitfalls

### Pitfall 1: Remote Commands Are Silently Ignored on AirPlay 2 / iOS 17.4+

**What goes wrong:**
Play, pause, next, previous, and volume commands sent via D-Bus (or MQTT remote) appear to be accepted with no error — but the Apple source device silently ignores them. No exception is thrown, no error is logged, the D-Bus call "succeeds," yet nothing happens on the streaming device.

**Why it happens:**
Shairport-Sync's remote control mechanism depends on DACP (Digital Audio Control Protocol). The AirPlay session must provide an `Active-Remote` ID and `DACP-ID` during the RTSP handshake — Shairport-Sync uses these to send back control commands to the originating Apple device. Since iOS 17.4 and macOS 14.4, Apple stopped transmitting these parameters in AirPlay 2 sessions. Without them, Shairport-Sync cannot construct a valid DACP request, so commands are dropped. The Shairport-Sync maintainer confirmed: "no fix has been found -- it seems to be a permanent change at Apple's end." (Issue #1822, closed as "not planned".)

**How to avoid:**
- Verify this is not an issue on your specific client during the very first phase. Connect via AirPlay, start playback, and test `dbus-send` commands manually from the Pi shell before writing any bridge code.
- If AirPlay 2 is in use, test whether disabling AirPlay 2 at build time (compile shairport-sync without AirPlay 2 support) restores DACP functionality — this is the only confirmed workaround.
- Treat "D-Bus call returns no error" as insufficient proof of success. Verify the source device actually responded.

**Warning signs:**
- `dbus-send` commands complete without error but playback on the iPhone/Mac does not change.
- Shairport-Sync logs show no outbound DACP request after a remote control command.
- Commands work from a macOS client on older OS versions but not iOS.

**Phase to address:** Foundation / Day 1 — verify manually with `dbus-send` before writing any bridge code.

---

### Pitfall 2: D-Bus Interface Absent Because Shairport-Sync Was Not Compiled with It

**What goes wrong:**
Bridge code calls D-Bus methods on `org.gnome.ShairportSync` or `org.mpris.MediaPlayer2.ShairportSync` and receives "service unknown" or "destination not found." The interface does not exist on the bus.

**Why it happens:**
D-Bus support in Shairport-Sync is not compiled in by default. Both the native D-Bus interface (`--with-dbus-interface`) and the MPRIS interface (`--with-mpris-interface`) are optional compile-time flags. Distribution packages (e.g., Raspbian `apt install shairport-sync`) frequently ship without these flags enabled, so `org.gnome.ShairportSync` simply never appears on the system bus.

**How to avoid:**
- Before any bridge work, run `busctl list | grep -i shairport` (or `dbus-send --system --print-reply --dest=org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus.ListNames`) to confirm the D-Bus names are actually registered.
- If missing, you must compile Shairport-Sync from source with `--with-dbus-interface` and/or `--with-mpris-interface`.
- Document the exact compile flags used in the project so the setup is reproducible.

**Warning signs:**
- `dbus-send` returns "org.freedesktop.DBus.Error.ServiceUnknown" immediately.
- `busctl list` shows no `org.gnome.ShairportSync` or `org.mpris.MediaPlayer2.ShairportSync` entry.

**Phase to address:** Foundation / environment verification step before bridge implementation begins.

---

### Pitfall 3: D-Bus Policy Not Installed — Bridge User Denied Access to System Bus

**What goes wrong:**
The bridge service starts but receives `org.freedesktop.DBus.Error.AccessDenied` when attempting to call methods on `org.gnome.ShairportSync`. Alternatively, Shairport-Sync itself fails to register on the system bus with "Could not acquire an MPRIS interface."

**Why it happens:**
The D-Bus system bus enforces policy files in `/etc/dbus-1/system.d/`. Shairport-Sync's `make install` deploys `shairport-sync-dbus-policy.conf` to that directory — but this step is often skipped when installing from a package manager or when the installed binary was not compiled with D-Bus support. Without the policy file, no unprivileged process (including a bridge service running as a non-root user) can own or call the Shairport-Sync D-Bus names.

Additionally, if the bridge service runs under a different Linux user than `shairport-sync`, that user must have an explicit `<allow>` entry in the policy file.

**How to avoid:**
- Confirm `/etc/dbus-1/system.d/shairport-sync-dbus-policy.conf` exists after installation. If absent, copy from the Shairport-Sync source at `scripts/shairport-sync-dbus-policy.conf`.
- After adding or modifying the policy file, run `systemctl daemon-reload && systemctl restart shairport-sync` — D-Bus does not hot-reload policies for active services.
- The bridge service user must match the user granted access in the policy file, or run as the `shairport-sync` user.
- Alternative with zero security setup: configure Shairport-Sync to use the D-Bus **session bus** (`dbus_service_bus = "session"` in `shairport-sync.conf`) instead of the system bus — no policy file required.

**Warning signs:**
- `dbus-send` returns `org.freedesktop.DBus.Error.AccessDenied`.
- Shairport-Sync journal shows "Could not acquire... interface... on the system bus."
- `ls /etc/dbus-1/system.d/` does not contain a shairport-sync entry.

**Phase to address:** Foundation — environment configuration and verification, before bridge implementation.

---

### Pitfall 4: Remote Control Only Works During an Active AirPlay Session

**What goes wrong:**
Play/pause/next commands sent by the bridge when no AirPlay source is streaming are silently dropped. The bridge sends the command, D-Bus returns success, but nothing happens — because there is no connected player to receive the DACP command.

**Why it happens:**
Shairport-Sync's remote control mechanism is stateful: the `Active-Remote` ID and `DACP-ID` are only populated when a client is actively streaming. Outside of an active session, Shairport-Sync has no target to forward the command to, so the command is a no-op. The native D-Bus interface exposes a `RemoteControl` property that indicates whether the remote control connection is viable — this is the correct way to gate command dispatch.

**How to avoid:**
- The bridge must track session state by subscribing to Shairport-Sync's MQTT metadata topics (specifically `shairport-sync/play_state` or equivalent) and only dispatch control commands when a session is active.
- Use the native D-Bus interface's `RemoteControl` viability property as a pre-flight check before sending commands.
- Design the UI to reflect "no active session" state so users do not press buttons that will be silently ignored.

**Warning signs:**
- Control buttons "work" during an active stream but fail completely at idle.
- No DACP traffic appears in Shairport-Sync debug logs when commands are sent at idle.

**Phase to address:** Bridge implementation — session state management must be built in from the start, not retrofitted.

---

### Pitfall 5: MQTT `enable_remote` Is Disabled by Default — Commands Never Reach Shairport-Sync

**What goes wrong:**
The frontend publishes commands to `shairport-sync/remote` (as it already does in this project). Mosquitto delivers the message. Nothing happens. No error anywhere in the chain.

**Why it happens:**
This project's bridge bypasses Shairport-Sync's own MQTT remote control path (which is a separate feature where shairport-sync itself subscribes to MQTT). However, it is worth noting: if anyone attempts to use Shairport-Sync's built-in MQTT remote, `enable_remote = "yes"` must be explicitly set in `shairport-sync.conf` — it defaults to `"no"` and the setting is commented out. The bridge approach in this project routes around this, but the `enable_remote` requirement surfaces in documentation examples and confuses debugging.

More critically for this project: the bridge must subscribe to the correct topic. If the frontend is publishing to `shairport-sync/remote` and the bridge subscribes to a slightly different topic (wrong prefix, trailing slash, case mismatch), the bridge receives nothing and MQTT delivers no error.

**How to avoid:**
- In the bridge, log every received MQTT message at startup to confirm the subscription is matching.
- Use `mosquitto_sub -t 'shairport-sync/#' -v` on the Pi to observe all traffic in the namespace and confirm the frontend's publish is reaching the broker on the expected topic.
- Do not rely on Shairport-Sync's built-in `enable_remote` feature — the bridge approach is the correct architecture for this project. Understand the two paths are separate.

**Warning signs:**
- Bridge service starts, no errors, but no messages are ever processed.
- `mosquitto_sub` on `shairport-sync/#` shows no traffic when the frontend button is pressed.

**Phase to address:** Bridge implementation — topic alignment between frontend and bridge must be verified on day one.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcode D-Bus service name as `org.gnome.ShairportSync` | No config needed | Breaks if Shairport-Sync renames or if MPRIS path is used instead | Acceptable for single-Pi deploy; document explicitly |
| Run bridge as root to avoid D-Bus policy setup | No policy file needed | Security risk; service failure takes down more than necessary | Never — configure the policy file instead |
| Skip session-state checks, always send D-Bus commands | Simpler code | Silent failures when no AirPlay session is active | Never — silent failures erode trust in the UI |
| Use `loop_forever()` without reconnect handling for MQTT | Simple implementation | Bridge stops working silently if Mosquitto restarts | Acceptable in MVP; add reconnect in next iteration |
| Inline all config (broker host, topic, D-Bus names) | Fast to write | Hard to adapt across Pis or test environments | MVP only; extract to config file before "done" |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Shairport-Sync D-Bus | Calling `Next`/`Previous` as MPRIS Player methods expecting them to work on iOS | Verify DACP availability first; test AirPlay 1 vs AirPlay 2 behaviour separately |
| Shairport-Sync D-Bus | Using `dbus-python` (legacy, GLib-based) and fighting the GLib main loop | Use `dasbus` or `pydbus` with GLib main loop; or `dbus-next` for asyncio |
| Shairport-Sync D-Bus | Connecting to session bus when Shairport-Sync is on system bus (or vice versa) | Match the bus configured in `shairport-sync.conf`; default is system bus |
| Mosquitto MQTT | Connecting with a static `client_id`; second instance of the bridge boots the first | Use a unique or random client_id per instance |
| Mosquitto MQTT | Subscribing with QoS 0 and assuming reliable delivery on a flaky local network | QoS 1 for command topics on a Pi; broker and client are both local so overhead is negligible |
| systemd service | `After=mosquitto.service` without `Requires=` means the bridge starts even if Mosquitto failed | Use both `After=mosquitto.service` and `Requires=mosquitto.service` |
| systemd service | Not setting `Restart=on-failure` — bridge dies silently on uncaught exception | Always set `Restart=on-failure` with `RestartSec=5` for a resilient service |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Polling D-Bus for playback state instead of subscribing to signals | High CPU on a Pi Zero; lag in state updates | Subscribe to MQTT metadata topics that Shairport-Sync already publishes; do not poll D-Bus | Immediately on low-power Pi hardware |
| No debounce on touchscreen button presses | Rapid-fire D-Bus calls for a single press; potential command duplication | Debounce in frontend JS (already the right layer) and/or rate-limit in the bridge | At any scale — touchscreens produce multiple events per tap |
| Blocking D-Bus calls in the MQTT message callback | Bridge blocks MQTT processing while waiting for D-Bus response | Use async D-Bus call or issue the D-Bus call in a thread/task separate from the MQTT callback | Immediately if D-Bus call hangs |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Running bridge as root to avoid D-Bus policy work | Root process can write to entire filesystem; compromised bridge is full Pi compromise | Create a dedicated system user; add that user to the D-Bus policy file |
| Anonymous MQTT access without topic ACLs (existing setup) | Any device on the LAN can publish fake commands to `shairport-sync/remote` | Acceptable on a trusted home LAN; document this assumption explicitly |
| Exposing MQTT broker port 9001 (WebSocket) on all interfaces | External access to control AirPlay playback | Bind Mosquitto WebSocket listener to `127.0.0.1` if the frontend is served locally; acceptable risk on a home LAN |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No feedback when a command is dispatched but silently ignored (iOS AirPlay 2 issue) | User presses button, nothing happens, presses again — frustration | Show a brief "sent" state on the button; longer-term, explore whether the command was acknowledged |
| Control buttons enabled when no AirPlay session is active | User taps next/prev at idle clock screen; nothing happens | Disable/hide control buttons when `play_state` MQTT topic indicates idle |
| Volume commands sent as relative steps (`volumeup`, `volumedown`) with no visual confirmation | User cannot tell if volume changed | Rely on the existing volume display already fed by Shairport-Sync MQTT metadata |

---

## "Looks Done But Isn't" Checklist

- [ ] **D-Bus interface present:** Confirm `busctl list | grep shairport` shows the expected service name — not just that the bridge code runs without error.
- [ ] **Commands acknowledged by source device:** Test with an iPhone streaming; verify playback actually pauses/advances — not just that `dbus-send` exits cleanly.
- [ ] **Bridge survives Mosquitto restart:** Kill and restart Mosquitto; confirm bridge reconnects automatically within a few seconds.
- [ ] **Bridge survives Shairport-Sync restart:** Shairport-Sync D-Bus name disappears and reappears; bridge must not crash.
- [ ] **Session-idle state handled:** Press play/pause when nothing is streaming; verify bridge does not crash and does not log errors continuously.
- [ ] **Service starts on boot:** Reboot the Pi; confirm bridge is active without manual intervention.
- [ ] **iOS 17.4+ tested specifically:** If the project owner uses a recent iPhone, test on that device — not just macOS or an older iOS.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Commands ignored on iOS (AirPlay 2 DACP missing) | HIGH | Compile Shairport-Sync without AirPlay 2 support (`--without-airplay2`); re-test; document as known limitation |
| D-Bus interface absent (not compiled in) | MEDIUM | Compile Shairport-Sync from source with `--with-dbus-interface`; re-install; reload D-Bus policy |
| D-Bus access denied | LOW | Install/fix `/etc/dbus-1/system.d/shairport-sync-dbus-policy.conf`; `systemctl daemon-reload && systemctl restart shairport-sync` |
| MQTT topic mismatch | LOW | Add MQTT message logging to bridge; align topic strings between frontend and bridge |
| Bridge dies silently | LOW | Add `Restart=on-failure` to systemd unit; review Python exception handling |
| Bridge and Mosquitto start-order race | LOW | Add `After=mosquitto.service Requires=mosquitto.service` to bridge systemd unit; add retry loop on initial MQTT connect |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| AirPlay 2 remote control silently dropped (iOS 17.4+) | Phase 1: Environment verification | Manually `dbus-send` a play/pause while streaming from target iPhone; confirm it works before writing code |
| D-Bus interface not compiled in | Phase 1: Environment verification | `busctl list \| grep shairport` returns the expected names |
| D-Bus policy / access denied | Phase 1: Environment verification | Bridge user can call D-Bus methods without sudo |
| Commands sent when no session active | Phase 2: Bridge implementation | Integration test: send command at idle, confirm no crash, no spurious error loop |
| MQTT topic mismatch | Phase 2: Bridge implementation | `mosquitto_sub -t 'shairport-sync/#' -v` shows bridge receiving messages when frontend button pressed |
| `enable_remote` confusion | Phase 2: Bridge implementation | Bridge architecture review — confirm bridge subscribes directly, not relying on Shairport-Sync's own MQTT remote |
| Service start order race | Phase 3: Systemd service deployment | Reboot Pi; confirm service is active within 30 seconds; Mosquitto restart test |
| Bridge not surviving restarts | Phase 3: Systemd service deployment | Kill Mosquitto; kill Shairport-Sync; confirm bridge recovers both without manual intervention |

---

## Sources

- [Shairport-Sync Issue #1822: D-Bus commands ignored on iOS 17.4 / macOS 14.4](https://github.com/mikebrady/shairport-sync/issues/1822) — confirmed as permanent Apple-side change, closed "not planned"
- [Shairport-Sync Issue #1858: MQTT Remote Control does nothing](https://github.com/mikebrady/shairport-sync/issues/1858) — Apple Music iOS no longer responds to DACP
- [Shairport-Sync Issue #1099: Could not acquire MPRIS interface on read-only Raspberry OS](https://github.com/mikebrady/shairport-sync/issues/1099) — D-Bus policy file not deployed
- [Shairport-Sync Issue #730: Problem with D-Bus interface (Resolved)](https://github.com/mikebrady/shairport-sync/issues/730) — user permissions in policy file
- [Shairport-Sync Discussion #1862: How to run shairport with dbus support](https://github.com/mikebrady/shairport-sync/discussions/1862) — system bus vs session bus, policy file requirements
- [Shairport-Sync Discussion #1606: Volume commands via MQTT not working in Docker](https://github.com/mikebrady/shairport-sync/discussions/1606) — DACP response required from player
- [Shairport-Sync sample D-Bus commands document](https://github.com/mikebrady/shairport-sync/blob/master/documents/sample%20dbus%20commands) — canonical bus names, object paths, interface names
- [Shairport-Sync MQTT.md](https://github.com/mikebrady/shairport-sync/blob/master/MQTT.md) — `enable_remote` default off; topic structure
- [dasbus on PyPI](https://pypi.org/project/dasbus/) — recommended Python D-Bus library (pydbus replacement)
- [pydbus Issue #57: asyncio support](https://github.com/LEW21/pydbus/issues/57) — GLib main loop conflict with asyncio
- [paho-mqtt reconnection patterns — Steve's Internet Guide](http://www.steves-internet-guide.com/loop-python-mqtt-client/) — `loop_forever()` and reconnect behaviour
- [Mosquitto systemd ordering](https://github.com/eclipse-mosquitto/mosquitto/pull/1617) — `After=network.target` vs `After=network-online.target`

---
*Pitfalls research for: MQTT-to-D-Bus bridge, Shairport-Sync, Raspberry Pi*
*Researched: 2026-03-29*
