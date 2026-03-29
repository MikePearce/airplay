# Phase 1: Environment Verification - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Confirm that D-Bus interface exists, is accessible from the user's account, and actually controls AirPlay playback on the real Pi. Verify MQTT message flow from the touchscreen frontend. No code is written in this phase — it's a hardware/software verification gate that unblocks Phase 2.

</domain>

<decisions>
## Implementation Decisions

### AirPlay 2 fallback strategy
- User is on iOS 17.4+ (high risk for DACP breakage) and AirPlays from multiple Apple devices
- Strategy: test first, decide later — run D-Bus PlayPause during an active AirPlay session and observe
- If playback commands are broken: user is open to recompiling Shairport-Sync from source IF the effort is reasonable
- If recompilation is too complex: accept volume-only control as a fallback

### D-Bus access setup
- Shairport-Sync install method unknown — may be apt or compiled. Verification must check both D-Bus interface presence and compile flags
- User runs a custom Pi username (not default `pi`) — D-Bus policy file must grant access to that specific user
- MQTT is confirmed working (Now Playing display functions) but D-Bus enablement is unknown — needs checking in /etc/shairport-sync.conf
- User accesses Pi via both SSH and direct keyboard

### Verification approach
- Claude's discretion on format (script vs step-by-step guide)
- User will paste terminal output back into the chat for analysis
- Verification should cover the full MQTT→D-Bus→playback chain, not just isolated D-Bus commands

### MQTT configuration
- Mosquitto WebSocket on port 9001 (confirmed)
- Default topic prefix: `shairport-sync` (confirmed)
- No authentication required (anonymous connections)
- Standard MQTT port 1883 for non-WebSocket connections (bridge will use this)

### Claude's Discretion
- Whether to produce a verification script or a step-by-step document
- Scope of end-to-end testing (full chain vs. component-by-component)
- How to structure the D-Bus policy file fix if needed

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `nowplaying.html`: Frontend already publishes six commands (`playpause`, `nextitem`, `previtem`, `mutetoggle`, `volumeup`, `volumedown`) to `shairport-sync/remote` topic — this is the contract the bridge must honor

### Established Patterns
- MQTT over WebSocket on port 9001 for frontend
- MQTT on standard port 1883 for backend services (bridge will use this)
- Topic structure: `shairport-sync/{subtopic}` for all Shairport-Sync data

### Integration Points
- Bridge subscribes to `shairport-sync/remote` (same topic frontend publishes to)
- Bridge calls D-Bus on `org.gnome.ShairportSync.RemoteControl` interface

</code_context>

<specifics>
## Specific Ideas

No specific requirements — verification is about discovering what works on the real hardware.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-environment-verification*
*Context gathered: 2026-03-29*
