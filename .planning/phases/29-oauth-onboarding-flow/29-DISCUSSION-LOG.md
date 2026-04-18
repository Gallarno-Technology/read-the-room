# Phase 29: OAuth Onboarding Flow - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-18
**Phase:** 29-oauth-onboarding-flow
**Areas discussed:** Callback response UX

---

## Callback response UX

### On success

| Option | Description | Selected |
|--------|-------------|----------|
| Redirect to / (Recommended) | HTTP 302 to / with uid cookie set | ✓ |
| Redirect to a welcome page | Redirect to /welcome before dashboard | |
| Return dashboard HTML directly | Serve dashboard HTML inline on callback | |

**User's choice:** Redirect to / (Recommended)
**Notes:** Simplest; matches AUTH-04; browser lands on dashboard immediately.

### On failure

| Option | Description | Selected |
|--------|-------------|----------|
| Plain HTML error page (Recommended) | 400/500 with human-readable error + operator contact note | ✓ |
| JSON error | Return JSON {"error": "..."} | |
| Redirect to a fixed error URL | Redirect to /auth/error?reason=... | |

**User's choice:** Plain HTML error page (Recommended)
**Notes:** User came from a browser; human-readable is the right call.

---

## Claude's Discretion

- State validation approach (in-memory pending map vs. check users.json status=pending)
- Daemon spawn scope for Phase 29 (minimal inline asyncio.create_subprocess_exec)
- Cookie attributes (HttpOnly + SameSite=Lax; Secure deferred to Phase 31)
- HTML error page styling

## Deferred Ideas

- In-memory pending-auth map (CSRF protection) — not needed for 5-user manual workflow
- Secure cookie flag — Phase 31
- Error page styling beyond minimal HTML — Phase 32
