import logging
import os
import uuid

import requests
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_fixed

load_dotenv()

logger = logging.getLogger("agents.execution_client")

EXECUTION_SERVICE_URL = os.getenv("EXECUTION_SERVICE_URL", "http://localhost:8081")

# Shorter, fixed-wait retry for the internal service call (2 attempts, 1s
# apart) -- this is a local network hop, not a rate-limited external API, so
# there's no need for exponential backoff. Mainly guards against the
# execution service still finishing its startup healthcheck window.
_internal_retry = retry(stop=stop_after_attempt(2), wait=wait_fixed(1), reraise=True)


@_internal_retry
def _post_backtest(url: str, recommendation_id: uuid.UUID):
    response = requests.post(
        url,
        json={"recommendationId": str(recommendation_id)},
        timeout=15,
    )
    response.raise_for_status()
    return response


def trigger_backtest(ticker: str, recommendation_id: uuid.UUID) -> dict | None:
    """
    Fire-and-report call to the Java execution service. Fails soft: if the
    execution service is unreachable or errors after retries, /analyze still
    returns the recommendation -- a backtest is supporting context, not a
    hard dependency of the analysis itself.
    """
    url = f"{EXECUTION_SERVICE_URL}/backtest/{ticker}"

    try:
        response = _post_backtest(url, recommendation_id)
        logger.info("backtest triggered", extra={"ticker": ticker, "status": "ok"})
        return response.json()
    except requests.RequestException as exc:
        logger.error(
            f"backtest service unavailable after retries: {exc}",
            extra={"ticker": ticker, "status": "error"},
        )
        return {"error": f"Backtest service unavailable: {exc}"}