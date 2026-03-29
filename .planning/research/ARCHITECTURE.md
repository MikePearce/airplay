# Architecture Research

**Domain:** MQTT-to-D-Bus bridge service for Shairport-Sync playback control
**Researched:** 2026-03-29
**Confidence:** HIGH (primary sources: official Shairport-Sync repo, dbus-python docs, paho-mqtt docs)

---

## Critical Architectural Discovery

Before discussing architecture, a finding that fundamentally shapes the design:

**Shairport-Sync's built-in MQTT remote is broken for modern iOS/macOS.** The `enable_remote = "yes"` MQTT setting exists in Shairport-Sync, but it routes commands through DACP (Digital Audio Control Protocol) back to the AirPlay sender. Since iOS 17.4 and macOS 14.4, Apple stopped sending the required DACP ID in AirPlay 2 sessions, so these commands are silently ignored. This is documented in [issue #1822](https://github.com/mikebrady/shairport-sync/issues/1822) and confirmed unresolved as of mid-2024.

**The correct approach is a separate bridge service that translates MQTT commands into D-Bus calls on the local `org.gnome.ShairportSync` interface.** D-Bus volume control (`Volume` property) operates on the local ALSA mixer — it does not route back to the AirPlay sender — and therefore is not affected by the iOS/DACP breakage. Playback control methods (Play, Pause, Next, Previous) do still route to the sender via DACP and carry the same iOS 17.4+ risk, but volume control is fully local and reliable.

---

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Raspberry Pi                             │
│                                                                 │
│  ┌──────────────────┐         ┌──────────────────────────────┐  │
│  │   nowplaying.html│         │    Shairport-Sync            │  │
│  │  (browser/kiosk) │         │  (AirPlay receiver)          │  │
│  │                  │         │                              │  │
│  │  Publishes to:   │         │  D-Bus service:              │  │
│  │  shairport-sync/ │         │  org.gnome.ShairportSync     │  │
│  │  remote          │         │  (system bus)                │  │
│  └────────┬─────────┘         └──────────────┬───────────────┘  │
│           │ WebSocket (9001)                  │ D-Bus            │
│           ▼                                  │                  │
│  ┌──────────────────┐                        │                  │
│  │   Mosquitto      │         ┌──────────────┴───────────────┐  │
│  │  (MQTT broker)   │◄───────►│   bridge.py                  │  │
│  │  port 1883/9001  │  MQTT   │  (new service)               │  │
│  └──────────────────┘  sub    │                              │  │
│                               │  Subscribes: shairport-sync/ │  │
│                               │  remote                      │  │
│                               │  Calls: D-Bus methods        │  │
│                               └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| nowplaying.html | Publishes command strings to `shairport-sync/remote` topic on button press | Existing; already does this |
| Mosquitto | Routes MQTT messages between publisher and subscriber | Existing; already running |
| bridge.py | Subscribes to `shairport-sync/remote`, maps command strings to D-Bus method calls | New — the thing to build |
| Shairport-Sync | Exposes D-Bus interface `org.gnome.ShairportSync` on system bus | Existing; must be compiled `--with-dbus-interface` |

---

## D-Bus Interface Reference

Shairport-Sync exposes the following on the system bus under `org.gnome.ShairportSync` at `/org/gnome/ShairportSync`:

### Playback Control (routes to AirPlay sender via DACP — iOS 17.4+ unreliable)

| D-Bus Method | Interface | Effect |
|---|---|---|
| `Play()` | `org.gnome.ShairportSync.RemoteControl` | Resume playback |
| `Pause()` | `org.gnome.ShairportSync.RemoteControl` | Pause playback |
| `PlayPause()` | `org.gnome.ShairportSync.RemoteControl` | Toggle play/pause |
| `Next()` | `org.gnome.ShairportSync.RemoteControl` | Next track |
| `Previous()` | `org.gnome.ShairportSync.RemoteControl` | Previous track |
| `VolumeUp()` | `org.gnome.ShairportSync.RemoteControl` | Volume up (sender) |
| `VolumeDown()` | `org.gnome.ShairportSync.RemoteControl` | Volume down (sender) |
| `ToggleMute()` | `org.gnome.ShairportSync.RemoteControl` | Mute toggle |

### Volume Control (local ALSA mixer — reliable, not DACP)

| D-Bus Property | Interface | Range | Effect |
|---|---|---|---|
| `Volume` (set) | `org.gnome.ShairportSync` | -30.0 to 0.0 dB; -144.0 = mute | Sets local output volume |

Setting `Volume` via `org.freedesktop.DBus.Properties.Set` modifies the ALSA mixer directly. This is the recommended path for volume control from the touchscreen.

---

## Recommended Project Structure

```
/opt/airplay-bridge/        # or /home/pi/airplay-bridge/
├── bridge.py               # single-file service: MQTT subscriber + D-Bus caller
├── bridge.service          # systemd unit file
└── requirements.txt        # paho-mqtt, pydbus (or dbus-python)
```

### Structure Rationale

- **Single-file service:** The bridge has one job — map MQTT payloads to D-Bus calls. A single Python file is appropriate; splitting into modules adds complexity with no benefit at this scale.
- **systemd unit:** The bridge must survive reboots and restart on failure. A `.service` file is the standard pattern on Raspberry Pi OS.
- **No config file needed initially:** MQTT host, topic, and D-Bus target are static on this hardware. Hardcoded constants are fine; extract to config only if the service is ever reused elsewhere.

---

## Architectural Patterns

### Pattern 1: MQTT loop_start + GLib MainLoop

**What:** Run paho-mqtt's network loop in a background thread (`client.loop_start()`), and drive D-Bus callbacks via GLib's `MainLoop`. The MQTT `on_message` callback fires from the paho thread; D-Bus calls are made directly from that callback (they are thread-safe for method calls on a proxy object).

**When to use:** This project — the bridge needs both an MQTT receive loop and access to D-Bus. GLib mainloop is required by pydbus; paho's `loop_start` runs independently in a daemon thread.

**Trade-offs:** Simple to reason about. No asyncio complexity. GLib MainLoop adds ~2 MB RSS on Pi — acceptable.

**Skeleton:**
```python
from pydbus import SystemBus
from gi.repository import GLib
import paho.mqtt.client as mqtt
import threading

MQTT_HOST = "localhost"
MQTT_TOPIC = "shairport-sync/remote"
DBUS_NAME = "org.gnome.ShairportSync"
DBUS_PATH = "/org/gnome/ShairportSync"

bus = SystemBus()
shairport = bus.get(DBUS_NAME, DBUS_PATH)

COMMAND_MAP = {
    "play":       lambda: shairport.Play(),
    "pause":      lambda: shairport.Pause(),
    "playpause":  lambda: shairport.PlayPause(),
    "nextitem":   lambda: shairport.Next(),
    "previtem":   lambda: shairport.Previous(),
    "volumeup":   lambda: shairport.VolumeUp(),
    "volumedown": lambda: shairport.VolumeDown(),
    "mutetoggle": lambda: shairport.ToggleMute(),
}

def on_message(client, userdata, msg):
    command = msg.payload.decode().strip().lower()
    action = COMMAND_MAP.get(command)
    if action:
        action()

client = mqtt.Client()
client.on_message = on_message
client.connect(MQTT_HOST, 1883)
client.subscribe(MQTT_TOPIC)
client.loop_start()

GLib.MainLoop().run()
```

### Pattern 2: Pure paho loop_forever (no GLib)

**What:** Use paho's blocking `loop_forever()` as the main loop. Make D-Bus calls via `dbus-python` low-level API without a GLib mainloop.

**When to use:** If pydbus cannot be installed (e.g., missing gi.repository). Falls back to `dbus-python` directly or subprocess `dbus-send`.

**Trade-offs:** Simpler event loop, but `dbus-python` without GLib loses D-Bus signal reception capability. Fine here since we only need to call methods, not listen for signals.

### Pattern 3: subprocess dbus-send (no Python D-Bus library)

**What:** In the `on_message` callback, call `subprocess.run(["dbus-send", ...])` for each command.

**When to use:** Absolute fallback if neither pydbus nor dbus-python installs cleanly on the target Pi.

**Trade-offs:** Slow (subprocess fork per command), but commands are infrequent (user button presses). Works with zero Python D-Bus dependencies. Adds ~50 ms latency per command — imperceptible to a human.

---

## Data Flow

### Command Flow (happy path)

```
User taps button on touchscreen
        |
        v
nowplaying.html publishes payload "playpause"
  to MQTT topic: shairport-sync/remote
  via WebSocket → Mosquitto (port 9001 → 1883)
        |
        v
Mosquitto routes to all subscribers of shairport-sync/remote
        |
        v
bridge.py on_message() receives payload "playpause"
        |
        v
COMMAND_MAP lookup → shairport.PlayPause()
        |
        v
pydbus sends D-Bus method call on system bus
  dest=org.gnome.ShairportSync
  path=/org/gnome/ShairportSync
  interface=org.gnome.ShairportSync.RemoteControl
  method=PlayPause
        |
        v
Shairport-Sync executes command
  (routes to AirPlay source via DACP for play/pause/next/prev)
  (modifies ALSA mixer directly for volume)
```

### Volume-Specific Flow

```
User taps volume up on touchscreen
        |
        v
nowplaying.html publishes "volumeup" to shairport-sync/remote
        |
        v
bridge.py maps to shairport.VolumeUp()
  OR (preferred for local control):
  Properties.Set org.gnome.ShairportSync Volume double:-15.0
        |
        v
ALSA mixer updated immediately (local — not DACP)
        |
        v
Shairport-Sync publishes updated volume to shairport-sync/volume
        |
        v
nowplaying.html receives volume update and reflects in UI
```

---

## Build Order

The bridge has minimal internal dependencies. The correct build sequence based on what can be validated independently:

1. **Verify D-Bus interface is available** — confirm Shairport-Sync was compiled `--with-dbus-interface` and `dbus_service_bus = "system"` is set in `shairport-sync.conf`. Test with `dbus-send` from the command line before writing any Python.

2. **Implement D-Bus caller** — write and test the pydbus proxy calls in isolation (a small test script calling `Play()`, `Pause()`, `VolumeUp()`). Confirm they affect Shairport-Sync before wiring MQTT.

3. **Implement MQTT subscriber** — add paho-mqtt subscription to `shairport-sync/remote`. Log received payloads without taking action. Confirm the frontend's button presses arrive.

4. **Wire them together** — connect the `on_message` callback to the command map. Test end-to-end from button press to playback change.

5. **Package as systemd service** — write the `.service` unit, enable on boot, test survive/restart behavior.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Mosquitto | paho-mqtt client; subscribe to `shairport-sync/remote` on `localhost:1883` | No auth required (local loopback); WebSocket port 9001 is for the browser, not the bridge |
| Shairport-Sync D-Bus | pydbus `SystemBus().get()` proxy | Requires `dbus_service_bus = "system"` in shairport-sync.conf; service name `org.gnome.ShairportSync` |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| paho thread ↔ D-Bus proxy | Direct method call from `on_message` callback | pydbus method calls are safe to call from threads; no locking needed for fire-and-forget commands |
| bridge.py ↔ systemd | stdout/stderr logging; exit codes | Use `print()` to stdout; systemd captures via journald |

---

## Anti-Patterns

### Anti-Pattern 1: Using Shairport-Sync's Built-in MQTT Remote (`enable_remote = "yes"`)

**What people do:** Enable the built-in MQTT remote in shairport-sync.conf and expect the frontend's MQTT publishes to control playback.

**Why it's wrong:** The built-in remote routes commands via DACP back to the AirPlay sender (iPhone/Mac). Since iOS 17.4+ stopped sending the DACP ID, all commands are silently dropped on modern Apple devices. Volume commands routed this way also fail on AirPlay 2 streams.

**Do this instead:** Build the bridge service described here. It calls the D-Bus interface directly on the local process, bypassing DACP entirely for volume (via the `Volume` property), and using the RemoteControl interface for play/pause/next/prev with the understanding those still use DACP for the playback commands.

### Anti-Pattern 2: Using the MPRIS Interface Instead of Native D-Bus

**What people do:** Target `org.mpris.MediaPlayer2.ShairportSync` because MPRIS is a standard and tooling is familiar.

**Why it's wrong:** The MPRIS interface in Shairport-Sync has more limited volume control (0.0–1.0 normalized, not dB) and requires a separate compile flag (`--with-mpris-interface`). The native `org.gnome.ShairportSync` interface is richer and better documented for this use case.

**Do this instead:** Use `org.gnome.ShairportSync` (native interface). It has explicit `RemoteControl` methods and the `Volume` property in dB.

### Anti-Pattern 3: Running the Bridge as Root

**What people do:** Run the systemd service as root to avoid D-Bus policy issues.

**Why it's wrong:** Unnecessary privilege. Creates security exposure on a kiosk device.

**Do this instead:** Add a D-Bus policy rule in `/etc/dbus-1/system.d/` allowing the service user (e.g., `pi`) to call methods on `org.gnome.ShairportSync`. Shairport-Sync already registers on the system bus; the policy file grants access without requiring root.

### Anti-Pattern 4: asyncio for the Event Loop

**What people do:** Use asyncio + asyncio-mqtt to avoid GLib dependency.

**Why it's wrong:** pydbus requires GLib.MainLoop — there is no asyncio integration. If you want asyncio, you must use `gbulb` to replace the asyncio event loop with GLib's, adding a non-obvious dependency. For a bridge that only calls methods (no D-Bus signal watching), this complexity is not justified.

**Do this instead:** Use `paho.loop_start()` in a thread and `GLib.MainLoop().run()` as the main blocking call. This is the documented pattern and adds no complexity.

---

## Scaling Considerations

This is a single-Pi, single-user kiosk. Scaling is not relevant. The only reliability concern is:

| Concern | Approach |
|---------|----------|
| Bridge crashes | systemd `Restart=on-failure` with `RestartSec=2s` |
| Mosquitto not yet up at boot | systemd `After=mosquitto.service` + `Requires=mosquitto.service` |
| Shairport-Sync D-Bus not ready | Retry loop on startup with 1-second backoff; log and exit after N attempts so systemd restarts the bridge |
| MQTT disconnect | paho's `loop_start` handles reconnection automatically if `reconnect_on_failure=True` (default in paho 2.x) |

---

## Sources

- [Shairport-Sync sample dbus commands](https://github.com/mikebrady/shairport-sync/blob/master/documents/sample%20dbus%20commands) — HIGH confidence (official repo)
- [Shairport-Sync MQTT.md](https://github.com/mikebrady/shairport-sync/blob/master/MQTT.md) — HIGH confidence (official repo)
- [Issue #1822: D-Bus commands ignored on iOS 17.4](https://github.com/mikebrady/shairport-sync/issues/1822) — HIGH confidence (official repo issue)
- [Issue #1858: MQTT Remote Control does nothing](https://github.com/mikebrady/shairport-sync/issues/1858) — HIGH confidence (official repo issue)
- [dbus-python tutorial](https://dbus.freedesktop.org/doc/dbus-python/tutorial.html) — HIGH confidence (official docs)
- [pydbus tutorial](https://pydbus.readthedocs.io/en/latest/legacydocs/tutorial.html) — HIGH confidence (official docs)
- [paho-mqtt PyPI](https://pypi.org/project/paho-mqtt/) — HIGH confidence (official)
- [Victron dbus-mqtt reference implementation](https://github.com/victronenergy/dbus-mqtt) — MEDIUM confidence (real-world MQTT↔D-Bus bridge pattern)

---

*Architecture research for: MQTT-to-D-Bus bridge for Shairport-Sync control*
*Researched: 2026-03-29*
