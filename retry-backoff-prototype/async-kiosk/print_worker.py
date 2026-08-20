import time
import random
import requests
import threading
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import queue_server as qs

WEBHOOK_URL = "http://localhost:5002/webhook"

PRINT_MIN_SECONDS = 2
PRINT_MAX_SECONDS = 6
FAILURE_RATE = 0.2


def process_job(job_id):
    job = qs.get_job_data(job_id)
    if not job:
        print(f"  [worker] Job {job_id[:8]} not found, skipping")
        return

    qs.update_job_status(job_id, "processing")
    print(f"  [worker] Processing job {job_id[:8]} for badge {job['badge_id']}...")

    duration = random.uniform(PRINT_MIN_SECONDS, PRINT_MAX_SECONDS)
    time.sleep(duration)

    if random.random() < FAILURE_RATE:
        qs.update_job_status(job_id, "failed")
        status = "failed"
        print(f"  [worker] Job {job_id[:8]} FAILED (simulated print error)")
    else:
        qs.update_job_status(job_id, "completed")
        status = "completed"
        print(f"  [worker] Job {job_id[:8]} completed in {duration:.1f}s")

    fire_webhook(job_id, job["badge_id"], job["attendee"], status)


def fire_webhook(job_id, badge_id, attendee, status):
    payload = {
        "job_id": job_id,
        "badge_id": badge_id,
        "attendee": attendee,
        "status": status
    }

    for attempt in range(3):
        try:
            resp = requests.post(WEBHOOK_URL, json=payload, timeout=5)
            if resp.status_code == 200:
                print(f"  [worker] Webhook delivered for job {job_id[:8]}")
                return
            print(f"  [worker] Webhook attempt {attempt+1} got {resp.status_code}, retrying...")
        except requests.exceptions.RequestException as e:
            print(f"  [worker] Webhook attempt {attempt+1} failed: {e}, retrying...")
        time.sleep(2 ** attempt)

    print(f"  [worker] Webhook delivery failed after 3 attempts for job {job_id[:8]}")


qs.on_job_queued(process_job)


if __name__ == "__main__":
    print("Print worker ready — listening for jobs via queue_server")
    print(f"Webhook target: {WEBHOOK_URL}")
    print(f"Simulated print time: {PRINT_MIN_SECONDS}–{PRINT_MAX_SECONDS}s")
    print(f"Failure rate: {FAILURE_RATE * 100:.0f}%")
