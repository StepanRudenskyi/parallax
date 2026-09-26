"""
One-time (re-runnable) script for seeding instrument + price_bar with historical data via yfinance.

Usage:
    python seed_price_data.py
"""

import sys
from datetime import datetime, timezone

import yfinance as yf
from sqlalchemy.dialects.postgresql import insert as pg_insert

from db import SessionLocal
from models import Instrument, PriceBar, AssetType, Timeframe

TICKERS = ["AAPL", "MSFT", "NVDA"]
SOURCE = "yfinance"
PERIOD = "1y"
INTERVAL = "1d"


def get_or_create_instrument(session, ticker: str) -> Instrument:
    instrument = (
        session.query(Instrument)
        .filter_by(ticker=ticker, source=SOURCE)
        .one_or_none()
    )
    if instrument is None:
        instrument = Instrument(
            ticker=ticker,
            asset_type=AssetType.EQUITY,
            source=SOURCE,
            currency="USD",
            is_active=True,
        )
        session.add(instrument)
        session.flush()
        print(f"[instrument] created {ticker} -> {instrument.id}")
    else:
        print(f"[instrument] reused {ticker} -> {instrument.id}")
    return instrument


def upsert_price_bars(session, instrument: Instrument, df) -> int:
    if df.empty:
        print(f"[price_bar] no data returned for {instrument.ticker}")
        return 0

    rows = []
    for ts, row in df.iterrows():
        rows.append(
            {
                "instrument_id": instrument.id,
                "ts": ts.to_pydatetime().replace(tzinfo=timezone.utc),
                "timeframe": Timeframe.DAILY.value,
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": float(row["Volume"]) if row["Volume"] == row["Volume"] else None,
                "source": SOURCE,
            }
        )

    stmt = pg_insert(PriceBar.__table__).values(rows)
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["instrument_id", "ts", "timeframe"]
    )
    result = session.execute(stmt)
    return result.rowcount or 0


def main():
    session = SessionLocal()
    total_inserted = 0

    try:
        for ticker in TICKERS:
            print(f"\n--- {ticker} ---")
            instrument = get_or_create_instrument(session, ticker)

            df = yf.download(
                ticker, period=PERIOD, interval=INTERVAL, progress=False, auto_adjust=False
            )
            if isinstance(df.columns, object) and hasattr(df.columns, "droplevel"):
                # yfinance іноді повертає MultiIndex-колонки для одного тікера
                try:
                    df.columns = df.columns.droplevel(1)
                except Exception:
                    pass

            inserted = upsert_price_bars(session, instrument, df)
            total_inserted += inserted
            print(f"[price_bar] inserted {inserted} new rows for {ticker}")

        session.commit()
        print(f"\nDone. Total new rows inserted: {total_inserted}")

    except Exception as exc:
        session.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()