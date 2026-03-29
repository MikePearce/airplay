# Environment Verification Checklist

**Purpose:** Confirm D-Bus interface availability, AirPlay 2 remote control viability, and MQTT message flow on the Raspberry Pi before any bridge code is written.

**How to use:** Run each step in order. Paste the terminal output for every step back into the chat — even if a step passes cleanly. Later steps only make sense if earlier ones pass. Stop and paste output as soon as a step fails.

**Remediation:** This checklist is diagnostic only. If a step fails, remediation commands and paths are documented in `01-RESEARCH.md`.

---

## Step 0 — Identify Environment

Run all three commands and paste the output.

**0a. Capture your username:**

```bash
whoami
```

Expected: your custom username (e.g. `mike`, `pi`, `airplay-user`). This matters for D-Bus policy checks in Step 3.

**0b. Capture Shairport-Sync version and compile flags:**

```bash
shairport-sync -V
```

Expected: a long version string listing all compile-time features, for example:
```
Version: 4.3.2-OpenSSL-Avahi-ALSA-stdout-pipe-soxr-metadata-dbus-interface-mqtt-interface
```

Paste the entire output — you need this for Step 1.

**0c. Confirm Pi OS version:**

```bash
cat /etc/os-release | head -5
```

Expected: something like `PRETTY_NAME="Debian GNU/Linux 12 (bookworm)"`.

---

## Step 1 — D-Bus Compile Flag Check

**Inspect the output from `shairport-sync -V` (Step 0b).**

Look for the string `dbus-interface` anywhere in the output.

**If `dbus-interface` IS present in the output:** The D-Bus interface is compiled in. Proceed to Step 2.

**If `dbus-interface` is NOT present in the output:** Stop here.

- Failure meaning: The installed Shairport-Sync binary was compiled without the D-Bus interface. The `busctl list` check, D-Bus policy check, and PlayPause test in Steps 2–4 are impossible without this flag.
- Paste the full `-V` output and note "D-Bus compile flag absent."
- Remediation paths (source compilation with `--with-dbus-interface`, or accepting volume-only control) are described in `01-RESEARCH.md` under "Remediation Paths."

---

## Step 2 — D-Bus Bus Registration

*Only run this step if Step 1 passed (D-Bus compile flag present).*

**2a. Check if Shairport-Sync is registered on the system bus:**

```bash
busctl list | grep -i shairport
```

Expected output when working:
```
org.gnome.ShairportSync   <pid>  shairport-sync  shairport-sync  ...
```

**If the output is non-empty** (`org.gnome.ShairportSync` appears): Proceed to Step 3.

**If the output is empty** (nothing returned): Stop here.

- Run these diagnostics and paste the output:

  ```bash
  systemctl status shairport-sync
  ```

  ```bash
  grep -i dbus /etc/shairport-sync.conf
  ```

- Failure meanings:
  - Service not running: `systemctl status shairport-sync` will show inactive/failed.
  - D-Bus disabled in config: The `dbus_service_bus` line in `shairport-sync.conf` may be commented out or set incorrectly.
  - Service running but D-Bus not registering: Compile flag may be present but a config issue prevents registration.

---

## Step 3 — D-Bus Policy and Access

*Only run this step if Step 2 passed (interface registered on system bus).*

**3a. Check whether a policy file exists:**

```bash
ls -la /etc/dbus-1/system.d/ | grep -i shairport
```

Expected: a line showing `shairport-sync-dbus-policy.conf` (or similar name).

**3b. Read the policy file content:**

```bash
cat /etc/dbus-1/system.d/shairport-sync-dbus-policy.conf 2>/dev/null || echo "POLICY FILE MISSING"
```

Expected output when correctly configured — it should contain a `send_destination` grant. It may look like this:

```xml
<policy context="default">
  <allow send_destination="org.gnome.ShairportSync"/>
  <allow receive_sender="org.gnome.ShairportSync"/>
</policy>
```

Or a user-specific entry:

```xml
<policy user="YOUR_USERNAME">
  <allow send_destination="org.gnome.ShairportSync"/>
</policy>
```

**Analyse the output:**

- If the file is missing (output shows `POLICY FILE MISSING`): Your user account will receive `AccessDenied` errors when calling D-Bus. Note this failure and paste the output. Remediation is in `01-RESEARCH.md` under "Pitfall 3" and "Remediation Paths."
- If the file exists but contains no `send_destination` for your user or for `context="default"`: Same failure — paste the full file content.
- If the file exists and grants `send_destination` to `context="default"` or to your specific username: Proceed to Step 4.

---

## Step 4 — Live AirPlay Playback Test

*Only run this step if Step 3 passed (policy file grants access).*

**IMPORTANT: You MUST be actively streaming audio from your iPhone or Mac via AirPlay to the Pi before running this command. Do not run this while idle.**

1. Start playing music from your iPhone or Mac via AirPlay to the Pi.
2. Confirm audio is audible from the Pi's speakers.
3. Then, from an SSH session or the Pi's keyboard, run:

```bash
dbus-send --system --print-reply \
  --dest=org.gnome.ShairportSync \
  /org/gnome/ShairportSync \
  org.gnome.ShairportSync.RemoteControl.PlayPause
```

**Three possible outcomes:**

| What you observe | Meaning | Next action |
|-----------------|---------|-------------|
| Command returns a reply AND the streaming device physically pauses | D-Bus works and AirPlay 2 remote control is functional | **PASS** — proceed to Step 5 |
| Command returns `org.freedesktop.DBus.Error.AccessDenied` | Policy file missing or user not permitted | **FAIL** — go back to Step 3 and paste the `AccessDenied` error |
| Command returns a reply (or no error), but the device does NOT pause | D-Bus interface works but AirPlay 2 DACP is broken (iOS 17.4+ issue) | **FAIL (DACP)** — run Step 4b and paste output |

**4b. If the device did NOT pause — check Shairport-Sync logs immediately after:**

```bash
journalctl -u shairport-sync -n 20 --no-pager
```

- If the log shows a DACP request that failed, or shows no outbound DACP request at all: AirPlay 2 DACP is broken. This is a known permanent issue confirmed by the Shairport-Sync maintainer (issue #1822, closed "not planned" April 2024).
- Paste the full log output.
- Remediation paths (recompile with `--without-airplay2` to restore AirPlay 1 DACP path, or accept volume-only control) are in `01-RESEARCH.md` under "Path B" and "Path C."

---

## Step 5 — MQTT Topic Flow

*Run this step regardless of Step 4 outcome — MQTT verification is independent.*

You need two terminal sessions for this step.

**Terminal 1: Start subscribing to all Shairport-Sync MQTT messages:**

```bash
mosquitto_sub -h localhost -t 'shairport-sync/#' -v
```

Leave this running. It will print messages as they arrive.

**Terminal 2 (or the touchscreen): Tap a button on the Now Playing display (nowplaying.html).**

Tap play/pause, next, or previous.

**Expected output in Terminal 1:**

```
shairport-sync/remote playpause
```

(or `nextitem` / `previtem` depending on which button was tapped)

**If nothing appears in Terminal 1 when a button is tapped:**

Run these diagnostics and paste all output:

```bash
systemctl status mosquitto
```

```bash
which mosquitto_sub
```

- Failure meanings:
  - `mosquitto` service not running: start it or check why it stopped.
  - `mosquitto_sub` not found: install with `sudo apt install mosquitto-clients`.
  - Service running but no messages: nowplaying.html may be connecting to the wrong broker address or wrong port. It must connect to WebSocket port 9001. Check the browser console on the touchscreen for connection errors.

---

## Step 6 — Summary Gate

**Complete this section after running Steps 0–5. Check each box based on your observations.**

| # | Success Criterion | Pass? |
|---|------------------|-------|
| 1 | `busctl list` shows `org.gnome.ShairportSync` (Step 2 passed) | [ ] Pass / [ ] Fail |
| 2 | `dbus-send PlayPause` causes the streaming device to physically pause (Step 4 outcome (a)) | [ ] Pass / [ ] Fail |
| 3 | `mosquitto_sub` shows button press messages when the touchscreen is tapped (Step 5 passed) | [ ] Pass / [ ] Fail |
| 4 | No `AccessDenied` errors from D-Bus calls (Step 4 produced no AccessDenied) | [ ] Pass / [ ] Fail |

---

**If all four pass:**

Phase 2 is unblocked. Paste "all passed" along with the terminal output from all steps.

**If any fail:**

Paste the terminal output for every step you ran (including the passing ones — the full output is needed to write the Phase 1 summary). Describe which criterion failed and what the terminal showed. We will determine the remediation path together.
