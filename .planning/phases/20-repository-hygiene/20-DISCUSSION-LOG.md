# Phase 20: Repository Hygiene - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-08
**Phase:** 20-repository-hygiene
**Areas discussed:** Docstring rename format, .dockerignore scope, User-agent string

---

## Docstring Rename Format

| Option | Description | Selected |
|--------|-------------|----------|
| Read the Room — Core Daemon | Drop stale "(Phase N)" annotation | ✓ |
| Read the Room — Core Daemon (Phase 1) | Keep phase annotation, swap name only | |
| Read the Room. | Minimal one-liner | |

**User's choice:** "Read the Room — Core Daemon" (drop the Phase N annotation)
**Notes:** The "(Phase N)" suffix is a stale implementation detail not appropriate for published code.

---

## .dockerignore Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Comprehensive | .env, token_cache/, state.json, data/, lyrics_cache.db, __pycache__, *.pyc, .git, .claude/, .planning/, tests/ | ✓ |
| Minimum required | Only .env and token_cache/ | |

**User's choice:** Comprehensive
**Notes:** Standard open-source Docker best practice — keep Docker build context lean.

---

## User-Agent String

| Option | Description | Selected |
|--------|-------------|----------|
| ReadTheRoom/1.0 | CamelCase, standard HTTP user-agent format | ✓ |
| read-the-room/1.0 | Kebab-case alternative | |

**User's choice:** ReadTheRoom/1.0
**Notes:** Direct camelCase equivalent of the display name.

---

## Claude's Discretion

- Exact comment wording for UID/GID/EVENTS_PATH in .env.example
- Ordering of new .env.example entries
- Complete enumeration of .dockerignore entries beyond mandated minimum

## Deferred Ideas

None.
