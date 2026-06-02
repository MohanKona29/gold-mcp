"""Multi-Timeframe (MTF) confluence engine — Ultra tier.

Composite confluence score across D1 (trend) → H4 (momentum) → H1
(entry) timeframes. Higher score = more independent timeframes agree.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import yfinance as yf

from .config import YF_SYMBOL


def _fetch(timeframe: str, period: str) -> pd.DataFrame | None:
    df = yf.download(YF_SYMBOL, period=period, interval=timeframe,
                     progress=False, auto_adjust=True)
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    return df


def _trend_score(df: pd.DataFrame) -> dict:
    closes = df["close"]
    sma20 = closes.rolling(20).mean()
    sma50 = closes.rolling(50).mean()
    last_close = float(closes.iloc[-1])
    last_sma20 = float(sma20.iloc[-1])
    last_sma50 = float(sma50.iloc[-1])

    score = 0
    if last_close > last_sma20:
        score += 1
    if last_close > last_sma50:
        score += 1
    if last_sma20 > last_sma50:
        score += 1
    direction = "bullish" if score >= 2 else "bearish" if score <= 1 else "neutral"

    # Trend strength (ADX-like simplification)
    high_low = df["high"] - df["low"]
    atr = high_low.rolling(14).mean()
    slope = (last_sma20 - sma20.iloc[-14]) / 14 if len(sma20.dropna()) >= 14 else 0
    strength = abs(slope) / atr.iloc[-1] if atr.iloc[-1] > 0 else 0

    return {
        "score": score,
        "direction": direction,
        "last_close": round(last_close, 4),
        "sma_20": round(last_sma20, 4),
        "sma_50": round(last_sma50, 4),
        "trend_strength_atr": round(float(strength), 4),
    }


def _momentum_score(df: pd.DataFrame) -> dict:
    closes = df["close"]
    delta = closes.diff().dropna()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.where(loss != 0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    last_rsi = float(rsi.dropna().iloc[-1]) if not rsi.dropna().empty else 50.0

    ema_f = closes.ewm(span=12, adjust=False).mean()
    ema_s = closes.ewm(span=26, adjust=False).mean()
    macd = ema_f - ema_s
    sig = macd.ewm(span=9, adjust=False).mean()
    hist = macd - sig
    last_hist = float(hist.iloc[-1])

    score = 0
    if last_rsi > 50:
        score += 1
    if last_rsi > 60:
        score += 1
    if last_hist > 0:
        score += 1
    if last_hist > hist.iloc[-2]:
        score += 1
    direction = "bullish" if score >= 3 else "bearish" if score <= 1 else "neutral"
    return {
        "score": score,
        "direction": direction,
        "rsi_14": round(last_rsi, 2),
        "macd_hist": round(last_hist, 5),
    }


def mtf_alignment(d1_period: str = "180d", h4_period: str = "60d",
                  h1_period: str = "30d") -> dict:
    """Composite confluence across D1 / H4 / H1 for XAUUSD.

    Returns a composite score 0-100 where higher = more timeframes
    aligned in the same direction.
    """
    d1 = _fetch("1d", d1_period)
    h4 = _fetch("4h", h4_period)
    h1 = _fetch("1h", h1_period)
    if d1 is None or len(d1) < 50:
        return {"error": "insufficient_d1_data"}
    if h4 is None or len(h4) < 50:
        return {"error": "insufficient_h4_data"}
    if h1 is None or len(h1) < 30:
        return {"error": "insufficient_h1_data"}

    d1_trend = _trend_score(d1)
    h4_trend = _trend_score(h4)
    h1_mom = _momentum_score(h1)

    # Count aligned-bullish / aligned-bearish
    directions = [d1_trend["direction"], h4_trend["direction"], h1_mom["direction"]]
    bull_count = directions.count("bullish")
    bear_count = directions.count("bearish")

    if bull_count == 3:
        composite = "fully_aligned_bullish"
        score = 100
    elif bear_count == 3:
        composite = "fully_aligned_bearish"
        score = 100
    elif bull_count == 2:
        composite = "partial_bullish"
        score = 66
    elif bear_count == 2:
        composite = "partial_bearish"
        score = 66
    else:
        composite = "no_alignment"
        score = 33

    return {
        "symbol": "XAUUSD",
        "d1_trend": d1_trend,
        "h4_trend": h4_trend,
        "h1_momentum": h1_mom,
        "alignment_score": score,
        "composite": composite,
        "bullish_timeframes": bull_count,
        "bearish_timeframes": bear_count,
        "trading_implication": {
            "fully_aligned_bullish": "All TFs bullish — trend continuation high probability.",
            "fully_aligned_bearish": "All TFs bearish — trend continuation high probability.",
            "partial_bullish": "Majority bullish — wait for laggard TF to confirm.",
            "partial_bearish": "Majority bearish — wait for laggard TF to confirm.",
            "no_alignment": "TFs disagree — reduce size or stay flat.",
        }[composite],
    }
