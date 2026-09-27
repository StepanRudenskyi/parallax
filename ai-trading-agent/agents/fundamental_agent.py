import logging

from fundamentals import fetch_fundamental_snapshot
from llm_provider import get_llm
from logging_config import Timer
from retry_utils import llm_retry
from schemas import AgentOpinion
from state import ResearchState

logger = logging.getLogger("agents.fundamental")

_llm = get_llm()
_structured_llm = _llm.with_structured_output(AgentOpinion)


@llm_retry
def _invoke(prompt: str) -> AgentOpinion:
    return _structured_llm.invoke(prompt)


def fundamental_node(state: ResearchState) -> dict:
    ticker = state["ticker"]
    with Timer(logger, "fundamental_node", ticker=ticker, agent="FUNDAMENTAL"):
        snapshot = fetch_fundamental_snapshot(ticker)

        if snapshot.get("trailing_pe") is None and snapshot.get("market_cap") is None:
            opinion = AgentOpinion(
                verdict="HOLD",
                confidence=0.0,
                reasoning="Fundamental data was unavailable for this ticker.",
            )
            logger.warning("fundamental_node: no data found", extra={"ticker": ticker})
            return {"fundamental_opinion": opinion}

        prompt = (
            f"You are a fundamental analyst. Given these metrics for {ticker}:\n"
            f"- Trailing P/E: {snapshot['trailing_pe']}\n"
            f"- Forward P/E: {snapshot['forward_pe']}\n"
            f"- Profit margins: {snapshot['profit_margins']}\n"
            f"- Revenue growth (YoY): {snapshot['revenue_growth']}\n"
            f"- Market cap: {snapshot['market_cap']}\n\n"
            f"Assess valuation and provide a BUY/HOLD/SELL verdict with a confidence "
            f"score (0-1) and a short reasoning based strictly on these metrics. If a "
            f"metric is missing, note it and lower your confidence accordingly."
        )

        opinion = _invoke(prompt)
        logger.info(
            "fundamental_node result",
            extra={"ticker": ticker, "verdict": opinion.verdict, "confidence": opinion.confidence},
        )
        return {"fundamental_opinion": opinion}