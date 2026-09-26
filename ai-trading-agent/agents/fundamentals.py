import yfinance as yf


def fetch_fundamental_snapshot(ticker: str) -> dict:
    """
    Pulls a small, fixed set of fundamental metrics. Fails soft: returns a dict
    of Nones if Yahoo's info endpoint is unavailable, so the fundamental agent
    can still respond (with low confidence) instead of crashing the graph run.
    """
    defaults = {
        "trailing_pe": None,
        "forward_pe": None,
        "profit_margins": None,
        "revenue_growth": None,
        "market_cap": None,
    }

    try:
        info = yf.Ticker(ticker).info or {}
    except Exception:
        return defaults

    return {
        "trailing_pe": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "profit_margins": info.get("profitMargins"),
        "revenue_growth": info.get("revenueGrowth"),
        "market_cap": info.get("marketCap"),
    }