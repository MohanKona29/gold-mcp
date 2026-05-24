"""Adapter for the economic-calendar news history."""
from __future__ import annotations

import pandas as pd

from ._paths import news_calendar_file, not_configured

GOLD_RELEVANT = ("USD", "EUR", "JPY", "GBP", "CNY", "CHF")


def _load() -> pd.DataFrame | None:
    path = news_calendar_file()
    if path is None:
        return None
    try:
        df = pd.read_csv(path, encoding="latin-1")
    except Exception:
        return None
    df["date_parsed"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date_parsed"]).copy()
    df["impact"] = df["impact"].fillna("low").astype(str).str.lower()
    return df


def get_news_calendar(
    lookforward_days: int = 7,
    lookback_days: int = 2,
    min_impact: str = "medium",
    gold_only: bool = True,
) -> dict:
    """Return upcoming + recent macro events relevant to gold."""
    df = _load()
    if df is None:
        return not_configured("get_news_calendar", "GOLD_MCP_NEWS_CALENDAR_FILE")

    now = pd.Timestamp.now(tz=None).normalize()
    start = now - pd.Timedelta(days=lookback_days)
    end = now + pd.Timedelta(days=lookforward_days)

    df = df[(df["date_parsed"] >= start) & (df["date_parsed"] <= end)]
    if gold_only:
        df = df[df["currency"].isin(GOLD_RELEVANT)]

    impact_order = {"low": 0, "medium": 1, "high": 2, "holiday": 0}
    min_rank = impact_order.get(min_impact.lower(), 1)
    df = df[df["impact"].map(impact_order).fillna(0).astype(int) >= min_rank]

    if df.empty:
        return {
            "window_days_back": lookback_days,
            "window_days_forward": lookforward_days,
            "min_impact": min_impact,
            "events": [],
            "interpretation": "No matching events in window.",
        }

    events = []
    for _, r in df.sort_values("date_parsed").iterrows():
        events.append({
            "date": r["date_parsed"].strftime("%Y-%m-%d"),
            "currency": r["currency"],
            "event": r["event"],
            "actual": _clean(r.get("actual")),
            "forecast": _clean(r.get("forecast")),
            "previous": _clean(r.get("previous")),
            "impact": r["impact"],
        })

    # Highlight upcoming high-impact USD events (most gold-relevant)
    upcoming_high_usd = [
        e for e in events
        if e["currency"] == "USD"
        and e["impact"] == "high"
        and e["date"] >= now.strftime("%Y-%m-%d")
    ]

    return {
        "window_days_back": lookback_days,
        "window_days_forward": lookforward_days,
        "min_impact": min_impact,
        "gold_only": gold_only,
        "event_count": len(events),
        "upcoming_high_impact_usd_count": len(upcoming_high_usd),
        "next_high_impact_usd_event": upcoming_high_usd[0] if upcoming_high_usd else None,
        "events": events,
        "interpretation": _summarize(events, upcoming_high_usd),
    }


def _clean(v) -> str | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip()
    return s if s else None


def _summarize(events: list, upcoming_high_usd: list) -> str:
    n = len(events)
    if not events:
        return "No notable macro events in window."
    if upcoming_high_usd:
        nxt = upcoming_high_usd[0]
        return (
            f"{n} events in window. Next high-impact USD event: "
            f"{nxt['event']} on {nxt['date']}. Gold typically sees increased "
            f"vol around USD high-impact releases."
        )
    return f"{n} events in window; no upcoming high-impact USD events."
