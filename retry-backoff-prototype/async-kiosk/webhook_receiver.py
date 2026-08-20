import threading
from flask import Flask, jsonify, request

app = Flask(__name__)

confirmed_jobs = {}
confirmed_lock = threading.Lock()

_confirmation_callbacks = []


def on_confirmation(fn):
    _confirmation_callbacks.append(fn)
    return fn


@app.route("/webhook", methods=["POST"])
def receive_webhook():
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "empty payload"}), 400

    job_id = body.get("job_id")
    badge_id = body.get("badge_id")
    status = body.get("status")

    if not all([job_id, badge_id, status]):
        return jsonify({"error": "missing fields"}), 400

    with confirmed_lock:
        if job_id in confirmed_jobs:
            print(f"  [webhook] Duplicate confirmation for job {job_id[:8]}, ignoring")
            return jsonify({"status": "already processed"}), 200

        confirmed_jobs[job_id] = {
            "job_id": job_id,
            "badge_id": badge_id,
            "attendee": body.get("attendee", "Unknown"),
            "status": status
        }

    print(f"  [webhook] Confirmation received — job {job_id[:8]} | badge {badge_id} | {status}")

    for cb in _confirmation_callbacks:
        threading.Thread(target=cb, args=(job_id, badge_id, status), daemon=True).start()

    return jsonify({"received": True}), 200


def is_confirmed(job_id):
    with confirmed_lock:
        return job_id in confirmed_jobs


def get_confirmation(job_id):
    with confirmed_lock:
        return confirmed_jobs.get(job_id)


if __name__ == "__main__":
    print("Webhook receiver starting on http://localhost:5002")
    app.run(port=5002, debug=False)
