"""Adapters for the XAUUSD strategy engine result artifacts.

Wraps precomputed analysis JSON/CSV outputs produced by the user's
research pipeline. Absolute source paths inside the files are stripped
before returning, so the public MCP never reveals where the source
data lives.
"""
from __future__ import annotations

import json

from ._paths import not_configured, strategy_results_dir

_PRIVATE_KEYS = {"source", "input_path", "data_path", "file_path", "path"}


def _sanitize(obj):
    """Recursively strip any keys that could reveal user-local paths."""
    if isinstance(obj, dict):
        return {
            k: _sanitize(v)
            for k, v in obj.items()
            if k.lower() not in _PRIVATE_KEYS
        }
    if isinstance(obj, list):
        return [_sanitize(x) for x in obj]
    return obj


def _load_json(filename: str) -> dict | None:
    base = strategy_results_dir()
    if base is None:
        return None
    path = base / filename
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return _sanitize(json.load(f))
    except Exception:
        return None


# ---------- Daily setup scanner ----------

def get_xau_daily_setup_config() -> dict:
    """Optimized parameters + summary stats of the daily-setup scanner."""
    data = _load_json("daily_setups_summary.json")
    if data is None:
        if strategy_results_dir() is None:
            return not_configured("get_xau_daily_setup_config", "GOLD_MCP_STRATEGY_RESULTS_DIR")
        return {"error": "file_not_found", "filename": "daily_setups_summary.json"}

    cfg = data.get("config", {})
    perf = {k: v for k, v in data.items() if k != "config"}
    return {
        "summary": (
            "Backtested intraday setup scanner combining swing structure, "
            "volume z-score, wick rejection, and time-of-day filters. "
            "Configuration below is the locked OOS parameter set."
        ),
        "config": cfg,
        "performance": perf,
    }


# ---------- Asian box ----------

def get_xau_asian_box_stats() -> dict:
    """Asian-session box stats + range-expansion correlations by state."""
    data = _load_json("asian_box_analysis.json")
    if data is None:
        if strategy_results_dir() is None:
            return not_configured("get_xau_asian_box_stats", "GOLD_MCP_STRATEGY_RESULTS_DIR")
        return {"error": "file_not_found"}

    cfg = data.get("config", {})
    dist = data.get("state_distribution", {})
    h1 = data.get("hypothesis_1_table", [])

    by_state = {row["state"]: row for row in h1}
    interp_parts = []
    if "EXPANDED" in by_state and "TIGHT" in by_state:
        exp_range = by_state["EXPANDED"].get("sess_range_mean", 0)
        tight_range = by_state["TIGHT"].get("sess_range_mean", 0)
        if exp_range and tight_range:
            ratio = exp_range / tight_range
            interp_parts.append(
                f"After an EXPANDED Asian box, the day's London/NY range is "
                f"{ratio:.1f}x larger on average than after a TIGHT box."
            )

    return {
        "summary": (
            "Distribution and behavior of the Asian-session box state. "
            "An EXPANDED Asian box historically precedes wider London/NY range; "
            "a TIGHT box favors mean-reversion."
        ),
        "config": cfg,
        "state_distribution": dist,
        "by_state": by_state,
        "interpretation": " ".join(interp_parts) if interp_parts else None,
        "total_days": data.get("total_days"),
    }


# ---------- Institutional footprint ----------

def get_xau_institutional_footprint() -> dict:
    """Historical institutional footprint signature on XAUUSD."""
    data = _load_json("institutional_footprint.json")
    if data is None:
        if strategy_results_dir() is None:
            return not_configured("get_xau_institutional_footprint", "GOLD_MCP_STRATEGY_RESULTS_DIR")
        return {"error": "file_not_found"}
    return {
        "summary": (
            "Footprint signature combining absorption, large-prints, and "
            "imbalance patterns observed historically on XAUUSD."
        ),
        "data": data,
    }


# ---------- Gamma regime ----------

def get_xau_gamma_regime() -> dict:
    """Gamma-regime state distribution and behavior on XAUUSD."""
    data = _load_json("gamma_regime_analysis.json")
    if data is None:
        if strategy_results_dir() is None:
            return not_configured("get_xau_gamma_regime", "GOLD_MCP_STRATEGY_RESULTS_DIR")
        return {"error": "file_not_found"}
    return {
        "summary": (
            "Empirically derived gamma-regime classification (POS/NEG/NEUTRAL) "
            "and its effect on daily behavior."
        ),
        "data": data,
    }


# ---------- Trend entry signature ----------

def get_xau_trend_entry_signature() -> dict:
    """Statistical signature of clean trend entries on XAUUSD."""
    data = _load_json("trend_entry_signature.json")
    if data is None:
        if strategy_results_dir() is None:
            return not_configured("get_xau_trend_entry_signature", "GOLD_MCP_STRATEGY_RESULTS_DIR")
        return {"error": "file_not_found"}
    return {
        "summary": (
            "Pattern signature of high-quality trend entries derived from "
            "OOS-validated backtest analysis."
        ),
        "data": data,
    }
