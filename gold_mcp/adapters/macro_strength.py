"""Adapter for the precomputed macro strength engine output."""
from __future__ import annotations

import json

import pandas as pd

from ._paths import macro_strength_file, not_configured


def get_macro_strength() -> dict:
    path = macro_strength_file()
    if path is None:
        return not_configured("get_macro_strength", "GOLD_MCP_MACRO_STRENGTH_FILE")

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {"error": "read_failed", "detail": str(e)}

    meta = data.get("meta", {})
    rankings = data.get("rankings", [])

    # Freshness check
    gen_at = meta.get("generated_at")
    age_human = "unknown"
    is_fresh = False
    if gen_at:
        try:
            gen_dt = pd.Timestamp(gen_at)
            if gen_dt.tzinfo is None:
                gen_dt = gen_dt.tz_localize("UTC")
            age_sec = (pd.Timestamp.now(tz="UTC") - gen_dt).total_seconds()
            age_human = _humanize_age(age_sec)
            is_fresh = age_sec < 86400  # 1 day
        except Exception:
            pass

    # USD-focused interpretation (gold is inversely correlated with USD strength)
    usd = next((r for r in rankings if r.get("currency") == "USD"), None)
    usd_score = float(usd.get("macro_coefficient", 0.0)) if usd else 0.0

    gold_bias = "neutral"
    if usd_score > 2:
        gold_bias = "bearish (USD strong)"
    elif usd_score > 0.5:
        gold_bias = "mild bearish"
    elif usd_score < -2:
        gold_bias = "bullish (USD weak)"
    elif usd_score < -0.5:
        gold_bias = "mild bullish"

    # Build clean ranking output
    rank_out = []
    for r in rankings:
        rank_out.append({
            "rank": r.get("rank"),
            "currency": r.get("currency"),
            "macro_coefficient": round(float(r.get("macro_coefficient", 0.0)), 3),
            "signal": r.get("signal"),
            "event_count": r.get("event_count", 0),
        })

    return {
        "asof": gen_at,
        "age": age_human,
        "is_fresh": is_fresh,
        "reference_date": meta.get("reference_date"),
        "window_days": meta.get("rolling_window_days"),
        "decay_half_life_days": meta.get("decay_half_life_days"),
        "score_range": meta.get("score_range"),
        "rankings": rank_out,
        "usd_score": round(usd_score, 3),
        "gold_macro_bias": gold_bias,
        "interpretation": (
            f"USD macro coefficient = {usd_score:+.2f} -> gold macro bias: {gold_bias}. "
            f"Gold tends to move inversely to USD strength on macro surprises."
        ),
        "warning": (
            None
            if is_fresh
            else f"Macro strength data is {age_human} old; consider refreshing the engine."
        ),
    }


def _humanize_age(sec: float) -> str:
    if sec < 60:
        return f"{sec:.0f}s"
    if sec < 3600:
        return f"{sec/60:.1f}min"
    if sec < 86400:
        return f"{sec/3600:.1f}h"
    return f"{sec/86400:.1f}d"
