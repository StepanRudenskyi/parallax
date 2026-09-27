import logging

from llm_provider import get_llm
from logging_config import Timer
from news import fetch_recent_headlines
from schemas import AgentOpinion
from state import ResearchState

logger = logging.getLogger("agents.sentiment")

_llm = get_llm()
_structured_llm = _llm.with_structured_output(AgentOpinion)


def sentiment_node(state: ResearchState) -> dict:
    ticker = state["ticker"]
    with Timer(logger, "sentiment_node", ticker=ticker, agent="SENTIMENT"):
        headlines = fetch_recent_headlines(ticker, limit=5)

        if not headlines:
            opinion = AgentOpinion(
                verdict="HOLD",
                confidence=0.0,
                reasoning="No recent news headlines were available for this ticker.",
            )
            logger.warning("sentiment_node: no headlines found", extra={"ticker": ticker})
            return {"sentiment_opinion": opinion}

        headlines_block = "\n".join(f"- {h}" for h in headlines)
        prompt = (
            f"You are a market sentiment analyst. Given these recent news headlines "
            f"for {ticker}:\n\n"
            f"{headlines_block}\n\n"
            f"Assess the overall sentiment and provide a BUY/HOLD/SELL verdict with a "
            f"confidence score (0-1) and a short reasoning. If headlines are mixed or "
            f"uninformative, lower your confidence rather than guessing."
        )

        opinion = _structured_llm.invoke(prompt)
        logger.info(
            "sentiment_node result",
            extra={"ticker": ticker, "verdict": opinion.verdict, "confidence": opinion.confidence},
        )
        return {"sentiment_opinion": opinion}