# Feature Research

**Domain:** MQTT-to-D-Bus bridge for AirPlay/Shairport-Sync playback control
**Researched:** 2026-03-29
**Confidence:** MEDIUM — Core protocol facts are HIGH confidence from official source code; Apple-side command reliability is MEDIUM due to documented regression with iOS 17.4+ / AirPlay 2.

---

## Context: What This Service Does

The frontend (`nowplaying.html`) publishes command payloads to the MQTT topic
`shairport-sync/remote`. The payloads it sends are: `playpause`, `nextitem`,
`previtem`, `mutetoggle`, `volumeup`, `volumedown`.

Shairport-Sync exposes a D-Bus interface (`org.gnome.ShairportSync.RemoteControl`
on the system bus) with corresponding methods. The bridge is the process sitting
between: subscribe to that MQTT topic, call the D-Bus method.

**Critical constraint:** Shairport-Sync's own built-in MQTT remote control
(`enable_remote = "yes"` in its config) is documented as broken since iOS 17.4 /
macOS 14.4 because Apple no longer sends DACP-ID in AirPlay 2 sessions (GitHub
issue #1858, closed "not planned"). The D-Bus path is the authoritative alternative.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features the bridge must have for the touchscreen to feel functional at all.
Missing any of these means buttons are silently broken.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Play/pause toggle | Core button already renders and publishes `playpause` | LOW | Maps to `org.gnome.ShairportSync.RemoteControl.PlayPause` |
| Next track | Core button already renders and publishes `nextitem` | LOW | Maps to `RemoteControl.Next` |
| Previous track | Core button already renders and publishes `previtem` | LOW | Maps to `RemoteControl.Previous` |
| Volume up / down | Volume buttons already publish `volumeup` / `volumedown` | LOW | Maps to `RemoteControl.VolumeUp` / `RemoteControl.VolumeDown` |
| Mute toggle | Mute button already publishes `mutetoggle` | LOW | Maps to `RemoteControl.ToggleMute` |
| MQTT subscribe on startup | Service must connect to Mosquitto and subscribe before any buttons are pressed | LOW | Subscribe to `shairport-sync/remote`; Mosquitto is on localhost |
| Survive Shairport-Sync not playing | D-Bus calls when no session is active should not crash the service | LOW | D-Bus call will return an error; log and discard |
| Run as a background service | Must start at boot and stay running without a TTY | LOW | systemd unit file |
| Logging | Operator must be able to see what commands were received and whether D-Bus calls succeeded | LOW | Write to stdout / journald; systemd captures automatically |

### Differentiators (Competitive Advantage)

Features not strictly required for v1 but that meaningfully improve reliability or
debuggability for a self-hosted Pi setup.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| MQTT auto-reconnect | Mosquitto restarts are common on Pi; service should reconnect without manual intervention | LOW | paho-mqtt has built-in reconnect; configure `reconnect_on_failure=True` |
| D-Bus unavailability handling | Shairport-Sync may not be running; service should log the error and continue rather than crash | LOW | Wrap every D-Bus call in try/except; retry is not needed (next button press will try again) |
| Configurable MQTT topic prefix | Allows the bridge to work with multi-room setups or non-default Shairport-Sync topic names without a code change | LOW | Read `MQTT_TOPIC` from environment variable or config file, default `shairport-sync` |
| Configurable D-Bus bus type | Shairport-Sync defaults to system bus but can be compiled for session bus; should be settable | LOW | `DBUS_BUS=system` env var |
| Startup connectivity check | Log a clear warning at boot if Mosquitto or D-Bus is unreachable, rather than silently failing | LOW | Try to connect/introspect at startup; log result |
| MQTT Last Will and Testament | Publishes an offline status message when the bridge crashes, so a monitoring UI can detect it | LOW | Set LWT in the MQTT connect call |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Using Shairport-Sync's built-in MQTT remote (`enable_remote = "yes"`) | Seems like the obvious path — Shairport-Sync already supports it | Broken since iOS 17.4 / macOS 14.4: Apple removed DACP-ID from AirPlay 2 packets; commands are accepted by Mosquitto but silently ignored by the AirPlay sender. Closed "not planned" upstream (issue #1858). | Use D-Bus directly — this is the explicit resolution in issue #223 and the approach documented in `documents/sample dbus commands` |
| Volume set by absolute value (e.g. publish `volume:0.75`) | Touchscreen has a drag-to-set volume bar | Shairport-Sync's `AdvancedRemoteControl.SetVolume` has limited device support; AirPlay volume range is -30 to 0 dB (not 0–1), and the MPRIS `SetVolume` method is also noted as having limited support. Mapping is fragile. | Use `VolumeUp` / `VolumeDown` step commands, which are well-supported. Frontend already does this with a click handler. |
| Bidirectional state sync (bridge publishes current playback state back to MQTT) | Seems useful to close the loop | Shairport-Sync already publishes metadata and state to MQTT topics (`shairport-sync/playing`, `shairport-sync/volume`, etc.) — the frontend subscribes to those directly. The bridge duplicating that creates a second publisher on the same topics, risking confusion and message loops. | The bridge is command-only; state flows through Shairport-Sync's own MQTT publisher |
| Multi-room / multi-instance support | Pi setups sometimes grow | Adds complexity (routing by instance name, multiple D-Bus service names) before the single-instance case is validated | Defer entirely; the project explicitly calls this out-of-scope |
| HTTP REST API for commands | Useful for future integrations | Adds a web server dependency, another port, another process to keep alive | Not needed; MQTT is already the agreed IPC layer |
| Command queueing / retry | Commands that fail should be retried | Commands are stateful and time-sensitive (pause, next); retrying a stale command after Shairport-Sync recovers causes unexpected playback changes | Log the failure; rely on the user pressing the button again |

---

## Feature Dependencies

```
[MQTT subscribe on startup]
    └──required by──> [Play/pause toggle]
    └──required by──> [Next track]
    └──required by──> [Previous track]
    └──required by──> [Volume up/down]
    └──required by──> [Mute toggle]

[Run as background service (systemd)]
    └──required by──> [Survive Shairport-Sync not playing]
    └──enhanced by──> [MQTT auto-reconnect]
    └──enhanced by──> [Startup connectivity check]

[MQTT auto-reconnect]
    └──enhances──> [Run as background service]

[Configurable MQTT topic prefix]
    └──enhances──> [MQTT subscribe on startup]

[D-Bus unavailability handling]
    └──enhances──> [Survive Shairport-Sync not playing]
```

### Dependency Notes

- All playback commands require MQTT subscription to be established first; that is the single gate.
- systemd service management enables the auto-reconnect and error handling features to be meaningful (a crashed bridge that restarts in 5 seconds is fine; a bridge that exits silently is not).
- Configurable topic prefix must be resolved before MQTT subscribe fires — it is a startup concern, not a runtime one.

---

## MVP Definition

### Launch With (v1)

Minimum viable product: touchscreen buttons work.

- [ ] Subscribe to `shairport-sync/remote` on localhost Mosquitto
- [ ] Map the six command payloads (`playpause`, `nextitem`, `previtem`, `mutetoggle`, `volumeup`, `volumedown`) to the corresponding D-Bus methods on `org.gnome.ShairportSync.RemoteControl`
- [ ] Log each received command and the D-Bus call result to stdout
- [ ] Handle D-Bus errors gracefully (log and continue; do not crash)
- [ ] systemd unit file so the service starts at boot

### Add After Validation (v1.x)

Add once the happy path is confirmed working.

- [ ] MQTT auto-reconnect with configurable retry interval — trigger: Mosquitto restart causes bridge to go silent
- [ ] Configurable MQTT topic via environment variable — trigger: needing to run a second instance or rename the topic
- [ ] Startup connectivity check with clear log output — trigger: first time debugging why buttons do nothing
- [ ] MQTT Last Will and Testament — trigger: wanting to monitor bridge health

### Future Consideration (v2+)

Deliberately deferred.

- [ ] Multi-room support — explicitly out of scope per PROJECT.md
- [ ] Non-AirPlay sources — explicitly out of scope
- [ ] Absolute volume control — fragile; hold until upstream `SetVolume` support improves
- [ ] HTTP API — not needed while MQTT is the IPC layer

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Play/pause toggle | HIGH | LOW | P1 |
| Next / Previous track | HIGH | LOW | P1 |
| Volume up / down | HIGH | LOW | P1 |
| Mute toggle | MEDIUM | LOW | P1 |
| D-Bus error handling (no crash) | HIGH | LOW | P1 |
| systemd service + boot start | HIGH | LOW | P1 |
| Logging to journald | HIGH | LOW | P1 |
| MQTT auto-reconnect | MEDIUM | LOW | P2 |
| Configurable topic prefix | LOW | LOW | P2 |
| Startup connectivity check | MEDIUM | LOW | P2 |
| MQTT Last Will and Testament | LOW | LOW | P3 |
| Absolute volume set | LOW | HIGH | P3 (defer) |

---

## Competitor / Prior Art Analysis

There is no direct "off-the-shelf" MQTT-to-D-Bus bridge for Shairport-Sync; this is
consistently a DIY integration. The closest reference implementations:

| Approach | How It Works | Relevant Lesson |
|----------|-------------|-----------------|
| `idcrook/shairport-sync-mqtt-display` | Python Flask app subscribes to MQTT metadata and re-publishes to WebSocket; includes remote control | Remote control is an afterthought, not the core feature |
| `parautenbach/hass-shairport-sync` | Home Assistant custom component; wraps MQTT subscribe + D-Bus calls | Confirms the MQTT→D-Bus pattern is viable; HA overhead is unnecessary for this Pi |
| `victronenergy/dbus-mqtt` (archived) | Maps entire D-Bus on Venus OS to MQTT; bidirectional | Much larger scope; demonstrates that D-Bus bridging is a solved problem |
| `dbus2mqtt` (jwnmulder) | MPRIS wildcard subscription; publishes state to MQTT every 5s + on change | Confirms pydbus/dasbus approach; state-publishing direction is opposite to our need |
| Shairport-Sync built-in MQTT remote | `enable_remote = "yes"` — Shairport-Sync itself subscribes | **Do not use**: broken since iOS 17.4 for AirPlay 2, closed "not planned" upstream |

The consistent pattern across all viable implementations: Python + paho-mqtt +
pydbus (or dasbus), command-only direction, no command queuing.

---

## Sources

- [Shairport-Sync sample D-Bus commands](https://github.com/mikebrady/shairport-sync/blob/master/documents/sample%20dbus%20commands) — HIGH confidence (official)
- [Shairport-Sync MQTT.md](https://github.com/mikebrady/shairport-sync/blob/master/MQTT.md) — HIGH confidence (official)
- [Issue #1858: MQTT Remote Control does nothing](https://github.com/mikebrady/shairport-sync/issues/1858) — HIGH confidence (maintainer statement, closed "not planned")
- [Issue #1822: D-Bus commands ignored on iOS 17.4 / macOS 14.4](https://github.com/mikebrady/shairport-sync/issues/1822) — HIGH confidence (maintainer diagnosis, AirPlay 2 limitation)
- [Discussion #1555: Plans for AirPlay 2 Remote Control](https://github.com/mikebrady/shairport-sync/discussions/1555) — HIGH confidence (maintainer, no plans)
- [Issue #223: Resolved — Use the D-Bus Interface](https://github.com/mikebrady/shairport-sync/issues/223) — HIGH confidence (canonical resolution)
- [dbus2mqtt media player example](https://jwnmulder.github.io/dbus2mqtt/examples/home_assistant_media_player/) — MEDIUM confidence (community project)
- [parautenbach/hass-shairport-sync](https://github.com/parautenbach/hass-shairport-sync) — MEDIUM confidence (community project)
- [idcrook/shairport-sync-mqtt-display](https://github.com/idcrook/shairport-sync-mqtt-display) — MEDIUM confidence (community project)
- Frontend source (`nowplaying.html`) — HIGH confidence (primary source, confirmed exact payloads and topic)

---

*Feature research for: MQTT-to-D-Bus bridge for Shairport-Sync / AirPlay control*
*Researched: 2026-03-29*
