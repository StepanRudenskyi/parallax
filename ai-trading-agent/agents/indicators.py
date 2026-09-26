import pandas as pd


def compute_sma(df: pd.DataFrame, window: int = 20) -> float | None:
    if len(df) < window:
        return None
    return float(df["close"].rolling(window=window).mean().iloc[-1])


def compute_rsi(df: pd.DataFrame, window: int = 14) -> float | None:
    if len(df) < window + 1:
        return None

    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()

    rs = avg_gain / avg_loss.replace(0, 1e-9)
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1])


def compute_indicators(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"sma_20": None, "rsi_14": None, "last_close": None}

    return {
        "sma_20": compute_sma(df, 20),
        "rsi_14": compute_rsi(df, 14),
        "last_close": float(df["close"].iloc[-1]),
    }