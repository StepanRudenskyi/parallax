from fastapi import FastAPI
from pydantic import BaseModel

from graph import quant_agent_graph

app = FastAPI(title="AI Trading Research Agent - Quant Analyst (Phase 1)")


class AnalyzeRequest(BaseModel):
    ticker: str


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    result = quant_agent_graph.invoke({"ticker": request.ticker.upper()})
    recommendation = result["recommendation"]

    return {
        "ticker": request.ticker.upper(),
        "indicators": result["indicators"],
        "recommendation": {
            "verdict": recommendation.verdict,
            "confidence": recommendation.confidence,
            "reasoning": recommendation.reasoning,
        },
    }


@app.get("/health")
def health():
    return {"status": "ok"}