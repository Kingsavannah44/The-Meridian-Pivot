import uuid
import threading
from flask import Flask, jsonify, request

app = Flask(__name__)

jobs = {}
jobs_lock = threading.Lock()

_job_ready_callbacks = []


def on_job_queued(fn):
    _job_ready_callbacks.append(fn)
    return fn


@app.route("/print-job", methods=["POST"])
def enqueue_job():
    body = request.get_json(silent=True) or {}

    badge_id = body.get("badge_id")
    if not badge_id:
        return jsonify({"error": "badge_id is required"}), 400

    with jobs_lock:
        for job in jobs.values():
            if job["badge_id"] == badge_id and job["status"] in ("queued", "processing"):
                return jsonify({
                    "error": "duplicate",
                    "message": f"Badge {badge_id} already has an active print job",
                    "job_id": job["job_id"]
                }), 409

        job_id = str(uuid.uuid4())
        jobs[job_id] = {
            "job_id": job_id,
            "badge_id": badge_id,
            "attendee": body.get("attendee", "Unknown"),
            "status": "queued"
        }

    print(f"  [queue] Job {job_id[:8]} queued for badge {badge_id}")

    for cb in _job_ready_callbacks:
        threading.Thread(target=cb, args=(job_id,), daemon=True).start()

    return jsonify({"job_id": job_id, "status": "queued"}), 202


@app.route("/job/<job_id>", methods=["GET"])
def get_job(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "not found"}), 404
    return jsonify(job), 200


def get_job_data(job_id):
    with jobs_lock:
        return jobs.get(job_id)


def update_job_status(job_id, status):
    with jobs_lock:
        if job_id in jobs:
            jobs[job_id]["status"] = status


if __name__ == "__main__":
    print("Queue server starting on http://localhost:5001")
    app.run(port=5001, debug=False)
