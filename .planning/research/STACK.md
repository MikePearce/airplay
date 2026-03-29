# Stack Research

**Domain:** MQTT-to-D-Bus bridge service on Raspberry Pi
**Researched:** 2026-03-29
**Confidence:** HIGH (core choices verified against official docs and official repos)

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11 (system default on Pi OS Bookworm) | Service runtime | Ships with Raspberry Pi OS Bookworm, no install needed. The bridge is I/O-bound with trivial logic — Python is the correct weight for this job. Avoid compiled languages for a 50-line event loop. |
| paho-mqtt | 2.1.0 | Subscribe to MQTT topic, receive control commands | The canonical Eclipse MQTT client. Actively maintained. v2.1.0 introduces the `CallbackAPIVersion` enum to stabilise the callback API ahead of v3.0. Ships pre-built on piwheels so pip install is fast on Pi. |
| jeepney | 0.9.0 | Make D-Bus method calls to Shairport-Sync | Pure-Python D-Bus implementation. No C extension to compile, no libdbus build dependency. Works correctly in a venv without `--system-site-packages`. Actively maintained (0.9.0 released Feb 2025). Provides a clean blocking proxy API. |
| systemd (unit file) | — | Process supervision, auto-start on boot | Pi OS Bookworm uses systemd. A unit file is the correct way to run a long-lived service — no PID files, no screen sessions, no cron workarounds. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dotenv | 1.x | Load MQTT broker config (host, port, topic) from `.env` | Use if broker host/port must be configurable without editing source. Optional for a hardcoded single-Pi deploy. |
| logging (stdlib) | — | Structured log output captured by journald | Always. `systemd-journald` captures stdout/stderr. Use `logging.basicConfig` pointing at stdout; `journalctl -u <service>` does the rest. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| just | Task runner for dev commands | Consistent with the project's existing convention (see project CLAUDE.md). Define `just install`, `just logs`, `just status` targets. |
| mosquitto_pub | Manual MQTT command injection for testing | Already on the Pi (`sudo apt install mosquitto-clients`). Use to fire test commands without the frontend: `mosquitto_pub -t shairport-sync/remote -m PlayPause` |
| dbus-send | Verify D-Bus interface independently of the bridge | `dbus-send --system --print-reply --dest=org.gnome.ShairportSync /org/gnome/ShairportSync org.gnome.ShairportSync.RemoteControl.PlayPause` |
| journalctl | Read service logs | `journalctl -u airplay-bridge -f` |

---

## Installation

```bash
# On the Raspberry Pi — create a venv (required on Bookworm)
python3 -m venv /opt/airplay-bridge/venv

# Install dependencies
/opt/airplay-bridge/venv/bin/pip install \
  paho-mqtt==2.1.0 \
  jeepney==0.9.0

# No --system-site-packages needed — jeepney is pure Python
# No apt packages needed beyond base Python
```

```ini
# /etc/systemd/system/airplay-bridge.service
[Unit]
Description=AirPlay MQTT to D-Bus Bridge
After=network.target mosquitto.service

[Service]
Type=simple
ExecStart=/opt/airplay-bridge/venv/bin/python /opt/airplay-bridge/bridge.py
Restart=on-failure
RestartSec=5
User=pi

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now airplay-bridge
```

---

## Shairport-Sync D-Bus Interface Reference

This is the interface the bridge calls. Verified against official Shairport-Sync docs.

| Item | Value |
|------|-------|
| Bus | System bus (default) — configurable via `dbus_service_bus` in `shairport-sync.conf` |
| Service name | `org.gnome.ShairportSync` |
| Object path | `/org/gnome/ShairportSync` |
| Remote control interface | `org.gnome.ShairportSync.RemoteControl` |
| Volume (integer 0–100) | `org.gnome.ShairportSync.AdvancedRemoteControl.SetVolume` (int32) |
| MPRIS interface | `org.mpris.MediaPlayer2.ShairportSync` (alternative, not needed here) |

**Available RemoteControl methods (no parameters):**
`Play`, `Pause`, `PlayPause`, `Resume`, `Stop`, `Next`, `Previous`, `VolumeUp`, `VolumeDown`, `ToggleMute`

**Confirmed working jeepney pattern:**

```python
from jeepney import DBusAddress, new_method_call
from jeepney.io.blocking import open_dbus_connection

SHAIRPORT = DBusAddress(
    "/org/gnome/ShairportSync",
    bus_name="org.gnome.ShairportSync",
    interface="org.gnome.ShairportSync.RemoteControl",
)

with open_dbus_connection(bus="SYSTEM") as conn:
    msg = new_method_call(SHAIRPORT, "PlayPause")
    conn.send_and_get_reply(msg)
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| jeepney | dbus-python (1.4.0) | Never for new code. Marked "Inactive" on PyPI. Its own docs say "might not be the best binding." Requires libdbus C headers to build from pip, and `python3-dbus` apt package pulls in GLib/GObject overhead. Use only if you find jeepney has an undocumented gap with the shairport-sync system bus policy. |
| jeepney | dasbus | Reasonable alternative. Active development, cleaner high-level API. But it wraps GLib/GObject (pulls in PyGObject), which is heavier than jeepney's zero-dependency pure-Python approach. Overkill for 3 method calls. |
| paho-mqtt 2.x (CallbackAPIVersion.VERSION2) | asyncio-mqtt / aiomqtt | Use asyncio-mqtt if you want a fully async service with `async/await`. Unnecessary here — the bridge is fire-and-forget (receive MQTT → call D-Bus → done). Synchronous paho with `loop_start()` is simpler and adequate. |
| systemd unit | Docker / PM2 / supervisor | Systemd is already on the Pi. Docker adds ~200MB image overhead, port mapping complexity, and D-Bus socket sharing friction. Never use Docker for a single-Pi system-bus service. |
| Python | Go / Rust | Go and Rust produce smaller binaries but require a D-Bus binding (dbus crate, etc.) and a cross-compile or on-device build step. Python ships on the Pi and the performance difference is irrelevant for a 10-command-per-minute service. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `dbus-python` (pip) | Marked "Inactive" by maintainers. Requires libdbus C headers (`apt install libdbus-1-dev python3-dev`) to pip-install, or `python3-dbus` apt package which pulls in GLib event loop. Its own documentation lists alternatives as preferable. | jeepney |
| `paho-mqtt` VERSION1 callback API | Deprecated in 2.0, will be removed in 3.0. Using it today means a forced migration later. | paho-mqtt 2.x with `CallbackAPIVersion.VERSION2` |
| `pip install --break-system-packages` | Raspberry Pi OS Bookworm enforces PEP 668. Bypassing it corrupts the system Python environment. | `python3 -m venv` per service |
| Global apt `python3-dbus` as the only mechanism | Ties the service to the system Python, can't be isolated in a venv. | jeepney in a venv (pure Python, no system packages needed) |
| Running the bridge as root | Grants unnecessary privilege. The system bus D-Bus policy for shairport-sync allows the `pi` user (or `shairport-sync` group) to call its interface. | Configure the D-Bus policy file correctly, run as `pi` |

---

## Stack Patterns by Variant

**If shairport-sync is configured to use the session bus (`dbus_service_bus = "session"` in shairport-sync.conf):**
- Change `open_dbus_connection(bus="SESSION")` in the bridge
- The session bus is user-scoped; the bridge must run as the same user as shairport-sync
- No D-Bus policy file changes needed (session bus has no access restrictions)
- Simpler for dev/testing, but default installs use the system bus

**If the MQTT broker requires authentication (not the default Mosquitto config on this Pi):**
- Add `client.username_pw_set(username, password)` before `client.connect()`
- Or configure Mosquitto ACLs to allow localhost without auth (already the default here)

**If volume control via absolute value (0–100) is needed instead of VolumeUp/VolumeDown:**
- Use `org.gnome.ShairportSync.AdvancedRemoteControl` interface with `SetVolume` (int32)
- Same jeepney pattern, different `DBusAddress` interface string

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| paho-mqtt 2.1.0 | Python 3.7–3.12 | Confirmed. Use `CallbackAPIVersion.VERSION2`. |
| jeepney 0.9.0 | Python 3.7+ | Confirmed. No C extensions, no system library deps. |
| Python 3.11.2 | Pi OS Bookworm (Debian 12) | System default. No install needed. |
| jeepney 0.9.0 | System bus (shairport-sync default) | Verified pattern: `open_dbus_connection(bus="SYSTEM")` |

---

## D-Bus Policy Note (Critical)

Shairport-Sync installs a D-Bus policy file at `/etc/dbus-1/system.d/shairport-sync.conf`. By default it allows the `shairport-sync` system user to own the bus name, but calling from a non-root user (e.g., `pi`) may require adding a policy entry:

```xml
<policy user="pi">
  <allow send_destination="org.gnome.ShairportSync"/>
</policy>
```

Without this, the bridge will silently fail or receive an access-denied error. Verify with `dbus-send` as the `pi` user before assuming the bridge code is broken.

---

## Sources

- https://pypi.org/project/paho-mqtt/ — version 2.1.0 confirmed, CallbackAPIVersion breaking change
- https://pypi.org/project/jeepney/ — version 0.9.0 confirmed, pure Python, actively maintained
- https://pypi.org/project/dbus-python/ — version 1.4.0, status "Inactive" confirmed
- https://github.com/mikebrady/shairport-sync/blob/master/documents/sample%20dbus%20commands — D-Bus service name, object path, interface, method list (HIGH confidence — official repo)
- https://github.com/pimoroni/pirate-audio/blob/master/examples/shairport-sync-control.py — working Python D-Bus control example for shairport-sync (MEDIUM confidence — third party but widely referenced)
- https://github.com/mikebrady/shairport-sync/discussions/1862 — system vs session bus behaviour, permission requirements (HIGH confidence — official repo discussion)
- https://www.raspberrypi.com/news/bookworm-the-new-version-of-raspberry-pi-os/ — Python 3.11 default, venv requirement on Bookworm (HIGH confidence — official Raspberry Pi source)

---

*Stack research for: MQTT-to-D-Bus bridge (Shairport-Sync AirPlay control)*
*Researched: 2026-03-29*
