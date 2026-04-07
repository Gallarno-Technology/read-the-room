# Quick Task 260406-sut Summary

**Task:** create a Claude Code hook to execute make restart after every execute phase
**Date:** 2026-04-07
**Status:** complete

## What was done

Added a PostToolUse hook that automatically runs `make restart` after any gsd-executor completes.

### Files changed

- **`.claude/hooks/gsd-restart-on-execute.js`** (created) — Hook script that detects executor completion via "PLAN COMPLETE" in the Agent tool response, then runs `make restart` in the project directory. Silent fail if docker isn't running.
- **`.claude/settings.json`** (modified) — Added new PostToolUse hook entry matching `Agent|Task` tools with 130s timeout (generous for docker rebuild time).

## How it works

1. After every `Agent` or `Task` tool call completes, Claude Code runs the hook script
2. The script checks `tool_response` for "PLAN COMPLETE" — the standard completion marker emitted by gsd-executor
3. If found, runs `make restart` (`docker compose down && docker compose up -d --build`)
4. Silently exits 0 on any failure (docker not running, make errors, etc.) — never blocks Claude

## Detection logic

- Matches: execute-phase executors, gsd:quick executors (both emit "PLAN COMPLETE")
- Does not match: planners, checkers, verifiers, research agents (none emit "PLAN COMPLETE")
