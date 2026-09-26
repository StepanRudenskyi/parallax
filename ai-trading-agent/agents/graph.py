import os
from typing import TypedDict, Optional

from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

from db import fetch_price_history
from indicators import compute_indicators

load_dotenv()


class Recommendation(BaseModel):
    verdict: str = Field(description="One of: BUY, HOLD, SELL")
    confidence: float = Field(description="Confidence score between 0 and 1")
    reasoning: str = Field(description="Short explanation referencing the indicators")


class QuantAgentState(TypedDict):
    ticker: str
    indicators: Optional[dict]
    recommendation: Optional[Recommendation]


def get_llm():
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()

    if provider == "groq":
        from langchain_groq import ChatGroq

        model_name = os.getenv("GROQ_MODEL", "qwen/qwen3.6-27b")
        return ChatGroq(model=model_name, temperature=0.1)

    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        model_name = os.getenv("GOOGLE_MODEL", "gemini-2.5-flash")
        return ChatGoogleGenerativeAI(model=model_name, temperature=0.1)

    from langchain_ollama import ChatOllama

    model_name = os.getenv("OLLAMA_MODEL", "qwen3:4b")
    return ChatOllama(model=model_name, temperature=0.1)


llm = get_llm()
structured_llm = llm.with_structured_output(Recommendation)


def fetch_and_compute_node(state: QuantAgentState) -> QuantAgentState:
    df = fetch_price_history(state["ticker"], days=100)
    indicators = compute_indicators(df)
    return {**state, "indicators": indicators}


def llm_synthesis_node(state: QuantAgentState) -> QuantAgentState:
    indicators = state["indicators"]

    if indicators.get("last_close") is None:
        recommendation = Recommendation(
            verdict="HOLD",
            confidence=0.0,
            reasoning="Insufficient historical data to compute indicators.",
        )
        return {**state, "recommendation": recommendation}

    prompt = (
        f"You are a quantitative analyst. Given these technical indicators for "
        f"{state['ticker']}:\n"
        f"- Last close price: {indicators['last_close']:.2f}\n"
        f"- SMA(20): {indicators['sma_20']}\n"
        f"- RSI(14): {indicators['rsi_14']}\n\n"
        f"Provide a BUY/HOLD/SELL verdict with a confidence score (0-1) and a short "
        f"reasoning based strictly on these numbers."
    )

    recommendation = structured_llm.invoke(prompt)
    return {**state, "recommendation": recommendation}


def build_quant_agent_graph():
    builder = StateGraph(QuantAgentState)
    builder.add_node("fetch_and_compute", fetch_and_compute_node)
    builder.add_node("llm_synthesis", llm_synthesis_node)

    builder.add_edge(START, "fetch_and_compute")
    builder.add_edge("fetch_and_compute", "llm_synthesis")
    builder.add_edge("llm_synthesis", END)

    return builder.compile()


quant_agent_graph = build_quant_agent_graph()