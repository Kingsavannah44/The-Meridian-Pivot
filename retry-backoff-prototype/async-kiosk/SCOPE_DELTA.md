# Scope Delta Analysis — Day 4 Pivot

## Context

The vendor deprecated the synchronous REST API for badge printing. The kiosk service now publishes print requests to a message queue and receives job completion status via webhook callback instead of waiting for a synchronous response.

---

## Removed

- Synchronous `POST /print` call that blocked until the badge was printed
- Immediate "Checked In" state set on HTTP 200 response
- Single-request duplicate check based on response timing

---

## Added

- `queue_server.py` — accepts print jobs via `POST /print-job`, returns a `job_id` immediately with HTTP 202. Holds active job state and blocks duplicate badge submissions at the queue level.
- `print_worker.py` — background worker that simulates the vendor print process. Fires a webhook to the kiosk on completion or failure.
- `webhook_receiver.py` — Flask endpoint on port 5002 that receives job confirmations. Deduplicates out-of-order or repeated webhook deliveries using an in-memory confirmed jobs map.
- `kiosk.py` — orchestrates all three services. Manages per-badge UI state machine: `Pending...` → `Checked In` or `Print Failed` or `Timeout`.
- Async duplicate-scan protection at two layers: kiosk-side `seen_badges` set (blocks re-scan before job is even queued) and queue-server-side active job check (catches race conditions if two scans arrive simultaneously).

---

## Modified

- UI state model: previously binary (success/fail on sync response). Now a three-state flow — `Not Scanned` → `Pending...` → `Checked In / Print Failed / Timeout`.
- Duplicate protection: previously relied on synchronous response timing. Now enforced independently of job completion, so out-of-order webhook arrivals cannot bypass it.

---

## Trade-offs Accepted for Prototype

- In-memory state only — no persistence across restarts
- Single-process threading instead of a real message broker (RabbitMQ, Redis Streams, etc.)
- Webhook target is localhost — in production this would be a public HTTPS endpoint with HMAC signature verification
