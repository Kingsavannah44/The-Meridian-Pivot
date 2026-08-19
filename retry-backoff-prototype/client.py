import time
import random
import logging
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

BASE_DELAY = 1.0
MAX_DELAY = 30.0
MAX_RETRIES = 5
JITTER_MAX = 1.0

RETRYABLE_STATUSES = {500, 502, 503, 504}


class MaxRetriesExceeded(Exception):
    pass


def backoff_delay(attempt: int) -> float:
    exponential = BASE_DELAY * (2 ** attempt)
    capped = min(exponential, MAX_DELAY)
    jitter = random.uniform(0, JITTER_MAX)
    return round(capped + jitter, 3)


def post_with_retry(url: str, payload: dict) -> dict:
    last_exception = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.post(url, json=payload, timeout=5)

            if response.status_code == 200:
                log.info(
                    f"[Attempt {attempt + 1}] → {response.status_code} ✓  "
                    f"(succeeded after {attempt + 1} attempt{'s' if attempt else ''})"
                )
                return response.json()

            if response.status_code in RETRYABLE_STATUSES:
                if attempt < MAX_RETRIES:
                    delay = backoff_delay(attempt)
                    log.warning(
                        f"[Attempt {attempt + 1}] → {response.status_code}  "
                        f"(retry in {delay}s)"
                    )
                    time.sleep(delay)
                else:
                    log.error(
                        f"[Attempt {attempt + 1}] → {response.status_code}  "
                        f"(max retries reached, giving up)"
                    )
            else:
                log.error(
                    f"[Attempt {attempt + 1}] → {response.status_code}  "
                    f"(non-retryable, aborting)"
                )
                response.raise_for_status()

        except requests.exceptions.ConnectionError as e:
            last_exception = e
            if attempt < MAX_RETRIES:
                delay = backoff_delay(attempt)
                log.warning(
                    f"[Attempt {attempt + 1}] Connection error — retry in {delay}s\n"
                    f"  Detail: {e}"
                )
                time.sleep(delay)
            else:
                log.error(f"[Attempt {attempt + 1}] Connection error — max retries reached")

        except requests.exceptions.Timeout as e:
            last_exception = e
            if attempt < MAX_RETRIES:
                delay = backoff_delay(attempt)
                log.warning(f"[Attempt {attempt + 1}] Timeout — retry in {delay}s")
                time.sleep(delay)

    raise MaxRetriesExceeded(
        f"All {MAX_RETRIES + 1} attempts failed for {url}. "
        f"Last error: {last_exception}"
    )


if __name__ == "__main__":
    TARGET_URL = "http://localhost:5000/data"
    PAYLOAD = {"message": "hello", "sprint": "meridian-pivot"}

    log.info("=" * 50)
    log.info(f"Calling {TARGET_URL}")
    log.info(f"Config: base={BASE_DELAY}s, max_delay={MAX_DELAY}s, max_retries={MAX_RETRIES}")
    log.info("=" * 50)

    try:
        result = post_with_retry(TARGET_URL, PAYLOAD)
        log.info(f"Final response: {result}")
    except MaxRetriesExceeded as e:
        log.error(f"FAILED: {e}")
