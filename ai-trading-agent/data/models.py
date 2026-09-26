from sqlalchemy import (
    Column, String, Boolean, Numeric, TIMESTAMP, BigInteger, ForeignKey,
    UniqueConstraint, Enum, func
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.dialects.postgresql import UUID
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
