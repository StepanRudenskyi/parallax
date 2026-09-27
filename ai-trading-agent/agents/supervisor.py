import logging

from langgraph.graph import StateGraph, START, END

from fundamental_agent import fundamental_node
from llm_provider import get_llm
from logging_config import Timer
from quant_agent import quant_node
from retry_utils import llm_retry
from schemas import FinalRecommendation
from sentiment_agent import sentiment_node
from state import ResearchState

logger = logging.getLogger("agents.supervisor")

_llm = get_llm()
_structured_llm = _llm.with_structured_output(FinalRecommendation)


@llm_retry
def _invoke(prompt: str) -> FinalRecommendation:
    return _structured_llm.invoke(prompt)


def synthesis_node(state: ResearchState) -> dict:
    ticker = state["ticker"]
    with Timer(logger, "synthesis_node", ticker=ticker, agent="SUPERVISOR"):
        quant = state["quant_opinion"]
        sentiment = state["sentiment_opinion"]
        fundamental = state["fundamental_opinion"]

        prompt = (
            f"You are the supervisor synthesizing three independent analyst opinions "
            f"for {ticker}. You do not have your own opinion — you weigh the "
            f"three below, favoring higher-confidence opinions, and explain any "
            f"disagreement between them.\n\n"
            f"Quant analyst: verdict={quant.verdict}, confidence={quant.confidence}, "
            f"reasoning=\"{quant.reasoning}\"\n\n"
            f"Sentiment analyst: verdict={sentiment.verdict}, confidence={sentiment.confidence}, "
            f"reasoning=\"{sentiment.reasoning}\"\n\n"
            f"Fundamental analyst: verdict={fundamental.verdict}, confidence={fundamental.confidence}, "
            f"reasoning=\"{fundamental.reasoning}\"\n\n"
            f"Provide a final BUY/HOLD/SELL verdict, an overall confidence score (0-1), "
            f"and a short summary explaining how you weighed the three inputs."
        )

        final_recommendation = _invoke(prompt)
        logger.info(
            "synthesis_node result",
            extra={
                "ticker": ticker,
                "verdict": final_recommendation.final_verdict,
                "confidence": final_recommendation.confidence,
            },
        )
        return {"final_recommendation": final_recommendation}


def build_research_graph():
    builder = StateGraph(ResearchState)

    builder.add_node("quant", quant_node)
    builder.add_node("sentiment", sentiment_node)
    builder.add_node("fundamental", fundamental_node)
    builder.add_node("synthesis", synthesis_node)

    # Fan-out: all three specialists run from START.
    builder.add_edge(START, "quant")
    builder.add_edge(START, "sentiment")
    builder.add_edge(START, "fundamental")

    # Fan-in: synthesis only runs once all three have written their opinion,
    # because each node returns a partial update touching a distinct key
    # (no concurrent writes to the same key -> no reducer needed).
    builder.add_edge("quant", "synthesis")
    builder.add_edge("sentiment", "synthesis")
    builder.add_edge("fundamental", "synthesis")

    builder.add_edge("synthesis", END)

    return builder.compile()


research_graph = build_research_graph()