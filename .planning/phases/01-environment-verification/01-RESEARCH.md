# Phase 1: Environment Verification - Research

**Researched:** 2026-03-29
**Domain:** Shairport-Sync D-Bus interface verification, AirPlay 2 remote control viability, MQTT topic flow confirmation on Raspberry Pi
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- User is on iOS 17.4+ (high risk for DACP breakage) and AirPlays from multiple Apple devices
- Strategy: test first, decide later — run D-Bus PlayPause during an active AirPlay session and observe
- If playback commands are broken: user is open to recompiling Shairport-Sync from source IF the effort is reasonable
- If recompilation is too complex: accept volume-only control as a fallback
- Shairport-Sync install method unknown — may be apt or compiled; verification must check both D-Bus interface presence and compile flags
- User runs a custom Pi username (not default `pi`) — D-Bus policy file must grant access to that specific user
- MQTT is confirmed working (Now Playing display functions) but D-Bus enablement is unknown — needs checking in /etc/shairport-sync.conf
- User accesses Pi via both SSH and direct keyboard
- Mosquitto WebSocket on port 9001 (confirmed)
- Default topic prefix: `shairport-sync` (confirmed)
- No authentication required (anonymous connections)
- Standard MQTT port 1883 for non-WebSocket connections

### Claude's Discretion

- Whether to produce a verification script or a step-by-step document
- Scope of end-to-end testing (full chain vs. component-by-component)
- How to structure the D-Bus policy file fix if needed

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

## Summary

Phase 1 is a hardware verification gate, not an implementation phase. No code is written. The goal is to confirm three things on the actual Pi before writing any bridge code: (1) the Shairport-Sync D-Bus interface is compiled in and accessible by the user's account, (2) D-Bus PlayPause commands during an active AirPlay session cause the streaming device to respond, and (3) MQTT button-press messages from the touchscreen flow through Mosquitto on the expected topic.

Two independent showstoppers can only be detected on real hardware. First: the Shairport-Sync apt package on Raspberry Pi OS frequently omits the `--with-dbus-interface` compile flag, meaning `org.gnome.ShairportSync` simply never appears on the system bus. This must be checked with `busctl list` before any Python is written. Second: since iOS 17.4 and macOS 14.4, Apple stopped transmitting the DACP-ID in AirPlay 2 sessions, making play/pause/next/previous commands silently no-ops even when D-Bus calls complete without error. The Shairport-Sync maintainer confirmed this is permanent (issue #1822, closed "not planned"). These two risks are the entire reason Phase 1 exists.

The verification work is diagnostic, not constructive. If all checks pass, Phase 2 begins immediately. If D-Bus is missing, the decision is whether to compile from source (well-documented process, ~30–60 min) or proceed with volume-only control. If AirPlay 2 DACP is broken on the user's iOS device, the decision is whether to recompile without AirPlay 2 support or document the limitation. The CONTEXT.md decisions are clear: test first, then decide.

**Primary recommendation:** Produce a single verification checklist document (not a script) that the user runs top-to-bottom, pasting results back for analysis. The checklist structure reflects the dependency order: D-Bus interface presence → D-Bus policy access → shairport-sync.conf settings → live AirPlay command test → MQTT topic flow test.

---

## Standard Stack

### Core (verification tooling — already present on Pi)

| Tool | Version | Purpose | Already Installed? |
|------|---------|---------|-------------------|
| `busctl` | systemd component | List system bus names; confirm `org.gnome.ShairportSync` presence | Yes — ships with Raspberry Pi OS Bookworm |
| `dbus-send` | dbus package | Send test D-Bus method calls; verify permission and response | Yes — ships with Raspberry Pi OS |
| `shairport-sync -V` | installed version | Report compile-time feature flags; confirm `--with-dbus-interface` was included | Yes — native binary check |
| `mosquitto_sub` | mosquitto-clients | Subscribe to MQTT topics; verify button-press messages arrive | Likely yes; confirm with `which mosquitto_sub` |
| `systemctl` | systemd | Check service status; restart services after config changes | Yes — ships with Raspberry Pi OS Bookworm |
| `cat` / `grep` | coreutils | Read shairport-sync.conf, D-Bus policy files | Yes — always present |

### Supporting (needed only if remediation is required)

| Tool | Purpose | Install Command |
|------|---------|-----------------|
| `build-essential git autoconf automake libtool` | Required for compiling from source | `sudo apt install ...` |
| `libglib2.0-dev libdbus-1-dev` | D-Bus development headers for `--with-dbus-interface` compile flag | `sudo apt install libglib2.0-dev libdbus-1-dev` |
| Full source build deps | See remediation section | Listed in the source-compilation path below |

---

## Architecture Patterns

### Verification Dependency Order

The checks have a strict dependency order. Subsequent checks are only meaningful if earlier ones pass:

```
1. shairport-sync -V                   # Is D-Bus compiled in?
        |
        v (yes: interface present)
2. busctl list | grep -i shairport     # Is it registered on the bus?
        |
        v (yes: interface registered)
3. cat /etc/shairport-sync.conf        # Is dbus_service_bus set correctly?
4. cat /etc/dbus-1/system.d/shairport* # Does the policy file exist?
        |
        v
5. dbus-send PlayPause (as the user)   # Can the user call it? Does it work?
        |
        v (during active AirPlay session)
6. mosquitto_sub shairport-sync/#      # Does the MQTT topic flow match?
```

If step 1 fails (no D-Bus in compile flags), steps 2–5 are meaningless. Proceed to source compilation decision. If step 5 fails with no response from the Apple device, the AirPlay 2 DACP issue is confirmed.

### Decision Tree After Verification

```
D-Bus interface present?
├── NO  → Two paths:
│         A) Compile from source with --with-dbus-interface (see below)
│         B) Accept volume-only limitation (no play/pause/next/prev)
└── YES → D-Bus policy grants access?
          ├── NO  → Add user to /etc/dbus-1/system.d/shairport-sync-dbus-policy.conf
          └── YES → PlayPause during active AirPlay session works?
                    ├── YES → All green. Phase 2 unblocked.
                    └── NO  → AirPlay 2 DACP broken. Two paths:
                              A) Recompile without AirPlay 2 (--without-airplay2)
                              B) Accept volume-only limitation
```

---

## Verification Commands

All commands run on the Pi as the actual user account (not root). Replace `YOUR_USERNAME` with the actual username.

### Step 1: Check Compile Flags

```bash
shairport-sync -V
```

Look for `dbus-interface` in the output. A binary with D-Bus support will show it in the feature list. No D-Bus entry means the apt package was built without it.

Expected output fragment when D-Bus is present:
```
Version: 4.x.x-OpenSSL-Avahi-ALSA-stdout-pipe-soxr-metadata-dbus-interface-mqtt-interface...
```

### Step 2: Check System Bus Registration

```bash
busctl list | grep -i shairport
```

Expected when working:
```
org.gnome.ShairportSync   <pid>  shairport-sync  shairport-sync  ...
```

Empty output = interface not on bus (compile flag missing, or shairport-sync.conf has D-Bus disabled, or service not running).

Alternative check:
```bash
dbus-send --system --print-reply \
  --dest=org.freedesktop.DBus \
  /org/freedesktop/DBus \
  org.freedesktop.DBus.ListNames \
  | grep -i shairport
```

### Step 3: Check shairport-sync.conf

```bash
grep -i dbus /etc/shairport-sync.conf
```

Look for `dbus_service_bus`. If the line is commented out or absent, D-Bus defaults to `"system"` — this is correct. If it reads `"session"`, note it (the bridge must match).

### Step 4: Check D-Bus Policy File

```bash
ls -la /etc/dbus-1/system.d/ | grep -i shairport
cat /etc/dbus-1/system.d/shairport-sync-dbus-policy.conf 2>/dev/null || \
  echo "POLICY FILE MISSING"
```

The policy file grants `send_destination` to callers. The default policy (from `make install`) allows any user to call methods via a `<policy context="default">` block. If the file is missing, the user will get `AccessDenied` errors.

### Step 5: Test D-Bus Access and AirPlay Control

**This test MUST be run while actively streaming from the target iOS device.**

```bash
dbus-send --system --print-reply \
  --dest=org.gnome.ShairportSync \
  /org/gnome/ShairportSync \
  org.gnome.ShairportSync.RemoteControl.PlayPause
```

Three possible outcomes:

| Outcome | Meaning |
|---------|---------|
| Returns reply, streaming device pauses | D-Bus works and AirPlay 2 remote control is functional |
| Returns `org.freedesktop.DBus.Error.AccessDenied` | Policy file missing or user not permitted |
| Returns reply (or no error), but device does NOT pause | AirPlay 2 DACP broken — iOS 17.4+ issue confirmed |

To disambiguate the third case (silent DACP failure), check Shairport-Sync logs immediately after the command:
```bash
journalctl -u shairport-sync -n 20 --no-pager
```
If a DACP attempt appears and fails, or if no outbound DACP request appears at all, DACP is broken.

### Step 6: Verify MQTT Topic Flow

```bash
# Terminal 1: subscribe to all shairport-sync messages
mosquitto_sub -h localhost -t 'shairport-sync/#' -v

# Then tap a button on the touchscreen (nowplaying.html)
```

Expected output in Terminal 1:
```
shairport-sync/remote playpause
```

If nothing appears when a button is tapped: confirm Mosquitto is running (`systemctl status mosquitto`) and that nowplaying.html is connecting to the correct broker address and port 9001.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| D-Bus interface discovery | Custom introspection code | `busctl list` and `shairport-sync -V` — both are already on the Pi |
| Testing D-Bus method calls | Python test script | `dbus-send` — synchronous, no dependencies, exact same path the bridge will use |
| MQTT traffic inspection | Custom Python subscriber | `mosquitto_sub -t 'shairport-sync/#' -v` — already on the Pi, zero setup |
| Compile flag detection | Parsing binary or source | `shairport-sync -V` prints the compile-time feature set directly |

**Key insight:** Every verification step in this phase uses tools already present on Raspberry Pi OS. No installation is needed for the verification work itself.

---

## Common Pitfalls

### Pitfall 1: D-Bus Call Succeeds But Device Does Not Respond (Silent DACP Failure)

**What goes wrong:** `dbus-send` PlayPause exits with no error and returns a reply. The iPhone or Mac does not pause. The D-Bus interface is confirmed working but the remote control is silently broken.

**Why it happens:** Since iOS 17.4 and macOS 14.4, Apple stopped transmitting `Active-Remote` and `DACP-ID` in AirPlay 2 sessions. Shairport-Sync has no valid target to forward the command to. Confirmed permanent by the Shairport-Sync maintainer (issue #1822, closed "not planned" April 2024). The D-Bus call "succeeds" from the Pi's perspective — there is no error to detect from the client side.

**How to avoid:** Test during active streaming. Observe the device physically. Check Shairport-Sync journal for DACP activity. Do not treat "dbus-send exited 0" as success proof.

**Warning signs:** Command completes instantly with no delay, but playback does not change. `journalctl -u shairport-sync` shows no DACP request logged after the command.

### Pitfall 2: D-Bus Interface Not on Bus Despite Service Running

**What goes wrong:** `busctl list | grep shairport` returns nothing. Shairport-Sync is running and streaming works.

**Why it happens:** The D-Bus interface (`--with-dbus-interface`) is an optional compile flag. The apt package on Raspberry Pi OS may not include it. The service can run and stream audio perfectly without the D-Bus interface.

**How to avoid:** Check `shairport-sync -V` first. If `dbus-interface` is not in the output, the entire D-Bus verification chain is impossible without recompilation.

**Recovery:** See source compilation path in the remediation section below.

### Pitfall 3: Policy File Is Present But User Is Still Denied

**What goes wrong:** `/etc/dbus-1/system.d/shairport-sync-dbus-policy.conf` exists, but `dbus-send` returns `AccessDenied`.

**Why it happens:** The default policy file installed by `make install` uses `<policy context="default">` which allows any user. However, some distributions install a more restrictive version that only allows the `shairport-sync` system user. The user's custom username is not in the policy.

**How to avoid:** Read the policy file content before assuming it is permissive. If the `<policy context="default">` block is absent or does not include `send_destination`, add the user explicitly.

**Fix:**
```xml
<!-- Add inside /etc/dbus-1/system.d/shairport-sync-dbus-policy.conf -->
<policy user="YOUR_USERNAME">
  <allow send_destination="org.gnome.ShairportSync"/>
</policy>
```

Then reload: `sudo systemctl daemon-reload && sudo systemctl restart shairport-sync`

### Pitfall 4: Testing Without Active AirPlay Session

**What goes wrong:** D-Bus calls are tested when nothing is streaming. All commands return without error. The conclusion is drawn that everything works. Phase 2 begins. Bridge is built. Buttons do nothing when music is playing.

**Why it happens:** Play/pause/next commands route to the AirPlay sender via DACP. With no active session there is no sender and no DACP connection to verify. The D-Bus call still completes — it just has nothing to dispatch to.

**How to avoid:** Always have an iPhone or Mac actively streaming audio from the App (Apple Music, Spotify via AirPlay, etc.) when running Step 5. Verify the device responds physically to the `dbus-send` PlayPause command.

### Pitfall 5: Policy File Requires Reload After Edit

**What goes wrong:** The policy file is edited to add the user. `dbus-send` still returns `AccessDenied`.

**Why it happens:** D-Bus does not hot-reload policies for active services. The shairport-sync service must be restarted for the policy change to take effect.

**Fix:** `sudo systemctl daemon-reload && sudo systemctl restart shairport-sync`

---

## Remediation Paths

### Path A: Compile Shairport-Sync from Source (D-Bus Missing)

If `shairport-sync -V` shows no `dbus-interface`, the apt binary is missing the flag. Compilation on Raspberry Pi Bookworm with D-Bus support:

```bash
# Install build dependencies
sudo apt install --no-install-recommends \
  build-essential git autoconf automake libtool \
  libpopt-dev libconfig-dev libasound2-dev \
  avahi-daemon libavahi-client-dev \
  libssl-dev libsoxr-dev libplist-dev libsodium-dev \
  uuid-dev libgcrypt-dev xxd \
  libglib2.0-dev libdbus-1-dev \
  libplist-utils libavutil-dev libavcodec-dev libavformat-dev

# Clone and build
git clone https://github.com/mikebrady/shairport-sync.git
cd shairport-sync
autoreconf -fi
./configure \
  --sysconfdir=/etc \
  --with-alsa \
  --with-avahi \
  --with-ssl=openssl \
  --with-metadata \
  --with-soxr \
  --with-systemd \
  --with-mqtt-client \
  --with-dbus-interface
make -j$(nproc)
sudo make install

# Verify new binary has the flag
shairport-sync -V | grep dbus
```

After `make install`, the D-Bus policy file is installed automatically. Restart both the shairport-sync service and D-Bus daemon, or reboot.

Estimated time: 30–60 minutes on a Pi 4 with a good internet connection.

### Path B: Compile Without AirPlay 2 (DACP Broken on iOS 17.4+)

If PlayPause via `dbus-send` does not work on the iOS device, and the user opts for the recompile route:

```bash
# Same as Path A, but add --without-airplay2 to ./configure
./configure \
  --sysconfdir=/etc \
  --with-alsa \
  --with-avahi \
  --with-ssl=openssl \
  --with-metadata \
  --with-soxr \
  --with-systemd \
  --with-mqtt-client \
  --with-dbus-interface \
  --without-airplay2
```

Without AirPlay 2, DACP operates via the older AirPlay 1 path where Apple still sends the DACP-ID. Remote control commands are then routed correctly and the device responds. **Trade-off:** AirPlay 2 multi-room features are unavailable (not relevant for this single-Pi setup). Audio quality difference is negligible for the use case.

Source: confirmed workaround referenced in Shairport-Sync issue #1822 discussion thread.

### Path C: Accept Volume-Only Control (Fallback)

If compilation is deemed too complex or risky for the current setup, volume control via D-Bus is **not** affected by the DACP/AirPlay 2 problem. The `VolumeUp`, `VolumeDown`, and `ToggleMute` D-Bus methods operate on the local ALSA mixer, not via DACP. Only play, pause, next, and previous are DACP-dependent.

Document this limitation explicitly in Phase 2 if this path is taken.

---

## Code Examples

### Canonical dbus-send PlayPause Command

```bash
# Source: https://github.com/mikebrady/shairport-sync/blob/master/documents/sample%20dbus%20commands
dbus-send --system --print-reply \
  --dest=org.gnome.ShairportSync \
  /org/gnome/ShairportSync \
  org.gnome.ShairportSync.RemoteControl.PlayPause
```

### Canonical dbus-send Volume Check

```bash
# Read current volume (confirms interface is working)
dbus-send --system --print-reply \
  --dest=org.gnome.ShairportSync \
  /org/gnome/ShairportSync \
  org.freedesktop.DBus.Properties.Get \
  string:"org.gnome.ShairportSync" \
  string:"Volume"
```

Returns a double (dB value, -30.0 to 0.0, or -144.0 for mute). This call works regardless of whether an AirPlay session is active — it reads the local mixer state.

### D-Bus Policy File Structure (Correct Form)

```xml
<!-- /etc/dbus-1/system.d/shairport-sync-dbus-policy.conf -->
<!DOCTYPE busconfig PUBLIC
  "-//freedesktop//DTD D-BUS Bus Configuration 1.0//EN"
  "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig>
  <policy user="root">
    <allow own="org.gnome.ShairportSync"/>
  </policy>
  <policy user="shairport-sync">
    <allow own="org.gnome.ShairportSync"/>
  </policy>
  <!-- Add your username here if needed: -->
  <policy user="YOUR_USERNAME">
    <allow send_destination="org.gnome.ShairportSync"/>
  </policy>
  <policy context="default">
    <allow send_destination="org.gnome.ShairportSync"/>
    <allow receive_sender="org.gnome.ShairportSync"/>
  </policy>
</busconfig>
```

Note: If the installed policy already has `<policy context="default">` with `send_destination`, no per-user entry is needed. Check the existing file before adding.

---

## State of the Art

| Old Approach | Current Approach | Impact |
|---|---|---|
| Shairport-Sync built-in MQTT remote (`enable_remote = "yes"`) | Direct D-Bus method calls | Built-in MQTT remote routes via DACP — broken on iOS 17.4+ since April 2024, closed "not planned" |
| AirPlay 2 remote control (DACP via AirPlay 2 session) | Compile `--without-airplay2` to restore AirPlay 1 DACP path | AirPlay 2 dropped DACP-ID from session headers; AirPlay 1 path still works |
| MPRIS interface for control | Native `org.gnome.ShairportSync` D-Bus interface | MPRIS requires separate compile flag, has normalised volume (0–1 not dB), less feature-complete |

**Current status of iOS 17.4+ DACP breakage:** Confirmed permanent as of April 2024. No fix found. Issue #1822 closed "not planned." No evidence of a fix in 2025–2026 update cycle.

---

## Validation Architecture

Phase 1 is a precondition gate. There are no automated tests — the verification is manual, interactive, and hardware-dependent. The "tests" are the `dbus-send` and `mosquitto_sub` commands run live on the Pi.

### Phase Requirements → Verification Map

| Success Criterion | Verification Command | Pass Condition |
|-------------------|---------------------|----------------|
| `busctl list` shows `org.gnome.ShairportSync` | `busctl list \| grep -i shairport` | Non-empty output |
| `dbus-send` PlayPause causes streaming device to pause | `dbus-send ... RemoteControl.PlayPause` during active AirPlay session | Device responds physically |
| `mosquitto_sub` shows button press messages | `mosquitto_sub -t 'shairport-sync/#' -v` while tapping touchscreen | `shairport-sync/remote playpause` appears |
| D-Bus policy grants `send_destination` access without AccessDenied | Same `dbus-send` command as above | No AccessDenied error in output |

### Phase Gate

Phase 2 is unblocked only when all four success criteria above are confirmed. If criteria 1 or 2 fail, the remediation path (A or B above) must be executed and re-verified before proceeding.

---

## Open Questions

1. **Which Shairport-Sync version is installed?**
   - What we know: The user has Shairport-Sync running and the Now Playing display works (MQTT metadata is flowing).
   - What's unclear: Install method (apt vs. compiled), version number, and compile flags.
   - Recommendation: `shairport-sync -V` is the first command to run. Its output resolves the D-Bus question immediately.

2. **What is the exact custom username?**
   - What we know: User does not use the default `pi` username.
   - What's unclear: The actual username used.
   - Recommendation: Ask the user for their username before writing the D-Bus policy fix command. Include a `whoami` step in the verification checklist.

3. **Is the existing Shairport-Sync configured to use system bus or session bus?**
   - What we know: Default is system bus. MQTT is working, which is independent of D-Bus bus choice.
   - What's unclear: Whether a previous operator changed `dbus_service_bus` in shairport-sync.conf.
   - Recommendation: `grep -i dbus /etc/shairport-sync.conf` reveals this in Step 3 of the verification.

4. **Which iOS version and streaming app is the user using?**
   - What we know: User is on iOS 17.4+ which is the high-risk range.
   - What's unclear: Exact iOS version and whether the user streams from Apple Music, Spotify, or another app.
   - Recommendation: Note the iOS version and app in the Phase 1 output. Different apps may behave differently with DACP.

---

## Sources

### Primary (HIGH confidence)
- [Shairport-Sync issue #1822](https://github.com/mikebrady/shairport-sync/issues/1822) — AirPlay 2 DACP broken, iOS 17.4+, closed "not planned" April 2024. Maintainer confirmed permanent.
- [Shairport-Sync sample dbus commands](https://github.com/mikebrady/shairport-sync/blob/master/documents/sample%20dbus%20commands) — canonical service name, object path, interface names, exact dbus-send syntax
- [Shairport-Sync D-Bus policy file](https://github.com/mikebrady/shairport-sync/blob/master/scripts/shairport-sync-dbus-policy.conf) — reference policy file structure; default allows any user via `context="default"`
- [Shairport-Sync CONFIGURATION FLAGS.md](https://github.com/mikebrady/shairport-sync/blob/master/CONFIGURATION%20FLAGS.md) — `--with-dbus-interface` flag confirmed
- [Shairport-Sync BUILD.md](https://github.com/mikebrady/shairport-sync/blob/master/BUILD.md) — Debian/Pi build dependency list
- [Shairport-Sync Discussion #1862](https://github.com/mikebrady/shairport-sync/discussions/1862) — D-Bus session vs system bus, policy file requirements, `make install` handles policy

### Secondary (MEDIUM confidence)
- [Shairport-Sync Issue #730](https://github.com/mikebrady/shairport-sync/issues/730) — D-Bus interface resolved, user permissions in policy file
- [Shairport-Sync Issue #915](https://github.com/mikebrady/shairport-sync/issues/915) — D-Bus service failed to start; compile flag missing
- [Debian manpage: shairport-sync.7](https://manpages.debian.org/testing/shairport-sync/shairport-sync.7.en.html) — `dbus_service_bus` config option, `shairport-sync -V` flag
- [Existing project research: STACK.md, PITFALLS.md, ARCHITECTURE.md, FEATURES.md, SUMMARY.md](.planning/research/) — pre-roadmap research with HIGH confidence ratings; synthesised here

### Tertiary (LOW confidence — device-specific, must verify on hardware)
- AirPlay 2 DACP behaviour on the user's specific iOS version and streaming app — confirmed broken in general; exact device outcome requires live testing

---

## Metadata

**Confidence breakdown:**
- Verification commands: HIGH — all commands drawn from official Shairport-Sync documentation and official D-Bus tooling
- AirPlay 2 DACP status: HIGH — confirmed permanent by maintainer April 2024; no fix found as of 2026-03-29
- Source compilation path: MEDIUM — build dependencies from official BUILD.md, but exact Pi Bookworm behaviour may vary by installed package state
- D-Bus policy structure: HIGH — drawn directly from official policy file in Shairport-Sync repository

**Research date:** 2026-03-29
**Valid until:** 2026-06-29 (stable domain; unlikely to change unless Apple ships AirPlay protocol update or Shairport-Sync maintainer finds DACP fix)
