import random
from flask import Flask, jsonify, request

app = Flask(__name__)

FAILURE_RATE = 0.6


@app.route("/data", methods=["POST"])
def flaky_endpoint():
    if random.random() < FAILURE_RATE:
        print(f"  [server] Simulating failure for request from {request.remote_addr}")
        return jsonify({"error": "Internal Server Error", "retryable": True}), 500

    payload = request.get_json(silent=True) or {}
    print(f"  [server] Success — received payload: {payload}")
    return jsonify({"status": "ok", "received": payload}), 200


if __name__ == "__main__":
    print(f"Flaky server starting on http://localhost:5000")
    print(f"Failure rate: {FAILURE_RATE * 100:.0f}%")
    print("-" * 40)
    app.run(port=5000, debug=False)
