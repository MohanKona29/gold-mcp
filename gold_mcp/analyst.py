"""Aggregator tool that combines the public-data tools into a single read.

Educational only — returns raw numbers and statistical context, no
trading recommendation. Downstream LLMs can decide how to phrase the
read for the user.
"""
from __future__ import annotations

from . import analytics, gold_data, macro_data
from .adapters import vn_macro as vn_macro_adapter


def _safe(fn, *args, **kwargs):
    try:
        out = fn(*args, **kwargs)
        return out if isinstance(out, dict) else {"error": "non_dict_return"}
    except Exception as e:
        return {"error": "exception", "detail": str(e)}


def gold_market_snapshot(timeframe: str = "1h") -> dict:
    """One-call structured snapshot of gold's current market state.

    Aggregates the public-data tools (price, recent bars, macro context,
    correlations, seasonality, VN parity) into a single structured
    object plus a concise bulleted summary of the most salient numbers.

    Args:
        timeframe: Bar timeframe used for recent_bars (default "1h").
    """
    price = _safe(gold_data.get_gold_price)
    bars = _safe(gold_data.get_gold_ohlcv, timeframe=timeframe, lookback=12)
    macro = _safe(macro_data.get_macro_context)
    correlations = _safe(macro_data.get_correlation_matrix, lookback_days=60)
    seasonality = _safe(analytics.get_seasonality, group_by="dow", lookback_years=5)
    vn = _safe(vn_macro_adapter.get_vn_macro)

    bullets = []
    if isinstance(price, dict) and price.get("last") is not None:
        chg = price.get("change_24h_pct")
        if chg is not None:
            bullets.append(f"Gold {price['last']} ({chg:+.2f}% 24h).")
        else:
            bullets.append(f"Gold {price['last']}.")

    if isinstance(macro, dict):
        data = macro.get("data", {})
        legs = []
        for k in ("DXY", "US10Y", "VIX"):
            if k in data and "change_pct" in data[k]:
                legs.append(f"{k} {data[k]['change_pct']:+.2f}%")
        if legs:
            bullets.append("Macro: " + ", ".join(legs) + ".")

    if isinstance(correlations, dict):
        gc = correlations.get("gold_correlations", {})
        if gc:
            top_pos = max(gc.items(), key=lambda x: x[1])
            top_neg = min(gc.items(), key=lambda x: x[1])
            bullets.append(
                f"60d correlation: strongest with {top_pos[0]} ({top_pos[1]:+.2f}), "
                f"most negative with {top_neg[0]} ({top_neg[1]:+.2f})."
            )

    if isinstance(vn, dict):
        parity = vn.get("world_parity_gold", {})
        per_tael = parity.get("vnd_per_tael_millions")
        if per_tael:
            bullets.append(f"VN world-parity reference: {per_tael}M VND/tael.")

    return {
        "timeframe": timeframe,
        "summary_bullets": bullets,
        "price": price,
        "recent_bars": bars,
        "macro_snapshot": macro,
        "macro_correlations": correlations,
        "seasonality_dow": seasonality,
        "vn_context": vn,
        "disclaimer": (
            "This is a data snapshot for educational and research purposes only. "
            "Not financial advice."
        ),
    }
