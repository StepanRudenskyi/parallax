from llm_provider import get_llm
from news import fetch_recent_headlines
from schemas import AgentOpinion
from state import ResearchState

_llm = get_llm()
_structured_llm = _llm.with_structured_output(AgentOpinion)


def sentiment_node(state: ResearchState) -> dict:
    headlines = fetch_recent_headlines(state["ticker"], limit=5)

    if not headlines:
        opinion = AgentOpinion(
            verdict="HOLD",
            confidence=0.0,
            reasoning="No recent news headlines were available for this ticker.",
        )
        return {"sentiment_opinion": opinion}

    headlines_block = "\n".join(f"- {h}" for h in headlines)
    prompt = (
        f"You are a market sentiment analyst. Given these recent news headlines "
        f"for {state['ticker']}:\n\n"
        f"{headlines_block}\n\n"
        f"Assess the overall sentiment and provide a BUY/HOLD/SELL verdict with a "
        f"confidence score (0-1) and a short reasoning. If headlines are mixed or "
        f"uninformative, lower your confidence rather than guessing."
    )

    opinion = _structured_llm.invoke(prompt)
    return {"sentiment_opinion": opinion}