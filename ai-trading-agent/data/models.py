from sqlalchemy import (
    Column, String, Boolean, Numeric, TIMESTAMP, BigInteger, ForeignKey,
    UniqueConstraint, CheckConstraint, Enum, Integer, Text, func
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
import enum


class Base(DeclarativeBase):
    pass


class AssetType(str, enum.Enum):
    EQUITY = "EQUITY"
    CRYPTO = "CRYPTO"


class Timeframe(str, enum.Enum):
    DAILY = "1d"
    HOURLY = "1h"
    MINUTE = "1m"


class Instrument(Base):
    __tablename__ = "instrument"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker = Column(String(20), nullable=False)
    asset_type = Column(Enum(AssetType, name="asset_type"), nullable=False, default=AssetType.EQUITY)
    source = Column(String(50), nullable=False)
    currency = Column(String(10), nullable=False, default="USD")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("ticker", "source", name="uq_instrument_ticker_source"),
    )


class PriceBar(Base):
    __tablename__ = "price_bar"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    instrument_id = Column(UUID(as_uuid=True), ForeignKey("instrument.id"), nullable=False)
    ts = Column(TIMESTAMP(timezone=True), nullable=False)
    timeframe = Column(Enum(Timeframe, name="timeframe"), nullable=False, default=Timeframe.DAILY)

    open = Column(Numeric(20, 8), nullable=False)
    high = Column(Numeric(20, 8), nullable=False)
    low = Column(Numeric(20, 8), nullable=False)
    close = Column(Numeric(20, 8), nullable=False)
    volume = Column(Numeric(24, 8), nullable=True)

    source = Column(String(50), nullable=False)

    __table_args__ = (
        UniqueConstraint("instrument_id", "ts", "timeframe", name="uq_price_bar_instrument_ts_timeframe"),
    )


class AnalysisRun(Base):
    """
    One row per /analyze invocation. status/triggered_by use VARCHAR + CHECK
    (not native Postgres ENUM) deliberately, so the future Java service can
    write to this table over plain JDBC without enum-type friction.
    """
    __tablename__ = "analysis_run"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instrument_id = Column(UUID(as_uuid=True), ForeignKey("instrument.id"), nullable=False)
    thread_id = Column(String(100), nullable=True)
    status = Column(String(20), nullable=False, default="RUNNING")
    triggered_by = Column(String(20), nullable=False, default="API")
    requested_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('RUNNING', 'COMPLETED', 'FAILED')", name="ck_analysis_run_status"),
        CheckConstraint("triggered_by IN ('MANUAL', 'SCHEDULED', 'API')", name="ck_analysis_run_triggered_by"),
    )


class Recommendation(Base):
    __tablename__ = "recommendation"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_run.id"), nullable=False, unique=True)
    final_verdict = Column(String(10), nullable=False)
    confidence = Column(Numeric(4, 3), nullable=False)
    summary_text = Column(Text, nullable=False)
    model_used = Column(String(100), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("final_verdict IN ('BUY', 'HOLD', 'SELL')", name="ck_recommendation_final_verdict"),
    )


class AgentOpinionRow(Base):
    __tablename__ = "agent_opinion"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_run.id"), nullable=False)
    agent_name = Column(String(20), nullable=False)
    verdict = Column(String(10), nullable=False)
    confidence = Column(Numeric(4, 3), nullable=False)
    reasoning_text = Column(Text, nullable=False)
    raw_output_json = Column(JSONB, nullable=True)
    model_used = Column(String(100), nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("agent_name IN ('SENTIMENT', 'QUANT', 'FUNDAMENTAL')", name="ck_agent_opinion_agent_name"),
        CheckConstraint("verdict IN ('BUY', 'HOLD', 'SELL')", name="ck_agent_opinion_verdict"),
    )