"""Gold (XAUUSD) price + OHLCV from Yahoo Finance.

This module is intentionally thin: it wraps `yfinance` so any MCP
client can ask for the current gold price and historical bars without
needing a broker account, tick stream, or any local data file.
"""
from __future__ import annotations

import pandas as pd
import yfinance as yf

from .config import YF_SYMBOL

_TF_TO_YF_INTERVAL = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "60m",
    "4h": "4h",
    "1d": "1d",
    "1wk": "1wk",
    "1mo": "1mo",
}


def get_gold_price() -> dict:
    """Latest gold close + intraday change from Yahoo Finance."""
    try:
        df = yf.download(YF_SYMBOL, period="2d", interval="1m", progress=False, auto_adjust=True)
    except Exception as e:
        return {"error": "yfinance_failed", "detail": str(e)}

    if df is None or df.empty:
        return {"error": "no_data"}

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    last = df.iloc[-1]
    last_close = float(last["Close"])
    last_ts = pd.Timestamp(df.index[-1])

    # Compare against the previous session close (roughly 24h back)
    cutoff = last_ts - pd.Timedelta(hours=24)
    prior = df.loc[df.index <= cutoff]
    if not prior.empty:
        prev_close = float(prior.iloc[-1]["Close"])
        change = last_close - prev_close
        change_pct = change / prev_close * 100
    else:
        change = None
        change_pct = None

    return {
        "symbol": YF_SYMBOL,
        "asof": last_ts.isoformat(),
        "last": round(last_close, 3),
        "change_24h": round(change, 3) if change is not None else None,
        "change_24h_pct": round(change_pct, 3) if change_pct is not None else None,
        "intraday_high": round(float(df["High"].iloc[-30:].max()), 3),
        "intraday_low": round(float(df["Low"].iloc[-30:].min()), 3),
        "source": "yfinance",
    }


def get_gold_ohlcv(timeframe: str = "1h", lookback: int = 24) -> dict:
    """OHLCV bars for gold.

    Args:
        timeframe: One of 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1wk, 1mo.
        lookback: Number of most recent bars to return.
    """
    if timeframe not in _TF_TO_YF_INTERVAL:
        return {
            "error": "unsupported_timeframe",
            "supported": list(_TF_TO_YF_INTERVAL.keys()),
        }

    yf_interval = _TF_TO_YF_INTERVAL[timeframe]
    # yfinance has a max history per interval; pick a sensible period
    period_map = {
        "1m": "7d", "5m": "60d", "15m": "60d", "30m": "60d",
        "60m": "730d", "4h": "730d", "1d": "10y", "1wk": "10y", "1mo": "max",
    }
    period = period_map.get(yf_interval, "60d")

    try:
        df = yf.download(YF_SYMBOL, period=period, interval=yf_interval,
                         progress=False, auto_adjust=True)
    except Exception as e:
        return {"error": "yfinance_failed", "detail": str(e)}

    if df is None or df.empty:
        return {"error": "no_data"}

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.tail(lookback)

    bars = [
        {
            "time": pd.Timestamp(idx).isoformat(),
            "open": round(float(row["Open"]), 3),
            "high": round(float(row["High"]), 3),
            "low": round(float(row["Low"]), 3),
            "close": round(float(row["Close"]), 3),
            "volume": float(row["Volume"]) if "Volume" in row and pd.notna(row["Volume"]) else 0.0,
        }
        for idx, row in df.iterrows()
    ]

    return {
        "symbol": YF_SYMBOL,
        "timeframe": timeframe,
        "lookback": lookback,
        "rows": len(bars),
        "bars": bars,
        "source": "yfinance",
    }
