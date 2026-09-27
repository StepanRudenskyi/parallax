import logging

from tenacity import before_sleep_log, retry, stop_after_attempt, wait_exponential

logger = logging.getLogger("agents.retry")

# Shared retry policy for LLM calls: 3 attempts total, exponential backoff
# (1s, 2s, 4s, capped at 8s). Transient issues (rate limits, brief provider
# outages, network blips) are common with free-tier cloud LLM APIs -- this
# is cheap insurance against a single flaky call failing an entire /analyze
# request. `reraise=True` means the original exception surfaces after the
# final attempt, so callers/logs still see the real error, not a wrapper.
llm_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
    before_sleep=before_sleep_log(logger, logging.WARNING),
)