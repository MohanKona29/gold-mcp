"""Tick data access + OHLCV resampling for XAUUSD."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from .config import TICKS_DIR

_TF_RULES = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "1h",
    "4h": "4h",
    "1d": "1D",
}


def _list_tick_files() -> list:
    if not TICKS_DIR or not TICKS_DIR.exists():
        return []
    return sorted(TICKS_DIR.glob("XAUUSD_ticks_*.parquet"))


def _load_recent_ticks(days: int = 1) -> pd.DataFrame:
    files = _list_tick_files()
    if not files:
        return pd.DataFrame()
    selected = files[-days:] if days > 0 else files
    frames = [pd.read_parquet(f) for f in selected]
    df = pd.concat(frames, ignore_index=True)
    df["mid"] = (df["bid"] + df["ask"]) / 2
    return df


def get_latest_price() -> dict:
    files = _list_tick_files()
    if not files:
        return {"error": "no tick data available", "ticks_dir": str(TICKS_DIR)}
    df = pd.read_parquet(files[-1])
    last = df.iloc[-1]
    bid = float(last["bid"])
    ask = float(last["ask"])
    return {
        "timestamp": pd.Timestamp(last["time_msc"]).isoformat(),
        "bid": bid,
        "ask": ask,
        "mid": (bid + ask) / 2,
        "spread": ask - bid,
        "spread_bps": (ask - bid) / bid * 10_000,
        "source_file": files[-1].name,
    }


def get_ohlcv(timeframe: str = "1h", lookback: int = 24) -> dict:
    if timeframe not in _TF_RULES:
        return {
            "error": f"unsupported timeframe '{timeframe}'",
            "supported": list(_TF_RULES.keys()),
        }

    days_needed = max(2, int(lookback * _tf_to_hours(timeframe) / 24) + 2)
    df = _load_recent_ticks(days=days_needed)
    if df.empty:
        return {"error": "no tick data available"}

    df = df.set_index("time_msc").sort_index()
    bars = df["mid"].resample(_TF_RULES[timeframe]).ohlc()
    bars["volume"] = df["volume_real"].resample(_TF_RULES[timeframe]).sum()
    bars = bars.dropna(subset=["open"]).tail(lookback)

    return {
        "timeframe": timeframe,
        "lookback": lookback,
        "rows": len(bars),
        "bars": [
            {
                "time": idx.isoformat(),
                "open": round(row.open, 3),
                "high": round(row.high, 3),
                "low": round(row.low, 3),
                "close": round(row.close, 3),
                "volume": float(row.volume) if pd.notna(row.volume) else 0.0,
            }
            for idx, row in bars.iterrows()
        ],
    }


def _tf_to_hours(tf: str) -> float:
    mapping = {"1m": 1 / 60, "5m": 5 / 60, "15m": 0.25, "30m": 0.5, "1h": 1, "4h": 4, "1d": 24}
    return mapping.get(tf, 1)


def get_session_summary() -> dict:
    """Today's session: open, current, high/low, % change."""
    files = _list_tick_files()
    if not files:
        return {"error": "no tick data"}
    df = pd.read_parquet(files[-1])
    if df.empty:
        return {"error": "empty file"}
    open_px = float(df.iloc[0]["bid"])
    last = df.iloc[-1]
    last_bid = float(last["bid"])
    high = float(df["bid"].max())
    low = float(df["bid"].min())
    return {
        "date": pd.Timestamp(df.iloc[0]["time"]).date().isoformat(),
        "open": open_px,
        "last": last_bid,
        "high": high,
        "low": low,
        "range": high - low,
        "change": last_bid - open_px,
        "change_pct": (last_bid - open_px) / open_px * 100,
        "tick_count": len(df),
    }
