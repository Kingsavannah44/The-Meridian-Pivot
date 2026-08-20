import time
import threading
import requests
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import webhook_receiver as wh

QUEUE_URL = "http://localhost:5001/print-job"

badge_states = {}
states_lock = threading.Lock()

seen_badges = set()
seen_lock = threading.Lock()


def scan_badge(badge_id, attendee_name):
    with seen_lock:
        if badge_id in seen_badges:
            print(f"  [kiosk] DUPLICATE SCAN blocked for badge {badge_id}")
            return
        seen_badges.add(badge_id)

    with states_lock:
        badge_states[badge_id] = "Pending..."

    print(f"\n  [kiosk] Badge {badge_id} scanned for {attendee_name}")
    print(f"  [kiosk] UI state → Pending...")

    try:
        resp = requests.post(QUEUE_URL, json={
            "badge_id": badge_id,
            "attendee": attendee_name
        }, timeout=5)

        if resp.status_code == 202:
            job_id = resp.json().get("job_id")
            print(f"  [kiosk] Print job queued → job_id: {job_id[:8]}")
            _wait_for_confirmation(badge_id, job_id)

        elif resp.status_code == 409:
            print(f"  [kiosk] Server also caught duplicate for badge {badge_id}")

        else:
            print(f"  [kiosk] Unexpected response: {resp.status_code} — {resp.text}")
            with states_lock:
                badge_states[badge_id] = "Error"

    except requests.exceptions.RequestException as e:
        print(f"  [kiosk] Failed to reach queue server: {e}")
        with states_lock:
            badge_states[badge_id] = "Error"


def _wait_for_confirmation(badge_id, job_id):
    def poll():
        timeout = 60
        interval = 1
        elapsed = 0

        while elapsed < timeout:
            confirmation = wh.get_confirmation(job_id)
            if confirmation:
                status = confirmation["status"]
                if status == "completed":
                    with states_lock:
                        badge_states[badge_id] = "Checked In"
                    print(f"  [kiosk] UI state → Checked In ✓  (badge {badge_id})")
                else:
                    with states_lock:
                        badge_states[badge_id] = "Print Failed"
                    print(f"  [kiosk] UI state → Print Failed ✗  (badge {badge_id})")
                return

            time.sleep(interval)
            elapsed += interval

        with states_lock:
            badge_states[badge_id] = "Timeout"
        print(f"  [kiosk] UI state → Timeout (no confirmation after {timeout}s)")

    threading.Thread(target=poll, daemon=True).start()


def get_ui_state(badge_id):
    with states_lock:
        return badge_states.get(badge_id, "Not Scanned")


def run_kiosk_server():
    from flask import Flask, jsonify, request as freq
    ui_app = Flask("kiosk_ui")

    @ui_app.route("/scan", methods=["POST"])
    def scan():
        body = freq.get_json(silent=True) or {}
        badge_id = body.get("badge_id")
        attendee = body.get("attendee", "Unknown")
        if not badge_id:
            return jsonify({"error": "badge_id required"}), 400
        threading.Thread(target=scan_badge, args=(badge_id, attendee), daemon=True).start()
        return jsonify({"status": "queued", "badge_id": badge_id}), 202

    @ui_app.route("/status/<badge_id>", methods=["GET"])
    def status(badge_id):
        return jsonify({"badge_id": badge_id, "ui_state": get_ui_state(badge_id)}), 200

    print("Kiosk UI server on http://localhost:5003")
    ui_app.run(port=5003, debug=False)


if __name__ == "__main__":
    import queue_server as qs
    import print_worker

    print("=" * 55)
    print("  Async Kiosk — Day 4 Prototype")
    print("  Queue:   http://localhost:5001")
    print("  Webhook: http://localhost:5002")
    print("  Kiosk:   http://localhost:5003")
    print("=" * 55)

    threading.Thread(
        target=lambda: qs.app.run(port=5001, debug=False),
        daemon=True
    ).start()

    threading.Thread(
        target=lambda: wh.app.run(port=5002, debug=False),
        daemon=True
    ).start()

    time.sleep(1)

    print("\nSimulating badge scans...\n")

    scan_badge("BADGE-001", "Alice Johnson")
    time.sleep(0.3)
    scan_badge("BADGE-002", "Bob Smith")
    time.sleep(0.3)
    scan_badge("BADGE-001", "Alice Johnson")

    time.sleep(20)

    print("\n--- Final UI States ---")
    for badge_id in ["BADGE-001", "BADGE-002"]:
        print(f"  {badge_id}: {get_ui_state(badge_id)}")
