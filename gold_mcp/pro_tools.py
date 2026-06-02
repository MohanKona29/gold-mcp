"""Pro-tier tools for gold-mcp: advanced TA, alerts, multi-timeframe.

All tools operate on Yahoo data (BYOK for Free tier is N/A — gold-mcp
intentionally uses public futures data). Pro tier adds richer
derivations on top of the same data feed.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from .config import MACRO_SYMBOLS, YF_SYMBOL


def _closes(bars: list[dict]) -> pd.Series:
    return pd.Series([float(b["close"]) for b in bars])


def _highs(bars): return pd.Series([float(b["high"]) for b in bars])
def _lows(bars):  return pd.Series([float(b["low"])  for b in bars])


# ---------- Advanced TA (Bollinger, Ichimoku, Fib) ----------

def _bollinger(bars: list[dict], window: int = 20, num_std: float = 2.0) -> dict:
    closes = _closes(bars)
    if len(closes) < window:
        return {"error": "insufficient_data"}
    mid = closes.rolling(window).mean()
    std = closes.rolling(window).std()
    upper, lower = mid + num_std * std, mid - num_std * std
    last = float(closes.iloc[-1])
    up_v, lo_v, mid_v = float(upper.iloc[-1]), float(lower.iloc[-1]), float(mid.iloc[-1])
    return {
        "upper": round(up_v, 4), "middle": round(mid_v, 4), "lower": round(lo_v, 4),
        "last_close": round(last, 4),
        "bandwidth_pct": round((up_v - lo_v) / mid_v * 100, 3) if mid_v else None,
        "pct_b": round((last - lo_v) / (up_v - lo_v), 3) if up_v != lo_v else None,
        "signal": ("above_upper" if last > up_v else
                   "below_lower" if last < lo_v else "inside_band"),
    }


def _ichimoku(bars: list[dict]) -> dict:
    if len(bars) < 52:
        return {"error": "insufficient_data", "need": 52}
    hi, lo, c = _highs(bars), _lows(bars), _closes(bars)
    tenkan = (hi.rolling(9).max() + lo.rolling(9).min()) / 2
    kijun = (hi.rolling(26).max() + lo.rolling(26).min()) / 2
    span_a = ((tenkan + kijun) / 2).shift(26)
    span_b = ((hi.rolling(52).max() + lo.rolling(52).min()) / 2).shift(26)
    last_c = float(c.iloc[-1])
    last_t, last_k = float(tenkan.iloc[-1]), float(kijun.iloc[-1])
    last_sa = float(span_a.iloc[-1]) if not pd.isna(span_a.iloc[-1]) else None
    last_sb = float(span_b.iloc[-1]) if not pd.isna(span_b.iloc[-1]) else None
    if last_sa is None or last_sb is None:
        position = "cloud_forming"
    else:
        top, bot = max(last_sa, last_sb), min(last_sa, last_sb)
        position = ("above_cloud_bullish" if last_c > top else
                    "below_cloud_bearish" if last_c < bot else
                    "inside_cloud_neutral")
    return {
        "tenkan_sen": round(last_t, 4),
        "kijun_sen": round(last_k, 4),
        "senkou_span_a": round(last_sa, 4) if last_sa else None,
        "senkou_span_b": round(last_sb, 4) if last_sb else None,
        "last_close": round(last_c, 4),
        "cross_signal": "bullish_tk_cross" if last_t > last_k else "bearish_tk_cross",
        "cloud_position": position,
    }


def _fibonacci(bars: list[dict], lookback: int = 60) -> dict:
    if len(bars) < lookback:
        return {"error": "insufficient_data"}
    sub = bars[-lookback:]
    swing_hi = max(float(b["high"]) for b in sub)
    swing_lo = min(float(b["low"]) for b in sub)
    diff = swing_hi - swing_lo
    levels = {
        "0.0": swing_lo,
        "0.236": swing_lo + diff * 0.236,
        "0.382": swing_lo + diff * 0.382,
        "0.500": swing_lo + diff * 0.500,
        "0.618": swing_lo + diff * 0.618,
        "0.786": swing_lo + diff * 0.786,
        "1.0": swing_hi,
    }
    last = float(bars[-1]["close"])
    nearest = min(levels, key=lambda k: abs(levels[k] - last))
    return {
        "swing_high": round(swing_hi, 4),
        "swing_low": round(swing_lo, 4),
        "levels": {k: round(v, 4) for k, v in levels.items()},
        "last_close": round(last, 4),
        "nearest_level": nearest,
    }


def analyze_gold_advanced(timeframe: str = "1h", lookback: int = 120) -> dict:
    """Bollinger + Ichimoku + Fib on XAUUSD."""
    from .gold_data import get_gold_ohlcv
    bars_resp = get_gold_ohlcv(timeframe=timeframe, lookback=lookback)
    if "error" in bars_resp:
        return bars_resp
    bars = bars_resp["bars"]
    return {
        "symbol": "XAUUSD", "timeframe": timeframe,
        "bollinger": _bollinger(bars),
        "ichimoku": _ichimoku(bars),
        "fibonacci": _fibonacci(bars),
        "n_bars": len(bars),
        "source": "yfinance",
    }


# ---------- Multi-timeframe snapshot ----------

def multi_timeframe_snapshot(timeframes: list[str] | None = None) -> dict:
    """Pull gold OHLCV across several timeframes in one call.

    Args:
        timeframes: e.g. ["5m", "1h", "4h", "1d"]. Defaults to those four.
    """
    from .gold_data import get_gold_ohlcv
    tfs = timeframes or ["5m", "1h", "4h", "1d"]
    out = {}
    for tf in tfs:
        bars = get_gold_ohlcv(timeframe=tf, lookback=50)
        if "error" in bars:
            out[tf] = {"error": bars["error"]}
            continue
        b = bars["bars"]
        closes = _closes(b)
        if len(closes) < 14:
            out[tf] = {"error": "insufficient"}
            continue
        delta = closes.diff().dropna()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.where(loss != 0, np.nan)
        rsi = 100 - 100 / (1 + rs)
        last_close = float(closes.iloc[-1])
        first_close = float(closes.iloc[0])
        out[tf] = {
            "last_close": round(last_close, 3),
            "first_close": round(first_close, 3),
            "return_pct": round((last_close - first_close) / first_close * 100, 3),
            "rsi_14": round(float(rsi.dropna().iloc[-1]), 2) if not rsi.dropna().empty else None,
            "n_bars": len(b),
        }
    return {"symbol": "XAUUSD", "snapshots": out}


# ---------- Correlation regime detection ----------

def gold_correlation_regime(lookback_short: int = 20, lookback_long: int = 60) -> dict:
    """Detect regime shifts in gold ↔ macro correlations.

    Flags assets where the short-window correlation has diverged
    significantly from the long-window — e.g. "DXY decoupling".
    """
    symbols = {"GOLD": YF_SYMBOL, **MACRO_SYMBOLS}
    tickers = list(symbols.values())
    period = f"{lookback_long + 20}d"
    data = yf.download(tickers, period=period, interval="1d",
                       progress=False, auto_adjust=True)
    if data is None or data.empty:
        return {"error": "no_data"}
    closes = data["Close"] if isinstance(data.columns, pd.MultiIndex) else data
    rename = {v: k for k, v in symbols.items() if v in closes.columns}
    closes = closes.rename(columns=rename)
    returns = closes.pct_change().dropna()
    if "GOLD" not in returns.columns or len(returns) < lookback_long:
        return {"error": "insufficient_data"}

    short_corr = returns.tail(lookback_short).corr()["GOLD"].drop("GOLD")
    long_corr = returns.tail(lookback_long).corr()["GOLD"].drop("GOLD")
    regime = {}
    for asset in short_corr.index:
        short_val = float(short_corr[asset])
        long_val = float(long_corr[asset])
        delta = short_val - long_val
        if abs(delta) > 0.3:
            tag = "decoupling" if abs(short_val) < abs(long_val) else "tightening"
        else:
            tag = "stable"
        regime[asset] = {
            "short_corr": round(short_val, 3),
            "long_corr": round(long_val, 3),
            "delta": round(delta, 3),
            "regime": tag,
        }
    notable = {k: v for k, v in regime.items() if v["regime"] != "stable"}
    return {
        "asof": str(returns.index[-1]),
        "lookback_short": lookback_short,
        "lookback_long": lookback_long,
        "regime": regime,
        "notable_shifts": notable,
    }


# ---------- Setup detection (multi-indicator scan) ----------

def get_gold_setups(timeframe: str = "1h", lookback: int = 100) -> dict:
    """Scan for confluence: oversold + below Bollinger + Ichimoku bearish, etc."""
    from .gold_data import get_gold_ohlcv
    bars_resp = get_gold_ohlcv(timeframe=timeframe, lookback=lookback)
    if "error" in bars_resp:
        return bars_resp
    bars = bars_resp["bars"]
    closes = _closes(bars)
    if len(closes) < 52:
        return {"error": "insufficient_data"}

    delta = closes.diff().dropna()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.where(loss != 0, np.nan)
    rsi = float((100 - 100 / (1 + rs)).dropna().iloc[-1])

    boll = _bollinger(bars)
    ichi = _ichimoku(bars)

    signals = []
    if rsi < 30:
        signals.append({"type": "rsi_oversold", "value": round(rsi, 2)})
    if rsi > 70:
        signals.append({"type": "rsi_overbought", "value": round(rsi, 2)})
    if boll.get("signal") == "below_lower":
        signals.append({"type": "bollinger_breach_below", "value": boll["last_close"]})
    if boll.get("signal") == "above_upper":
        signals.append({"type": "bollinger_breach_above", "value": boll["last_close"]})
    if ichi.get("cloud_position") == "above_cloud_bullish":
        signals.append({"type": "ichimoku_above_cloud"})
    if ichi.get("cloud_position") == "below_cloud_bearish":
        signals.append({"type": "ichimoku_below_cloud"})

    # Confluence
    bullish_count = sum(1 for s in signals if s["type"] in
                        ("rsi_oversold", "bollinger_breach_below", "ichimoku_above_cloud"))
    bearish_count = sum(1 for s in signals if s["type"] in
                        ("rsi_overbought", "bollinger_breach_above", "ichimoku_below_cloud"))

    return {
        "symbol": "XAUUSD", "timeframe": timeframe,
        "n_bars": len(bars),
        "signals": signals,
        "bullish_confluence": bullish_count,
        "bearish_confluence": bearish_count,
        "rsi_14": round(rsi, 2),
        "bollinger_signal": boll.get("signal"),
        "ichimoku_cloud_position": ichi.get("cloud_position"),
    }


# ---------- Alerts ----------

def _alerts_path() -> Path:
    raw = os.environ.get("GOLD_MCP_ALERTS_DIR", "").strip()
    base = Path(raw).expanduser() if raw else Path.home() / ".cache" / "gold-mcp"
    base.mkdir(parents=True, exist_ok=True)
    return base / "alerts.json"


def list_gold_alerts() -> list[dict]:
    path = _alerts_path()
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def create_gold_alert(condition: str, threshold: float,
                      webhook_url: str | None = None) -> dict:
    """Create a gold alert rule. Pro tier.

    Args:
        condition: price_above | price_below | rsi_above | rsi_below |
                   premium_above (VN gold premium %)
        threshold: numeric threshold
        webhook_url: optional Discord/Slack webhook
    """
    valid = ("price_above", "price_below", "rsi_above", "rsi_below", "premium_above")
    if condition not in valid:
        return {"error": "unknown_condition", "valid": list(valid)}
    alerts = list_gold_alerts()
    new = {
        "id": int(time.time() * 1000),
        "symbol": "XAUUSD",
        "condition": condition,
        "threshold": float(threshold),
        "webhook_url": webhook_url,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    alerts.append(new)
    _alerts_path().write_text(json.dumps(alerts, indent=2), encoding="utf-8")
    return {"created": new, "total_alerts": len(alerts)}


def delete_gold_alert(alert_id: int) -> dict:
    alerts = list_gold_alerts()
    remaining = [a for a in alerts if a.get("id") != alert_id]
    if len(remaining) == len(alerts):
        return {"error": "alert_not_found", "id": alert_id}
    _alerts_path().write_text(json.dumps(remaining, indent=2), encoding="utf-8")
    return {"deleted_id": alert_id, "remaining": len(remaining)}
