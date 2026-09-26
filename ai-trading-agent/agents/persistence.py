import uuid
from datetime import datetime, timezone

from sqlalchemy import MetaData, Table, select

from db import engine

_metadata = MetaData()
_instrument = Table("instrument", _metadata, autoload_with=engine)
_analysis_run = Table("analysis_run", _metadata, autoload_with=engine)
_recommendation = Table("recommendation", _metadata, autoload_with=engine)
_agent_opinion = Table("agent_opinion", _metadata, autoload_with=engine)


def _get_instrument_id(conn, ticker: str):
    stmt = select(_instrument.c.id).where(_instrument.c.ticker == ticker)
    row = conn.execute(stmt).first()
    if row is None:
        raise ValueError(
            f"Instrument '{ticker}' not found in the instrument table. "
            f"Seed it first (see data/seed_price_data.py)."
        )
    return row[0]


def save_analysis_run(ticker: str, thread_id: str, opinions: dict, final_recommendation, model_used: str) -> dict:
    """
    opinions: {"quant": AgentOpinion, "sentiment": AgentOpinion, "fundamental": AgentOpinion}
    Persists one analysis_run + one recommendation + three agent_opinion rows
    in a single transaction. Returns both ids -- the recommendation_id is
    needed by the caller to link a Java backtest run to this specific
    recommendation.
    """
    with engine.begin() as conn:
        instrument_id = _get_instrument_id(conn, ticker)
        run_id = uuid.uuid4()
        recommendation_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        conn.execute(
            _analysis_run.insert().values(
                id=run_id,
                instrument_id=instrument_id,
                thread_id=thread_id,
                status="COMPLETED",
                triggered_by="API",
                requested_at=now,
                completed_at=now,
            )
        )

        conn.execute(
            _recommendation.insert().values(
                id=recommendation_id,
                analysis_run_id=run_id,
                final_verdict=final_recommendation.final_verdict,
                confidence=final_recommendation.confidence,
                summary_text=final_recommendation.summary,
                model_used=model_used,
            )
        )

        for agent_name, opinion in opinions.items():
            conn.execute(
                _agent_opinion.insert().values(
                    id=uuid.uuid4(),
                    analysis_run_id=run_id,
                    agent_name=agent_name.upper(),
                    verdict=opinion.verdict,
                    confidence=opinion.confidence,
                    reasoning_text=opinion.reasoning,
                    raw_output_json=opinion.model_dump(),
                    model_used=model_used,
                )
            )

    return {"analysis_run_id": run_id, "recommendation_id": recommendation_id}