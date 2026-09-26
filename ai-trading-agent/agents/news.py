import yfinance as yf


def fetch_recent_headlines(ticker: str, limit: int = 5) -> list[str]:
    """
    Defensive parsing: yfinance has changed the shape of Ticker.news more than
    once (flat dicts vs. nested under a 'content' key). Handle both, and fail
    soft (empty list) rather than crashing the whole agent run — a missing news
    feed should degrade the sentiment agent's confidence, not break the pipeline.
    """

    try:
        raw_items = yf.Ticker(ticker).news or []
    except Exception:
        return []

    headlines = []
    for item in raw_items[:limit]:
        title = None
        if isinstance(item, dict):
            if "title" in item:
                title = item.get("title")
            elif "content" in item and isinstance(item["content"], dict):
                title = item["content"].get("title")
        if title:
            headlines.append(title)

    return headlines
