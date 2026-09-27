import logging
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from execution_client import trigger_backtest
from llm_provider import get_active_model_label
from logging_config import Timer, configure_logging
from persistence import save_analysis_run
from supervisor import research_graph

configure_logging()
logger = logging.getLogger("agents.main")

app = FastAPI(title="AI Trading Research Agent - Multi-Agent Supervisor (Phase 5)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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

    with Timer(logger, "analyze_request", ticker=ticker):
        result = research_graph.invoke({"ticker": ticker})
        final = result["final_recommendation"]

        opinions = {
            "quant": result["quant_opinion"],
            "sentiment": result["sentiment_opinion"],
            "fundamental": result["fundamental_opinion"],
        }
        model_used = get_active_model_label()

        try:
            ids = save_analysis_run(
                ticker=ticker,
                thread_id=thread_id,
                opinions=opinions,
                final_recommendation=final,
                model_used=model_used,
            )
        except ValueError as exc:
            logger.error(f"persistence failed: {exc}", extra={"ticker": ticker, "status": "error"})
            raise HTTPException(status_code=422, detail=str(exc))

        backtest = trigger_backtest(ticker, ids["recommendation_id"])

        return {
            "analysis_run_id": str(ids["analysis_run_id"]),
            "recommendation_id": str(ids["recommendation_id"]),
            "ticker": ticker,
            "agent_opinions": {name: _opinion_dict(op) for name, op in opinions.items()},
            "final_recommendation": {
                "final_verdict": final.final_verdict,
                "confidence": final.confidence,
                "summary": final.summary,
            },
            "backtest_context": backtest,
        }


@app.get("/health")
def health():
    return {"status": "ok"}