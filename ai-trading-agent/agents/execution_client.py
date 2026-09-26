import os
import uuid

import requests
from dotenv import load_dotenv

load_dotenv()

EXECUTION_SERVICE_URL = os.getenv("EXECUTION_SERVICE_URL", "http://localhost:8081")


def trigger_backtest(ticker: str, recommendation_id: uuid.UUID) -> dict | None:
    """
    Fire-and-report call to the Java execution service. Fails soft: if the
    execution service is unreachable or errors, /analyze still returns the
    recommendation -- a backtest is supporting context, not a hard dependency
    of the analysis itself. Returns None on any failure.
    """
    url = f"{EXECUTION_SERVICE_URL}/backtest/{ticker}"

    try:
        response = requests.post(
            url,
            json={"recommendationId": str(recommendation_id)},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        return {"error": f"Backtest service unavailable: {exc}"}