# Retry/Backoff Prototype

I built this as a Day 1 sprint prototype to get hands-on with exponential backoff — something I'd read about but never actually implemented from scratch.

The idea is simple: you have a server that fails a lot, and instead of hammering it with retries immediately, the client waits a bit longer each time before trying again. That's the core of it.

## What's in here

`server.py` is a small Flask server I rigged to randomly throw 500 errors about 60% of the time. It's just there to give the client something unreliable to talk to.

`client.py` is where the actual work is. It POSTs to the server and if it gets a failure back, it waits, then tries again. Each wait is roughly double the previous one, plus a small random amount so retries don't all pile up at the same moment.

The formula I ended up using:

```
delay = min(base_delay * 2^attempt, max_delay) + random jitter
```

So in practice it looks something like:

- Attempt 1 fails → wait ~1.4s
- Attempt 2 fails → wait ~2.9s
- Attempt 3 fails → wait ~5.6s
- ... and so on up to a 30s cap

## Getting it running

Install the two dependencies:

```bash
pip install flask requests
```

Then open two terminals. In the first one, start the server:

```bash
python server.py
```

In the second one, run the client:

```bash
python client.py
```

You'll see it fail a few times and then eventually get through. If you want to watch it exhaust all retries, open `server.py` and set `FAILURE_RATE = 1.0`.

## What I learned

The jitter part surprised me — I originally skipped it and couldn't figure out why it mattered until I read about the thundering herd problem. If you have 50 clients all backing off for exactly 4 seconds and retrying at the same time, you've just recreated the exact spike that crashed the server. The random offset breaks that up.

The max delay cap also matters more than I expected. Without it, after enough failures you're waiting 512 seconds between retries, which is obviously useless in practice.
