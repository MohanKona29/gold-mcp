"""Tick-level microstructure analytics for XAUUSD.

Built on the daily tick archive resolved from `GOLD_MCP_TICKS_DIR`.
These tools are the core differentiator of the server because the
underlying data is several months of MT5 tick history — something
retail traders almost never have direct access to.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from .config import TICKS_DIR


def _list_tick_files() -> list:
    return sorted(TICKS_DIR.glob("XAUUSD_ticks_*.parquet"))


def _load_tail_ticks(days: int = 1) -> pd.DataFrame:
    files = _list_tick_files()
    if not files:
        return pd.DataFrame()
    selected = files[-days:] if days > 0 else files
    frames = [pd.read_parquet(f) for f in selected]
    df = pd.concat(frames, ignore_index=True)
    df["mid"] = (df["bid"] + df["ask"]) / 2
    df["spread"] = df["ask"] - df["bid"]
    df = df.sort_values("time_msc").reset_index(drop=True)
    return df


def get_tick_velocity(window_seconds: int = 60) -> dict:
    """Recent tick activity intensity (ticks/sec) and price movement per tick.

    Useful to detect bursts of activity vs. quiet markets.
    """
    df = _load_tail_ticks(days=1)
    if df.empty:
        return {"error": "no tick data"}

    cutoff = df["time_msc"].max() - pd.Timedelta(seconds=window_seconds)
    recent = df[df["time_msc"] >= cutoff]
    if len(recent) < 2:
        return {"error": "insufficient ticks in window"}

    duration = (recent["time_msc"].max() - recent["time_msc"].min()).total_seconds()
    if duration <= 0:
        return {"error": "zero duration"}

    n_ticks = len(recent)
    price_change = float(recent["mid"].iloc[-1] - recent["mid"].iloc[0])
    abs_movement = float(recent["mid"].diff().abs().sum())

    return {
        "window_seconds": window_seconds,
        "asof": pd.Timestamp(recent["time_msc"].iloc[-1]).isoformat(),
        "tick_count": int(n_ticks),
        "actual_window_sec": round(duration, 2),
        "ticks_per_sec": round(n_ticks / duration, 2),
        "price_change": round(price_change, 3),
        "abs_movement": round(abs_movement, 3),
        "movement_per_tick": round(abs_movement / n_ticks, 4),
        "interpretation": _velocity_interpretation(n_ticks / duration, abs_movement / n_ticks),
    }


def _velocity_interpretation(tps: float, mpt: float) -> str:
    if tps < 1:
        intensity = "very quiet"
    elif tps < 3:
        intensity = "quiet"
    elif tps < 8:
        intensity = "normal"
    elif tps < 15:
        intensity = "active"
    else:
        intensity = "very active / news-driven"

    if mpt < 0.005:
        character = "minimal price impact"
    elif mpt < 0.02:
        character = "small ticks"
    elif mpt < 0.05:
        character = "larger ticks"
    else:
        character = "explosive ticks (likely news)"
    return f"{intensity}, {character}"


def get_spread_stats(lookback_hours: int = 24) -> dict:
    """Spread distribution over recent history.

    Reports median, P75, P95, P99 — useful to know whether the current
    spread is normal or wide (illiquid).
    """
    days = max(1, int(np.ceil(lookback_hours / 20)))
    df = _load_tail_ticks(days=days)
    if df.empty:
        return {"error": "no tick data"}

    cutoff = df["time_msc"].max() - pd.Timedelta(hours=lookback_hours)
    recent = df[df["time_msc"] >= cutoff]
    if len(recent) < 100:
        return {"error": "insufficient ticks"}

    spreads = recent["spread"].values
    current = float(recent["spread"].iloc[-1])

    pct_rank = float((spreads <= current).mean() * 100)

    return {
        "lookback_hours": lookback_hours,
        "tick_count": int(len(recent)),
        "current_spread": round(current, 3),
        "current_percentile": round(pct_rank, 1),
        "median": round(float(np.median(spreads)), 3),
        "p25": round(float(np.percentile(spreads, 25)), 3),
        "p75": round(float(np.percentile(spreads, 75)), 3),
        "p95": round(float(np.percentile(spreads, 95)), 3),
        "p99": round(float(np.percentile(spreads, 99)), 3),
        "max": round(float(np.max(spreads)), 3),
        "interpretation": (
            f"Current spread {current:.2f} is at the {pct_rank:.0f}th percentile of the last "
            f"{lookback_hours}h. "
            + (
                "Wider than usual — possibly news or low liquidity."
                if pct_rank > 80
                else (
                    "Tight — normal liquidity."
                    if pct_rank < 50
                    else "Within normal range."
                )
            )
        ),
    }


def get_session_microstructure(lookback_days: int = 20) -> dict:
    """Asia / Europe / US session character: tick rate, range, average spread.

    Sessions (UTC):
      Asia    00:00 - 07:00
      Europe  07:00 - 13:00
      US      13:00 - 21:00
      Off     21:00 - 24:00
    """
    df = _load_tail_ticks(days=lookback_days)
    if df.empty:
        return {"error": "no tick data"}

    df["hour"] = df["time_msc"].dt.hour
    df["session"] = pd.cut(
        df["hour"],
        bins=[-1, 6, 12, 20, 23],
        labels=["Asia", "Europe", "US", "Off"],
        ordered=False,
    ).astype(str)

    out = {}
    for sess in ["Asia", "Europe", "US"]:
        s = df[df["session"] == sess]
        if s.empty:
            continue
        # Group by date to compute per-day range, average ticks, etc.
        per_day = s.groupby(s["time_msc"].dt.date).agg(
            tick_count=("mid", "size"),
            high=("ask", "max"),
            low=("bid", "min"),
            avg_spread=("spread", "mean"),
        )
        per_day["range"] = per_day["high"] - per_day["low"]
        if per_day.empty:
            continue
        out[sess] = {
            "avg_ticks_per_session": round(float(per_day["tick_count"].mean()), 0),
            "avg_range_usd": round(float(per_day["range"].mean()), 2),
            "avg_spread": round(float(per_day["avg_spread"].mean()), 3),
            "n_sessions": int(len(per_day)),
        }

    if not out:
        return {"error": "no session data"}

    most_active = max(out, key=lambda k: out[k]["avg_ticks_per_session"])
    widest_range = max(out, key=lambda k: out[k]["avg_range_usd"])

    return {
        "lookback_days": lookback_days,
        "sessions": out,
        "most_active_session": most_active,
        "widest_range_session": widest_range,
        "interpretation": (
            f"Last {lookback_days} days: {most_active} session has the highest tick "
            f"activity; {widest_range} session has the widest average range."
        ),
    }


def get_data_freshness() -> dict:
    """Health check: how recent is the data feeding this server?"""
    files = _list_tick_files()
    if not files:
        return {"status": "no_data", "error": "no tick files found"}

    df = pd.read_parquet(files[-1])
    if df.empty:
        return {"status": "empty", "error": "latest file empty"}

    last_ts = pd.Timestamp(df["time_msc"].iloc[-1])
    if last_ts.tzinfo is None:
        last_ts = last_ts.tz_localize("UTC")
    now = pd.Timestamp.now(tz="UTC")
    age_sec = (now - last_ts).total_seconds()

    if age_sec < 60:
        status = "live"
    elif age_sec < 3600:
        status = "recent"
    elif age_sec < 86400:
        status = "stale"
    else:
        status = "very_stale"

    return {
        "status": status,
        "last_tick_time": last_ts.isoformat(),
        "age_seconds": int(age_sec),
        "age_human": _humanize_age(age_sec),
        "tick_days_available": len(files),
        "earliest_day": files[0].name,
        "warning": (
            None
            if status in ("live", "recent")
            else f"Tick data is {_humanize_age(age_sec)} old. Stream may be down."
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
