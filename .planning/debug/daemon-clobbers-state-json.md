---
status: investigating
trigger: "daemon overwrites state.json on every track change, wiping the family_safe_mode key set by make fsm-on"
created: 2026-04-01T00:00:00Z
updated: 2026-04-01T00:00:00Z
---

## Current Focus

hypothesis: daemon.py calls save_state(state) where `state` is the dict loaded at startup — it never re-reads state.json before writing, so any key written externally (e.g. family_safe_mode) after startup is lost on the next save_state call
test: trace save_state call sites and what `state` dict contains at each call
expecting: confirmed — the in-memory `state` dict is missing family_safe_mode because it was set after load_state() ran
next_action: document findings

## Symptoms

expected: family_safe_mode=True persists in state.json across track changes
actual: state.json is overwritten on each track change, family_safe_mode key is gone
errors: (none — silent data loss)
reproduction: run make fsm-on, then wait for a track change; cat state.json — family_safe_mode is absent
started: always broken (Phase 2 FSM feature, state never persisted correctly across daemon writes)

## Eliminated

(none)

## Evidence

- timestamp: 2026-04-01T00:00:00Z
  checked: daemon.py load_state() line 59-65
  found: load_state() reads state.json once at poll_loop startup (line 89); returns {"last_track_id": None} as default
  implication: the in-memory `state` dict is a snapshot from startup; any external writes to state.json after that point are invisible to the daemon

- timestamp: 2026-04-01T00:00:00Z
  checked: daemon.py save_state() line 68-76
  found: save_state() does a full json.dump of whatever dict is passed — no read-merge step
  implication: writing the in-memory dict back to disk destroys any keys that exist on disk but are absent from the in-memory dict

- timestamp: 2026-04-01T00:00:00Z
  checked: daemon.py poll_loop() line 122-123
  found: on track change, code sets state["last_track_id"] = track_id then calls save_state(state); `state` is the dict from line 89 which never had family_safe_mode loaded into it (it was set externally after startup)
  implication: this is the clobber site — line 123 save_state(state) overwrites state.json with the stale in-memory dict

- timestamp: 2026-04-01T00:00:00Z
  checked: daemon.py line 128 — state.get("family_safe_mode", False)
  found: this reads from the same stale in-memory dict, not from disk; so FSM check always returns False
  implication: double failure — not only is the key wiped from disk, the daemon never even sees it after it is set

- timestamp: 2026-04-01T00:00:00Z
  checked: Makefile fsm-on (line 32)
  found: fsm-on correctly does read-merge-write — loads state.json, sets family_safe_mode=True, dumps back; preserves other keys
  implication: the Makefile side is correct; the bug is entirely in the daemon's save path

## Resolution

root_cause: |
  daemon.py loads state.json once at startup into an in-memory dict (line 89). On every track
  change it writes that same in-memory dict back to disk via save_state(state) (line 123) without
  first re-reading state.json. Any key written to state.json after the daemon started — specifically
  family_safe_mode set by `make fsm-on` — is absent from the in-memory dict and is therefore
  silently discarded on the next save. There is only one save_state call site (line 123), so there
  is only one clobber site.

fix: |
  In save_state(), or at the call site before save_state(), re-read the current state.json from
  disk, merge the daemon's fields on top (so disk-side keys like family_safe_mode are preserved),
  then write the merged dict. Concretely:

    def save_state(state: dict) -> None:
        try:
            with open(STATE_PATH) as f:
                on_disk = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            on_disk = {}
        on_disk.update(state)          # daemon fields win on conflict
        with open(STATE_PATH, "w") as f:
            json.dump(on_disk, f)

  Additionally, the FSM check at line 128 should read from disk (or re-load state each poll cycle)
  so the daemon picks up the flag within one poll interval as intended by the D-06 comment.
  The simplest fix for the FSM read is to re-read state.json at the top of the track-change block
  instead of relying on the stale in-memory dict.

verification: ""
files_changed:
  - daemon.py
