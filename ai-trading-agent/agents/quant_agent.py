import logging

from db import fetch_price_history
from indicators import compute_indicators
from llm_provider import get_llm
from logging_config import Timer
from retry_utils import llm_retry
from schemas import AgentOpinion
from state import ResearchState

logger = logging.getLogger("agents.quant")

_llm = get_llm()
_structured_llm = _llm.with_structured_output(AgentOpinion)


@llm_retry
def _invoke(prompt: str) -> AgentOpinion:
    return _structured_llm.invoke(prompt)


def quant_node(state: ResearchState) -> dict:
    ticker = state["ticker"]
    with Timer(logger, "quant_node", ticker=ticker, agent="QUANT"):
        df = fetch_price_history(ticker, days=100)
        indicators = compute_indicators(df)

        if indicators.get("last_close") is None:
            opinion = AgentOpinion(
                verdict="HOLD",
                confidence=0.0,
                reasoning="Insufficient historical price data to compute indicators.",
            )
            logger.warning("quant_node: no price data", extra={"ticker": ticker})
            return {"quant_opinion": opinion}

        prompt = (
            f"You are a quantitative technical analyst. Given these indicators for "
            f"{ticker}:\n"
            f"- Last close price: {indicators['last_close']:.2f}\n"
            f"- SMA(20): {indicators['sma_20']}\n"
            f"- RSI(14): {indicators['rsi_14']}\n\n"
            f"Provide a BUY/HOLD/SELL verdict with a confidence score (0-1) and a short "
            f"reasoning based strictly on these numbers."
        )

        opinion = _invoke(prompt)
        logger.info(
            "quant_node result",
            extra={"ticker": ticker, "verdict": opinion.verdict, "confidence": opinion.confidence},
        )
        return {"quant_opinion": opinion}
