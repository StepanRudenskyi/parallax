from db import fetch_price_history
from indicators import compute_indicators
from llm_provider import get_llm
from schemas import AgentOpinion
from state import ResearchState

_llm = get_llm()
_structured_llm = _llm.with_structured_output(AgentOpinion)


def quant_node(state: ResearchState) -> dict:
    df = fetch_price_history(state["ticker"], days=100)
    indicators = compute_indicators(df)

    if indicators.get("last_close") is None:
        opinion = AgentOpinion(
            verdict="HOLD",
            confidence=0.0,
            reasoning="Insufficient historical price data to compute indicators.",
        )
        return {"quant_opinion": opinion}

    prompt = (
        f"You are a quantitative technical analyst. Given these indicators for "
        f"{state['ticker']}:\n"
        f"- Last close price: {indicators['last_close']:.2f}\n"
        f"- SMA(20): {indicators['sma_20']}\n"
        f"- RSI(14): {indicators['rsi_14']}\n\n"
        f"Provide a BUY/HOLD/SELL verdict with a confidence score (0-1) and a short "
        f"reasoning based strictly on these numbers."
    )

    opinion = _structured_llm.invoke(prompt)
    return {"quant_opinion": opinion}