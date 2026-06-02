"""Smart Money Concepts (SMC) suite — Ultra tier.

Detects order blocks, fair value gaps, market structure (CHOCH/BOS),
and liquidity sweeps. All concepts are public-domain SMC methodology
(Larry Williams swings, Wyckoff structure, ICT FVG/OB terminology).
"""
from __future__ import annotations

import pandas as pd


def _to_df(bars: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(bars)
    return df.astype({"open": float, "high": float, "low": float,
                      "close": float, "volume": float}, errors="ignore")


# ---------- Swing points (fractal-based) ----------

def _swing_points(df: pd.DataFrame, lookaround: int = 2) -> tuple[list[int], list[int]]:
    """Indexes of swing highs and swing lows (k-bar fractals)."""
    highs, lows = [], []
    n = len(df)
    for i in range(lookaround, n - lookaround):
        window_h = df["high"].iloc[i - lookaround: i + lookaround + 1]
        window_l = df["low"].iloc[i - lookaround: i + lookaround + 1]
        if df["high"].iloc[i] == window_h.max() and (window_h == df["high"].iloc[i]).sum() == 1:
            highs.append(i)
        if df["low"].iloc[i] == window_l.min() and (window_l == df["low"].iloc[i]).sum() == 1:
            lows.append(i)
    return highs, lows


# ---------- Market structure: CHOCH / BOS ----------

def detect_market_structure(bars: list[dict], lookaround: int = 2) -> dict:
    """Label market structure: Break of Structure (BOS) and Change of Character (CHOCH).

    BOS = continuation: new higher high in uptrend (or lower low in downtrend).
    CHOCH = reversal: first lower high after uptrend (or first higher low after downtrend).
    """
    if len(bars) < 20:
        return {"error": "insufficient_data"}
    df = _to_df(bars)
    swing_highs, swing_lows = _swing_points(df, lookaround)
    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return {"error": "insufficient_swings"}

    events = []
    last_trend = None
    for i in range(2, max(len(swing_highs), len(swing_lows))):
        if i < len(swing_highs) and i < len(swing_lows):
            sh1, sh2 = swing_highs[i - 1], swing_highs[i] if i < len(swing_highs) else None
            sl1, sl2 = swing_lows[i - 1], swing_lows[i] if i < len(swing_lows) else None
            if sh2 is None or sl2 is None:
                continue
            h1, h2 = float(df["high"].iloc[sh1]), float(df["high"].iloc[sh2])
            l1, l2 = float(df["low"].iloc[sl1]), float(df["low"].iloc[sl2])

            if h2 > h1 and l2 > l1:
                event_type = "BOS_bullish" if last_trend == "up" else "CHOCH_bullish"
                last_trend = "up"
            elif h2 < h1 and l2 < l1:
                event_type = "BOS_bearish" if last_trend == "down" else "CHOCH_bearish"
                last_trend = "down"
            else:
                continue
            events.append({
                "index": int(sh2),
                "time": str(df["time"].iloc[sh2]) if "time" in df.columns else None,
                "type": event_type,
                "swing_high": round(h2, 4),
                "swing_low": round(l2, 4),
            })

    last_event = events[-1] if events else None
    return {
        "n_swing_highs": len(swing_highs),
        "n_swing_lows": len(swing_lows),
        "n_events": len(events),
        "current_trend": last_trend or "undefined",
        "last_event": last_event,
        "recent_events": events[-10:],
    }


# ---------- Order Blocks ----------

def detect_order_blocks(bars: list[dict], lookback: int = 100,
                       impulse_threshold_atr: float = 1.5) -> dict:
    """Detect bullish/bearish order blocks.

    Definition: the last opposing-color candle before an impulsive move
    that breaks a structure level. Identified as zones of likely future
    institutional re-entry.
    """
    if len(bars) < 30:
        return {"error": "insufficient_data"}
    df = _to_df(bars).tail(lookback).reset_index(drop=True)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift()).abs(),
        (df["low"] - df["close"].shift()).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()

    obs = []
    for i in range(2, len(df) - 1):
        candle_range = df["high"].iloc[i] - df["low"].iloc[i]
        atr_val = atr.iloc[i]
        if pd.isna(atr_val) or atr_val == 0:
            continue
        if candle_range < impulse_threshold_atr * atr_val:
            continue
        is_bullish = df["close"].iloc[i] > df["open"].iloc[i]
        # Find the last opposite-color candle before this impulse
        for j in range(i - 1, max(i - 5, 0), -1):
            opposite = (df["close"].iloc[j] < df["open"].iloc[j]) if is_bullish else (df["close"].iloc[j] > df["open"].iloc[j])
            if opposite:
                obs.append({
                    "type": "bullish_OB" if is_bullish else "bearish_OB",
                    "index": int(j),
                    "time": str(df["time"].iloc[j]) if "time" in df.columns else None,
                    "zone_high": round(float(df["high"].iloc[j]), 4),
                    "zone_low": round(float(df["low"].iloc[j]), 4),
                    "impulse_at_index": int(i),
                    "impulse_atr_multiple": round(float(candle_range / atr_val), 2),
                })
                break

    last_close = float(df["close"].iloc[-1])
    active = [
        o for o in obs
        if (o["type"] == "bullish_OB" and last_close > o["zone_high"])
        or (o["type"] == "bearish_OB" and last_close < o["zone_low"])
    ]
    return {
        "n_blocks_total": len(obs),
        "n_active": len(active),
        "last_close": round(last_close, 4),
        "active_blocks": active[-10:],
        "recent_all": obs[-15:],
    }


# ---------- Fair Value Gaps (FVG) ----------

def detect_fair_value_gaps(bars: list[dict], lookback: int = 100) -> dict:
    """Detect FVG (imbalance): 3-candle pattern where candle 1's high
    doesn't overlap candle 3's low (bullish FVG) or vice versa.
    """
    if len(bars) < 5:
        return {"error": "insufficient_data"}
    df = _to_df(bars).tail(lookback).reset_index(drop=True)
    fvgs = []
    for i in range(2, len(df)):
        c1_h, c1_l = float(df["high"].iloc[i - 2]), float(df["low"].iloc[i - 2])
        c3_h, c3_l = float(df["high"].iloc[i]), float(df["low"].iloc[i])
        if c3_l > c1_h:
            fvgs.append({
                "type": "bullish_FVG", "index": int(i),
                "time": str(df["time"].iloc[i]) if "time" in df.columns else None,
                "gap_low": round(c1_h, 4), "gap_high": round(c3_l, 4),
                "gap_size": round(c3_l - c1_h, 4),
            })
        elif c1_l > c3_h:
            fvgs.append({
                "type": "bearish_FVG", "index": int(i),
                "time": str(df["time"].iloc[i]) if "time" in df.columns else None,
                "gap_low": round(c3_h, 4), "gap_high": round(c1_l, 4),
                "gap_size": round(c1_l - c3_h, 4),
            })

    last_close = float(df["close"].iloc[-1])
    unfilled = [
        f for f in fvgs
        if not (f["gap_low"] <= last_close <= f["gap_high"])
    ]
    return {
        "n_fvgs_total": len(fvgs),
        "n_unfilled": len(unfilled),
        "last_close": round(last_close, 4),
        "unfilled_fvgs": unfilled[-10:],
        "recent_all": fvgs[-15:],
    }


# ---------- Liquidity Sweeps ----------

def detect_liquidity_sweeps(bars: list[dict], lookback: int = 100,
                             lookaround: int = 2,
                             reversal_within: int = 5) -> dict:
    """Detect liquidity sweeps: price breaches a prior swing high/low
    then reverses within `reversal_within` bars. Classic stop-hunt pattern.
    """
    if len(bars) < 30:
        return {"error": "insufficient_data"}
    df = _to_df(bars).tail(lookback).reset_index(drop=True)
    swing_highs, swing_lows = _swing_points(df, lookaround)
    sweeps = []
    for sh in swing_highs[:-1]:
        level = float(df["high"].iloc[sh])
        for i in range(sh + 2, min(sh + 30, len(df))):
            if df["high"].iloc[i] > level:
                # Did it close back below within reversal_within bars?
                future = df.iloc[i: i + reversal_within + 1]
                if (future["close"] < level).any():
                    sweeps.append({
                        "type": "bearish_sweep", "swing_index": int(sh),
                        "sweep_index": int(i),
                        "time": str(df["time"].iloc[i]) if "time" in df.columns else None,
                        "level_swept": round(level, 4),
                        "wick_high": round(float(df["high"].iloc[i]), 4),
                    })
                break
    for sl in swing_lows[:-1]:
        level = float(df["low"].iloc[sl])
        for i in range(sl + 2, min(sl + 30, len(df))):
            if df["low"].iloc[i] < level:
                future = df.iloc[i: i + reversal_within + 1]
                if (future["close"] > level).any():
                    sweeps.append({
                        "type": "bullish_sweep", "swing_index": int(sl),
                        "sweep_index": int(i),
                        "time": str(df["time"].iloc[i]) if "time" in df.columns else None,
                        "level_swept": round(level, 4),
                        "wick_low": round(float(df["low"].iloc[i]), 4),
                    })
                break

    sweeps.sort(key=lambda s: s["sweep_index"])
    last_close = float(df["close"].iloc[-1])
    return {
        "n_sweeps": len(sweeps),
        "last_close": round(last_close, 4),
        "recent_sweeps": sweeps[-10:],
        "last_sweep": sweeps[-1] if sweeps else None,
    }


# ---------- Composite SMC scan ----------

def smc_full_scan(bars: list[dict]) -> dict:
    """One-call SMC analysis: structure + OB + FVG + sweeps with composite bias."""
    structure = detect_market_structure(bars)
    obs = detect_order_blocks(bars)
    fvgs = detect_fair_value_gaps(bars)
    sweeps = detect_liquidity_sweeps(bars)

    bias_score = 0
    if isinstance(structure, dict) and "current_trend" in structure:
        if structure["current_trend"] == "up":
            bias_score += 2
        elif structure["current_trend"] == "down":
            bias_score -= 2

    if isinstance(obs, dict) and "active_blocks" in obs:
        for b in obs["active_blocks"]:
            bias_score += 1 if b["type"] == "bullish_OB" else -1

    if isinstance(fvgs, dict) and "unfilled_fvgs" in fvgs:
        for f in fvgs["unfilled_fvgs"]:
            bias_score += 0.5 if f["type"] == "bullish_FVG" else -0.5

    if isinstance(sweeps, dict) and sweeps.get("last_sweep"):
        ls = sweeps["last_sweep"]
        bias_score += 2 if ls["type"] == "bullish_sweep" else -2

    if bias_score >= 3:
        bias = "strongly_bullish"
    elif bias_score >= 1:
        bias = "bullish"
    elif bias_score <= -3:
        bias = "strongly_bearish"
    elif bias_score <= -1:
        bias = "bearish"
    else:
        bias = "neutral"

    return {
        "market_structure": structure,
        "order_blocks": obs,
        "fair_value_gaps": fvgs,
        "liquidity_sweeps": sweeps,
        "composite_bias_score": round(bias_score, 2),
        "composite_bias": bias,
    }
