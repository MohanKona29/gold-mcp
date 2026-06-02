"""Market regime classification: trending vs mean-reverting.

Uses Hurst exponent (R/S analysis) and Lo-MacKinlay variance ratio
test. Both are public-domain econometric methods for distinguishing
random walks, mean-reverting series, and trending series.

Hurst interpretation:
  H ≈ 0.5  → random walk (no edge)
  H < 0.5  → mean-reverting (fade extremes)
  H > 0.5  → trending (ride moves)

Variance ratio interpretation (Lo-MacKinlay 1988):
  VR ≈ 1.0  → random walk
  VR < 1.0  → mean-reverting
  VR > 1.0  → trending
"""
from __future__ import annotations

import numpy as np


def hurst_exponent(prices: list[float] | np.ndarray, max_lag: int = 50) -> dict:
    """Hurst exponent via R/S analysis on log-returns."""
    arr = np.asarray(prices, dtype=float)
    if len(arr) < max_lag * 2:
        return {"error": "insufficient_data", "have": len(arr), "need": max_lag * 2}
    log_rets = np.diff(np.log(arr))
    lags = range(2, min(max_lag, len(log_rets) // 2))
    rs_values = []
    valid_lags = []
    for lag in lags:
        chunks = len(log_rets) // lag
        if chunks < 2:
            continue
        rs = []
        for i in range(chunks):
            chunk = log_rets[i * lag: (i + 1) * lag]
            mean = chunk.mean()
            dev = chunk - mean
            cum_dev = dev.cumsum()
            r = cum_dev.max() - cum_dev.min()
            s = chunk.std()
            if s > 0:
                rs.append(r / s)
        if rs:
            rs_values.append(np.mean(rs))
            valid_lags.append(lag)
    if len(rs_values) < 5:
        return {"error": "insufficient_lags"}
    log_lags = np.log(valid_lags)
    log_rs = np.log(rs_values)
    slope, intercept = np.polyfit(log_lags, log_rs, 1)
    h = float(slope)
    if h > 0.55:
        regime = "trending"
    elif h < 0.45:
        regime = "mean_reverting"
    else:
        regime = "random_walk"
    return {
        "hurst": round(h, 4),
        "regime": regime,
        "n_lags_used": len(valid_lags),
        "interpretation": (
            f"H={h:.3f}: " + {
                "trending": "persistent / trending — ride moves",
                "mean_reverting": "anti-persistent / mean-reverting — fade extremes",
                "random_walk": "near random walk — no statistical edge from this metric",
            }[regime]
        ),
    }


def variance_ratio(prices: list[float] | np.ndarray, q: int = 4) -> dict:
    """Lo-MacKinlay (1988) variance ratio test.

    VR(q) = Var(q-period returns) / (q * Var(1-period returns))
    Under random walk, VR(q) → 1 for all q. Includes heteroscedasticity-
    robust z-statistic.
    """
    arr = np.asarray(prices, dtype=float)
    if len(arr) < q * 10:
        return {"error": "insufficient_data", "have": len(arr), "need": q * 10}
    log_rets = np.diff(np.log(arr))
    n = len(log_rets)
    mu = log_rets.mean()

    # 1-period variance (unbiased)
    var_1 = ((log_rets - mu) ** 2).sum() / (n - 1)

    # q-period overlapping returns
    q_rets = np.array([log_rets[i: i + q].sum() for i in range(n - q + 1)])
    m = q * (n - q + 1) * (1 - q / n)
    if m <= 0 or var_1 == 0:
        return {"error": "degenerate"}
    var_q = ((q_rets - q * mu) ** 2).sum() / m
    vr = var_q / (q * var_1)

    # Heteroscedasticity-robust standard error
    delta_sum = 0.0
    for j in range(1, q):
        gamma_j = ((log_rets[j:] - mu) ** 2 * (log_rets[:-j] - mu) ** 2).sum() / ((n - 1) ** 2 * var_1 ** 2)
        weight = (2 * (q - j) / q) ** 2
        delta_sum += weight * gamma_j
    se = float(np.sqrt(delta_sum)) if delta_sum > 0 else 1e-9
    z = (vr - 1.0) / se

    if vr < 0.85:
        regime = "mean_reverting"
    elif vr > 1.15:
        regime = "trending"
    else:
        regime = "random_walk"
    return {
        "q": q,
        "variance_ratio": round(float(vr), 4),
        "z_stat": round(float(z), 3),
        "is_significant_5pct": bool(abs(z) > 1.96),
        "regime": regime,
        "n_observations": n,
        "interpretation": (
            f"VR({q})={vr:.3f}, z={z:.2f}. " +
            ("Reject random-walk at 5%. " if abs(z) > 1.96 else "Fail to reject random-walk at 5%. ") +
            f"Series looks {regime.replace('_', ' ')}."
        ),
    }


def classify_regime(prices: list[float] | np.ndarray, q: int = 4,
                    hurst_lag: int = 50) -> dict:
    """Composite regime tag combining Hurst + VR."""
    h = hurst_exponent(prices, max_lag=hurst_lag)
    v = variance_ratio(prices, q=q)
    if "error" in h or "error" in v:
        return {"error": "computation_failed", "hurst": h, "variance_ratio": v}

    # Composite scoring
    score = 0
    if h["regime"] == "trending":
        score += 1
    elif h["regime"] == "mean_reverting":
        score -= 1
    if v["regime"] == "trending":
        score += 1
    elif v["regime"] == "mean_reverting":
        score -= 1

    if score >= 2:
        composite = "strongly_trending"
    elif score == 1:
        composite = "trending"
    elif score == 0:
        composite = "mixed_or_random"
    elif score == -1:
        composite = "mean_reverting"
    else:
        composite = "strongly_mean_reverting"

    return {
        "hurst": h,
        "variance_ratio": v,
        "composite_regime": composite,
        "score": score,
        "trading_implication": {
            "strongly_trending": "Trend-following strategies favored (MA crossover, breakout). Mean-reversion likely losing.",
            "trending": "Moderate trend — combine with confirmation filters.",
            "mixed_or_random": "No clear regime — reduce position size or stay flat.",
            "mean_reverting": "Mean-reversion strategies favored (RSI fade, BB extremes).",
            "strongly_mean_reverting": "Strong fade signal — trend-following likely losing.",
        }[composite],
    }
