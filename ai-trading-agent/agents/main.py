import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from llm_provider import get_active_model_label
from persistence import save_analysis_run
from supervisor import research_graph

app = FastAPI(title="AI Trading Research Agent - Multi-Agent Supervisor (Phase 2)")


class AnalyzeRequest(BaseModel):
    ticker: str


def _opinion_dict(opinion):
    return {
        "verdict": opinion.verdict,
        "confidence": opinion.confidence,
        "reasoning": opinion.reasoning,
    }


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    ticker = request.ticker.upper()
    thread_id = str(uuid.uuid4())

    result = research_graph.invoke({"ticker": ticker})
    final = result["final_recommendation"]

    opinions = {
        "quant": result["quant_opinion"],
        "sentiment": result["sentiment_opinion"],
        "fundamental": result["fundamental_opinion"],
    }
    model_used = get_active_model_label()

    try:
        analysis_run_id = save_analysis_run(
            ticker=ticker,
            thread_id=thread_id,
            opinions=opinions,
            final_recommendation=final,
            model_used=model_used,
        )
    except ValueError as exc:
        # Instrument not seeded yet -> still return the analysis, just unpersisted.
        raise HTTPException(status_code=422, detail=str(exc))

    return {
        "analysis_run_id": str(analysis_run_id),
        "ticker": ticker,
        "agent_opinions": {name: _opinion_dict(op) for name, op in opinions.items()},
        "final_recommendation": {
            "final_verdict": final.final_verdict,
            "confidence": final.confidence,
            "summary": final.summary,
        },
    }


@app.get("/health")
def health():
    return {"status": "ok"}