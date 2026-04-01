# Signal Notifications Research

**Domain:** Signal bot notifications and interactive messaging for background services
**Researched:** 2026-04-01
**Overall confidence:** MEDIUM (core patterns HIGH; reliability specifics LOW — Signal's unofficial API changes without notice)

---

## Executive Summary

Signal does not have an official bot API. All programmatic access flows through **signal-cli** (AsamK), an unofficial but widely-used Java CLI that reverse-engineers the Signal protocol. The practical deployment stack for a background Node.js or Python service is:

1. `bbernhard/signal-cli-rest-api` — a Dockerized HTTP/WebSocket wrapper around signal-cli
2. Your service calls the REST API to send messages and maintains a WebSocket to receive replies

This approach works well for personal/homelab scale (one user, low message volume). The interactive reply pattern (send a question, receive a "yes"/"no" reply) is fully supported via WebSocket.

For projects where Signal's setup complexity is unacceptable, **ntfy.sh** is the strongest alternative: it supports action buttons that POST back to your server, covering the "skip / allow" confirmation use case without a dedicated phone number or Docker daemon.

---

## 1. Signal Bot Landscape

### signal-cli (AsamK)
- **What it is:** Unofficial Java CLI that speaks the Signal protocol directly. The authoritative base for all Signal bots.
- **GitHub:** https://github.com/AsamK/signal-cli
- **Interfaces:** Command-line, JSON-RPC daemon, DBus daemon
- **Confidence:** HIGH — actively maintained, 3.2k+ stars, used as the foundation for all other tools

### bbernhard/signal-cli-rest-api (RECOMMENDED)
- **What it is:** Dockerized HTTP + WebSocket REST API wrapping signal-cli. By far the most practical integration point for any language.
- **GitHub:** https://github.com/bbernhard/signal-cli-rest-api
- **API docs:** https://bbernhard.github.io/signal-cli-rest-api/
- **Confidence:** HIGH — widely deployed, Home Assistant integration, active maintenance

### filipre/signalbot (Python framework)
- **What it is:** High-level Python package (`pip install signalbot`) that wraps signal-cli-rest-api. Provides command registration, async handlers, WebSocket receive loop.
- **PyPI:** https://pypi.org/project/signalbot/
- **Confidence:** MEDIUM — useful for Python services, but adds abstraction that may complicate debugging

### node-signal-client
- **What it is:** Node.js Signal client library.
- **GitHub:** https://github.com/matrix-hacks/node-signal-client
- **Confidence:** LOW — appears unmaintained; do not use. Prefer calling signal-cli-rest-api over HTTP from Node.js directly.

### DBus approach (legacy)
- Uses signal-cli in daemon mode with system DBus. Works but requires Linux with DBus, complex to configure, and the primary guides are from 2021-2022. Skip this in favor of the REST API.

---

## 2. Recommended Stack: signal-cli-rest-api

### Architecture for this project

```
Spotify Filter Service (Node.js or Python)
         |
         | HTTP POST  (send message/notification)
         | WebSocket  (receive user replies)
         v
signal-cli-rest-api (Docker, port 8080)
         |
         v
Signal Infrastructure (AsamK signal-cli)
         |
         v
User's Signal app (phone/desktop)
```

### docker-compose.yml

```yaml
version: "3"
services:
  signal-api:
    container_name: signal-api
    image: bbernhard/signal-cli-rest-api:latest
    restart: always
    ports:
      - "8080:8080"
    environment:
      # json-rpc mode: 3x faster, WebSocket /v1/receive becomes streaming (not polling)
      MODE: "json-rpc"
      # Optional: auto-pull messages on a schedule (not needed if using WebSocket)
      # AUTO_RECEIVE_SCHEDULE: "0 22 * * *"
    volumes:
      - "./signal-cli-config:/home/.local/share/signal-cli"
```

**Important:** In `json-rpc` mode, `/v1/receive` becomes a WebSocket endpoint (not HTTP GET). This is the correct mode for a bot that needs real-time message receipt. Do NOT mix `AUTO_RECEIVE_SCHEDULE` with active WebSocket receive — they conflict.

---

## 3. Setup Requirements (User-Facing)

### Option A: Link to existing Signal account (RECOMMENDED for this use case)

The user already has Signal on their phone. Link signal-cli as a secondary device — no new phone number needed, no disruption to existing account.

```bash
# 1. Start the container
docker compose up -d

# 2. Get the QR code link
curl http://localhost:8080/v1/qrcodelink?device_name=SpotifyBot

# Or open in browser: http://localhost:8080/v1/qrcodelink?device_name=SpotifyBot
# This displays a QR code image

# 3. On the user's phone: Signal Settings > Linked Devices > Add Device > Scan QR code

# 4. Verify it works
curl -X POST http://localhost:8080/v2/send \
  -H "Content-Type: application/json" \
  -d '{"message":"Bot connected!", "number":"+1USERPHONE", "recipients":["+1USERPHONE"]}'
```

The bot will now send messages TO the user's own number — they appear as messages from themselves (from the linked device). This is intentional and is the standard homelab pattern.

### Option B: Dedicated bot number

Register a separate phone number (VoIP ok; Google Voice works). This is cleaner semantically but requires maintaining a second number. Registration flow:

```bash
# Register (may need captcha — see gotchas)
signal-cli -u +1BOTNUMBER register

# Verify with SMS code
signal-cli -u +1BOTNUMBER verify 123456
```

**WARNING:** Registering a number via signal-cli will deactivate Signal on the phone that owns that number. Use a dedicated SIM or VoIP number, not your personal number.

---

## 4. Sending Notifications (Node.js)

The signal-cli-rest-api is plain HTTP. No special library needed from Node.js.

### Send a message

```javascript
// notify.js
const SIGNAL_API = 'http://localhost:8080';
const SENDER    = '+1YOURNUMBER';   // number registered/linked with signal-cli
const RECIPIENT = '+1USERNUMBER';   // who receives the message

async function sendSignalMessage(text) {
  const response = await fetch(`${SIGNAL_API}/v2/send`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: text,
      number: SENDER,
      recipients: [RECIPIENT],
    }),
  });
  if (!response.ok) {
    throw new Error(`Signal send failed: ${response.status} ${await response.text()}`);
  }
  return response.json();
}

// Usage:
await sendSignalMessage('Skipping "WAP" by Cardi B — explicit content detected.');
await sendSignalMessage(
  'Ambiguous song: "Shape of You" by Ed Sheeran. Allow or skip? Reply ALLOW or SKIP'
);
```

### Equivalent Python

```python
import httpx   # or requests

SIGNAL_API = "http://localhost:8080"
SENDER     = "+1YOURNUMBER"
RECIPIENT  = "+1USERNUMBER"

def send_signal_message(text: str) -> dict:
    r = httpx.post(f"{SIGNAL_API}/v2/send", json={
        "message": text,
        "number": SENDER,
        "recipients": [RECIPIENT],
    })
    r.raise_for_status()
    return r.json()
```

---

## 5. Receiving Replies (Interactive Bot Pattern)

### WebSocket receive (json-rpc mode)

In `json-rpc` mode the `/v1/receive/{number}` endpoint is a WebSocket. Connect once at startup and stream all incoming messages.

```javascript
// receive.js
import WebSocket from 'ws';  // npm install ws

const SIGNAL_API = 'http://localhost:8080';
const SENDER     = '+1YOURNUMBER';

function startReceiveLoop(onMessage) {
  const ws = new WebSocket(
    `ws://localhost:8080/v1/receive/${encodeURIComponent(SENDER)}`
  );

  ws.on('message', (data) => {
    const event = JSON.parse(data.toString());
    
    // Filter out delivery receipts, typing indicators, etc.
    const msg = event?.envelope?.dataMessage;
    if (!msg?.message) return;

    const from   = event.envelope.sourceNumber;
    const text   = msg.message.trim().toLowerCase();
    onMessage({ from, text, raw: event });
  });

  ws.on('close', () => {
    // Reconnect after a brief delay
    setTimeout(() => startReceiveLoop(onMessage), 5000);
  });

  ws.on('error', (err) => {
    console.error('Signal WebSocket error:', err.message);
  });
}

// Usage
startReceiveLoop(({ from, text }) => {
  if (text === 'allow') handleAllow(from);
  else if (text === 'skip') handleSkip(from);
  else if (text === 'change') handlePlaylistChange(from);
});
```

### Stateful confirmation pattern

For the ambiguous-song confirmation use case, maintain a pending-prompt map:

```javascript
const pendingConfirmations = new Map();
// key: userPhoneNumber, value: { songId, resolve, reject, timer }

async function askUserToConfirm(userNumber, songInfo) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      pendingConfirmations.delete(userNumber);
      resolve('timeout');  // default action on no reply
    }, 30_000);  // 30 second timeout

    pendingConfirmations.set(userNumber, { songInfo, resolve, timer });

    sendSignalMessage(
      `Ambiguous track: "${songInfo.title}" by ${songInfo.artist}.\n` +
      `Reply ALLOW to play it or SKIP to skip.`
    );
  });
}

// In your message handler:
startReceiveLoop(({ from, text }) => {
  const pending = pendingConfirmations.get(from);
  if (pending && (text === 'allow' || text === 'skip')) {
    clearTimeout(pending.timer);
    pendingConfirmations.delete(from);
    pending.resolve(text);
  }
});

// In your filter service:
const decision = await askUserToConfirm(USER_NUMBER, { title: 'WAP', artist: 'Cardi B' });
// decision === 'allow' | 'skip' | 'timeout'
```

### Python equivalent (asyncio)

```python
import asyncio
import json
import websockets

SENDER = "+1YOURNUMBER"
pending: dict[str, asyncio.Future] = {}

async def receive_loop():
    uri = f"ws://localhost:8080/v1/receive/{SENDER}"
    async with websockets.connect(uri) as ws:
        async for raw in ws:
            event = json.loads(raw)
            msg = event.get("envelope", {}).get("dataMessage", {})
            text = msg.get("message", "").strip().lower()
            source = event["envelope"]["sourceNumber"]

            if source in pending and text in ("allow", "skip"):
                future = pending.pop(source)
                if not future.done():
                    future.set_result(text)

async def ask_user(user_number: str, song_title: str) -> str:
    loop = asyncio.get_event_loop()
    future = loop.create_future()
    pending[user_number] = future

    send_signal_message(f'Allow or skip "{song_title}"? Reply ALLOW or SKIP')

    try:
        return await asyncio.wait_for(future, timeout=30.0)
    except asyncio.TimeoutError:
        pending.pop(user_number, None)
        return "timeout"
```

---

## 6. Reliable Receive in Non-json-rpc Mode (Polling Fallback)

If using `MODE=normal` or `MODE=native`, `/v1/receive` is an HTTP GET endpoint (not WebSocket). Poll it:

```javascript
// Poll every 3 seconds (not recommended — prefer json-rpc + WebSocket)
setInterval(async () => {
  const res = await fetch(`${SIGNAL_API}/v1/receive/${SENDER}`);
  const messages = await res.json();
  for (const envelope of messages) {
    // same processing as above
  }
}, 3000);
```

Drawbacks: 3+ second reply latency, and calling receive "fetches all messages from Signal Server" which can conflict with the container's AUTO_RECEIVE_SCHEDULE. Stick with `json-rpc` mode.

---

## 7. Reliability and Known Issues

### Rate Limiting (CRITICAL — HIGH confidence)

Signal imposes server-side rate limits on signal-cli. Multiple open GitHub issues (2023–2026) confirm:

- **Registration:** Frequently hit 429 / 413 "Rate limit exceeded" errors. Requires CAPTCHA token from `https://signalcaptchas.org/registration/generate.html` in many cases.
- **Message sending:** Previously ~1 msg/sec was safe. Current reports show rate limits triggered at even 1 msg/10 sec in some accounts.
- **For this use case (low volume, personal use):** Rate limits are unlikely to be a problem. A family music service sending a few notifications per hour is far below any realistic threshold.

**Mitigation:** Never burst-send messages. Space notifications at least 2 seconds apart. Do not send to large groups.

### Unofficial protocol (MEDIUM risk)

signal-cli reverse-engineers the Signal protocol. Signal has previously broken compatibility with third-party clients. The project maintainer keeps up with protocol changes, but there is no SLA.

- Signal blocked old signal-cli versions in the past (sealed sender, profile keys)
- Most breakages are fixed within days/weeks
- For personal use this is an acceptable risk

### Delivery guarantees (MEDIUM confidence)

Signal does not provide delivery receipts at the API level in the way email does. signal-cli surfaces read receipts and delivery receipts as events on the WebSocket, but:
- If the user's phone is offline, messages queue on Signal's servers
- No persistent queue on the signal-cli side
- A message sent just before a container restart could be lost

**Mitigation for confirmations:** Always use a timeout. If no reply within 30 seconds, apply a safe default (e.g., skip the ambiguous song) and log it.

### Container restarts and registration state (LOW risk for this project)

Signal-cli stores cryptographic keys in the config volume. If that volume is lost, re-registration is required. Use a named volume or bind mount. Never use an ephemeral container volume.

### Latency

- `json-rpc` mode: message sending latency < 200ms typical
- `normal` mode: 500ms–2s per message (JVM startup per request)
- WebSocket receive: near real-time (~100ms once connected)
- Polling receive: up to polling interval (3–10 seconds)

Use `json-rpc` mode for this project.

---

## 8. Alternative: ntfy.sh (Simpler but One-Way by Default)

If Signal setup complexity is a blocker, ntfy.sh is a strong fallback.

### What it is

HTTP pub-sub notification service. Free hosted at ntfy.sh or self-hostable. Mobile apps for iOS/Android. No phone number required.

### Sending from Node.js

```javascript
// Zero dependencies — plain HTTP
async function sendNtfy(message, title = 'Spotify Filter') {
  await fetch('https://ntfy.sh/your-secret-topic-name', {
    method: 'POST',
    headers: {
      'Title': title,
      'Priority': 'default',
      'Content-Type': 'text/plain',
    },
    body: message,
  });
}
```

### Interactive "action buttons" (covers skip/allow use case)

ntfy supports HTTP action buttons. When the user taps the button in the mobile notification, ntfy sends an HTTP POST to your configured endpoint:

```javascript
async function askNtfyConfirmation(song) {
  await fetch('https://ntfy.sh/your-secret-topic', {
    method: 'POST',
    headers: {
      'Title': `Allow or skip: "${song.title}"?`,
      'Actions': [
        'http, Allow, https://your-service.local/confirm?action=allow&song=' + song.id + ', method=POST',
        'http, Skip,  https://your-service.local/confirm?action=skip&song='  + song.id + ', method=POST',
      ].join('; '),
      'Content-Type': 'text/plain',
    },
    body: `"${song.title}" by ${song.artist} — explicit content flagged.`,
  });
}
```

Your service needs an HTTP endpoint reachable from the ntfy server (or use ngrok / Tailscale for LAN services). The user taps Allow or Skip in the notification, ntfy POSTs to your endpoint.

### ntfy limitations vs Signal

| Concern | Signal (signal-cli) | ntfy.sh |
|---------|---------------------|---------|
| Free reply text | Yes (user types anything) | No — only predefined button actions |
| No extra infrastructure | No (Docker required) | Yes (just HTTP) |
| User already has app | Yes (Signal) | Requires ntfy app install |
| Self-hostable | Via signal-cli-rest-api | Yes, easy Docker |
| Rate limits | Signal server-imposed | Generous for personal use |
| Interactive confirmations | Full (free-text reply) | Limited (button actions only) |

**Use ntfy if:** The user doesn't want to link a Signal device, or you need the simplest possible integration.
**Use Signal if:** The user is already on Signal and wants notifications in their existing app without installing anything new.

---

## 9. Alternative: Pushover

One-time $5 purchase per platform. Simple HTTP API, no self-hosting, official iOS/Android apps with reliable delivery.

```javascript
await fetch('https://api.pushover.net/1/messages.json', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    token: 'YOUR_APP_TOKEN',
    user:  'USER_KEY',
    message: 'Skipping explicit track...',
    title: 'Spotify Filter',
  }),
});
```

Does NOT support interactive replies. Only sends push notifications. No "ALLOW / SKIP" reply pattern without building a separate mechanism. Rule out for this use case unless one-way notifications are sufficient.

---

## 10. Recommendation

**Primary: Signal via signal-cli-rest-api** (the user already has Signal and a bot account set up)

Setup checklist:
1. Add `signal-api` service to docker-compose with `MODE=json-rpc`
2. Mount a persistent volume for signal-cli config
3. Link as secondary device via QR code (one-time, ~2 minutes)
4. Send messages via HTTP POST to `/v2/send`
5. Receive replies via WebSocket at `ws://localhost:8080/v1/receive/{number}`
6. Implement pending-confirmation map with 30-second timeout for ambiguous tracks
7. Never burst-send; space notifications >= 2 seconds

**Fallback: ntfy.sh** — if Signal proves unreliable or setup is blocked, switch to ntfy with HTTP action buttons. Requires the user installs the ntfy app, but covers the allow/skip confirmation pattern.

Do not use: Pushover (no interactive replies), node-signal-client (unmaintained), DBus approach (unnecessary complexity).

---

## 11. Minimum Working Integration Checklist

- [ ] Docker installed on the host machine running the filter service
- [ ] `bbernhard/signal-cli-rest-api` container running in `json-rpc` mode
- [ ] Persistent volume for `/home/.local/share/signal-cli`
- [ ] Bot linked as secondary device to user's existing Signal account (QR scan, one-time)
- [ ] Service can POST to `http://localhost:8080/v2/send`
- [ ] Service maintains WebSocket connection to `ws://localhost:8080/v1/receive/{number}`
- [ ] Pending-confirmation map with timeout implemented
- [ ] Error handling: reconnect WebSocket on close, catch HTTP errors from send

---

## Sources

- [bbernhard/signal-cli-rest-api — GitHub](https://github.com/bbernhard/signal-cli-rest-api)
- [signal-cli-rest-api API documentation](https://bbernhard.github.io/signal-cli-rest-api/)
- [AsamK/signal-cli — GitHub](https://github.com/AsamK/signal-cli)
- [signalbot — PyPI](https://pypi.org/project/signalbot/)
- [filipre/signalbot-example — GitHub](https://github.com/filipre/signalbot-example)
- [signal-cli-rest-api EXAMPLES.md](https://github.com/bbernhard/signal-cli-rest-api/blob/master/doc/EXAMPLES.md)
- [libe.net Signal API guide](https://www.libe.net/en/signal-api)
- [Signal-cli rate limit issues (GitHub)](https://github.com/AsamK/signal-cli/issues/1823)
- [ntfy.sh — Push notifications via PUT/POST](https://ntfy.sh/)
- [ntfy publishing docs (actions)](https://docs.ntfy.sh/publish/)
- [Fabio Barbero — How to make a Signal bot in Python](https://fabiobarbero.eu/posts/signalbot/)
- [Signal-cli WebSocket / JSON-RPC discussion](https://github.com/AsamK/signal-cli/discussions/679)
- [signal-api-receiver — WebSocket to REST bridge](https://github.com/kalbasit/signal-api-receiver)
