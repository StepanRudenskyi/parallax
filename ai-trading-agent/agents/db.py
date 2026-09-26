import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5433")

DB_URL = (
    f"postgresql+psycopg2://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{DB_HOST}:{DB_PORT}/{os.getenv('POSTGRES_DB')}"
)

engine = create_engine(DB_URL, future=True)


def fetch_price_history(ticker: str, days: int = 100) -> pd.DataFrame:
    query = text(
        """
        SELECT p.ts, p.open, p.high, p.low, p.close, p.volume
        FROM price_bar p
        JOIN instrument i ON i.id = p.instrument_id
        WHERE i.ticker = :ticker
        ORDER BY p.ts DESC
        LIMIT :days
        """
    )
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"ticker": ticker, "days": days})

    if df.empty:
        return df

    df = df.sort_values("ts").reset_index(drop=True)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    return df