"""Layer 3 — AI analyst tools.

These tools don't just return raw data — they aggregate multiple data
sources and present a structured read that downstream LLMs can reason
on more efficiently. The value here is the *opinionation*: which
signals to combine, how to weight them, and how to phrase the read.
"""
from __future__ import annotations

from . import l2_data, macro_data, microstructure, tick_data
from .adapters import (
    macro_strength as macro_strength_adapter,
    news_calendar as news_calendar_adapter,
    strategy as strategy_adapter,
)


def _safe(fn, *args, **kwargs):
    try:
        out = fn(*args, **kwargs)
        return out if isinstance(out, dict) else {"error": "non_dict_return"}
    except Exception as e:
        return {"error": "exception", "detail": str(e)}


def analyze_gold_setup(timeframe: str = "1h") -> dict:
    """Combined structured read on the current XAUUSD setup.

    Pulls: live price, spread regime, tick velocity, today's session
    summary, top-of-book L2, macro snapshot, macro strength, upcoming
    high-impact events, Asian-box state context, and freshness.

    Returns a single structured object grouped by signal category with
    a top-line read at the bottom.
    """
    price = _safe(tick_data.get_latest_price)
    spread = _safe(microstructure.get_spread_stats, lookback_hours=24)
    velocity = _safe(microstructure.get_tick_velocity, window_seconds=300)
    session = _safe(tick_data.get_session_summary)
    bars = _safe(tick_data.get_ohlcv, timeframe=timeframe, lookback=12)
    top_book = _safe(l2_data.get_top_of_book)
    macro = _safe(macro_data.get_macro_context)
    macro_str = _safe(macro_strength_adapter.get_macro_strength)
    news = _safe(news_calendar_adapter.get_news_calendar,
                 lookforward_days=2, lookback_days=0, min_impact="high", gold_only=True)
    asian = _safe(strategy_adapter.get_xau_asian_box_stats)
    fresh = _safe(microstructure.get_data_freshness)

    # Concise top-line read
    bullets = []
    if isinstance(session, dict) and "change_pct" in session:
        bullets.append(
            f"Session {session.get('date', '')}: {session['change_pct']:+.2f}% "
            f"(range ${session.get('range', 0):.1f})."
        )
    if isinstance(spread, dict) and "current_percentile" in spread:
        bullets.append(
            f"Spread at {spread['current_percentile']:.0f}th pct of 24h "
            f"({spread.get('current_spread', 0):.2f})."
        )
    if isinstance(velocity, dict) and "interpretation" in velocity:
        bullets.append(f"Tick activity: {velocity['interpretation']}.")
    if isinstance(macro_str, dict) and macro_str.get("gold_macro_bias"):
        bullets.append(f"Macro bias: {macro_str['gold_macro_bias']}.")
    if isinstance(news, dict) and news.get("next_high_impact_usd_event"):
        e = news["next_high_impact_usd_event"]
        bullets.append(f"Next USD high-impact event: {e['event']} ({e['date']}).")
    if isinstance(fresh, dict) and fresh.get("warning"):
        bullets.append(f"WARNING: {fresh['warning']}")

    return {
        "timeframe": timeframe,
        "price": price,
        "spread_regime": spread,
        "tick_activity": velocity,
        "session": session,
        "recent_bars": bars,
        "l2_top": top_book,
        "macro_snapshot": macro,
        "macro_strength": macro_str,
        "upcoming_high_impact_events": news,
        "asian_box_context": asian,
        "data_freshness": fresh,
        "top_line_read": bullets,
    }


def daily_briefing() -> dict:
    """Morning briefing aggregator: what happened, what to watch.

    Sections:
      - Overnight session recap (Asia)
      - Macro context + USD posture
      - Today's high-impact event watch
      - Asian-box statistical context for today
      - Freshness check
    """
    session = _safe(tick_data.get_session_summary)
    bars_4h = _safe(tick_data.get_ohlcv, timeframe="4h", lookback=6)
    session_micro = _safe(microstructure.get_session_microstructure, lookback_days=20)
    macro = _safe(macro_data.get_macro_context)
    macro_str = _safe(macro_strength_adapter.get_macro_strength)
    news = _safe(news_calendar_adapter.get_news_calendar,
                 lookforward_days=1, lookback_days=1, min_impact="high")
    asian = _safe(strategy_adapter.get_xau_asian_box_stats)
    fresh = _safe(microstructure.get_data_freshness)
    seasonality = _safe(_dow_seasonality)

    sections = {
        "1_overnight_recap": {
            "session_summary": session,
            "recent_4h_bars": bars_4h,
        },
        "2_macro_context": {
            "snapshot": macro,
            "macro_strength_engine": macro_str,
        },
        "3_today_event_watch": news,
        "4_session_microstructure_context": session_micro,
        "5_asian_box_statistical_context": asian,
        "6_today_seasonality": seasonality,
        "7_health": fresh,
    }

    return {
        "format": "daily_briefing",
        "sections": sections,
        "consumption_hint": (
            "Read sections 1-3 first for the immediate read, then 4-6 for "
            "context. Section 7 warns if any underlying data feed is stale."
        ),
    }


def _dow_seasonality() -> dict:
    from . import analytics
    return analytics.get_seasonality(group_by="dow", lookback_years=5)


def risk_assessment(side: str, entry_price: float, stop_price: float, size_usd: float) -> dict:
    """Quick risk assessment for a hypothetical XAUUSD position.

    Combines: current spread regime, tick velocity (slippage risk),
    Asian box state (range expectation), upcoming high-impact events
    (event risk).

    Args:
        side: "long" or "short".
        entry_price: planned entry.
        stop_price: planned stop loss.
        size_usd: notional size in USD.
    """
    side = side.lower().strip()
    if side not in ("long", "short"):
        return {"error": "side must be 'long' or 'short'"}

    risk_usd = abs(entry_price - stop_price) * (size_usd / entry_price)
    risk_pct = abs(entry_price - stop_price) / entry_price * 100

    spread = _safe(microstructure.get_spread_stats, lookback_hours=24)
    velocity = _safe(microstructure.get_tick_velocity, window_seconds=300)
    news = _safe(news_calendar_adapter.get_news_calendar,
                 lookforward_days=2, lookback_days=0, min_impact="high")
    asian = _safe(strategy_adapter.get_xau_asian_box_stats)

    flags = []
    if isinstance(spread, dict) and (spread.get("current_percentile") or 0) > 80:
        flags.append("Spread is wider than usual - execution slippage risk elevated.")
    if isinstance(velocity, dict):
        interp = velocity.get("interpretation", "")
        if "explosive" in interp or "news" in interp:
            flags.append("Tick activity is news-burst-like - momentum risk both ways.")
    if isinstance(news, dict) and news.get("upcoming_high_impact_usd_count", 0) > 0:
        flags.append("Upcoming high-impact USD event(s) within 48h - hold-through risk.")

    return {
        "position": {
            "side": side,
            "entry": entry_price,
            "stop": stop_price,
            "size_usd": size_usd,
            "risk_usd": round(risk_usd, 2),
            "risk_pct": round(risk_pct, 3),
        },
        "context": {
            "spread_regime": spread,
            "tick_activity": velocity,
            "upcoming_events": news,
            "asian_box_context": asian,
        },
        "flags": flags,
        "summary": (
            f"{side.upper()} {size_usd:,.0f} USD risking ${risk_usd:,.0f} "
            f"({risk_pct:.2f}%). " + (" ".join(flags) if flags else "No elevated context risks flagged.")
        ),
    }
