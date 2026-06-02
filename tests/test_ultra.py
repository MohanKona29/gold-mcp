"""Ultra-tier logic tests — pure math, no network calls."""
import numpy as np

from gold_mcp import regime, risk_mgmt, smart_money


def _bars(n=200, seed=11, drift=0.0005, vol=0.012):
    rng = np.random.default_rng(seed)
    rets = rng.normal(drift, vol, n)
    closes = 2000.0 * np.cumprod(1 + rets)
    bars = []
    for i, c in enumerate(closes):
        hi = c * (1 + abs(rng.normal(0, 0.003)))
        lo = c * (1 - abs(rng.normal(0, 0.003)))
        bars.append({"time": f"t{i}", "open": float(c), "high": float(hi),
                     "low": float(lo), "close": float(c), "volume": 1000.0})
    return bars


# ---------- SMC ----------

def test_smc_market_structure():
    out = smart_money.detect_market_structure(_bars(120))
    assert "current_trend" in out
    assert out["current_trend"] in ("up", "down", "undefined")


def test_smc_order_blocks_run():
    out = smart_money.detect_order_blocks(_bars(120))
    assert "n_blocks_total" in out
    assert isinstance(out["active_blocks"], list)


def test_smc_fvg_run():
    out = smart_money.detect_fair_value_gaps(_bars(120))
    assert "n_fvgs_total" in out
    assert isinstance(out["unfilled_fvgs"], list)


def test_smc_sweeps_run():
    out = smart_money.detect_liquidity_sweeps(_bars(120))
    assert "n_sweeps" in out


def test_smc_full_scan():
    out = smart_money.smc_full_scan(_bars(120))
    assert "composite_bias" in out
    assert out["composite_bias"] in (
        "strongly_bullish", "bullish", "neutral", "bearish", "strongly_bearish"
    )


def test_smc_insufficient_data():
    out = smart_money.detect_market_structure([{"open": 1, "high": 1, "low": 1, "close": 1}] * 5)
    assert "error" in out


# ---------- Regime ----------

def test_hurst_trending_series():
    # Synthetic strongly-trending series
    arr = [100.0]
    rng = np.random.default_rng(0)
    for _ in range(400):
        arr.append(arr[-1] * (1.001 + rng.normal(0, 0.001)))
    out = regime.hurst_exponent(arr, max_lag=30)
    assert "hurst" in out
    # Hurst should lean above 0.5 for a trending series
    assert out["hurst"] > 0.4


def test_variance_ratio_runs():
    rng = np.random.default_rng(0)
    arr = [100.0]
    for _ in range(400):
        arr.append(arr[-1] * (1 + rng.normal(0, 0.01)))
    out = regime.variance_ratio(arr, q=4)
    assert "variance_ratio" in out
    assert "z_stat" in out


def test_classify_regime_composite():
    rng = np.random.default_rng(0)
    arr = [100.0]
    for _ in range(400):
        arr.append(arr[-1] * (1 + rng.normal(0, 0.01)))
    out = regime.classify_regime(arr)
    assert "composite_regime" in out
    assert "trading_implication" in out


# ---------- Risk management ----------

def test_kelly_positive_expectancy():
    out = risk_mgmt.kelly_fraction(win_rate=0.55, payoff_ratio=1.5)
    assert "full_kelly_pct" in out
    assert out["full_kelly_pct"] > 0


def test_kelly_negative_expectancy():
    out = risk_mgmt.kelly_fraction(win_rate=0.40, payoff_ratio=1.0)
    assert out["full_kelly_pct"] <= 0
    assert "warning" in out


def test_fixed_fractional():
    out = risk_mgmt.fixed_fractional(account_size=100000, risk_pct=1.0,
                                       stop_distance=20.0)
    assert "position_units" in out
    assert out["risk_amount"] == 1000.0


def test_optimal_f():
    rng = np.random.default_rng(0)
    rets = rng.normal(0.002, 0.02, 100).tolist()
    out = risk_mgmt.optimal_f(rets)
    assert "optimal_f" in out
    assert 0 < out["optimal_f"] < 1


def test_risk_of_ruin_negative_edge():
    out = risk_mgmt.risk_of_ruin(win_rate=0.4, payoff_ratio=1.0,
                                  risk_pct=2.0, n_trades=200, n_simulations=500)
    assert "prob_of_ruin" in out
    assert out["prob_of_ruin"] > 0  # Negative-edge → some ruin probability


def test_risk_of_ruin_strong_edge():
    out = risk_mgmt.risk_of_ruin(win_rate=0.7, payoff_ratio=2.0,
                                  risk_pct=1.0, n_trades=200, n_simulations=500)
    assert out["prob_of_ruin"] < 0.2  # Strong edge → low ruin probability


def test_monte_carlo_bootstrap():
    rng = np.random.default_rng(0)
    rets = rng.normal(0.001, 0.012, 200).tolist()
    out = risk_mgmt.simulate_paths(rets, n_paths=500, n_steps=60)
    assert "expected_final" in out
    assert out["n_paths"] == 500


def test_monte_carlo_parametric():
    rng = np.random.default_rng(0)
    rets = rng.normal(0.001, 0.012, 200).tolist()
    out = risk_mgmt.simulate_paths(rets, n_paths=300, n_steps=60, method="parametric")
    assert "expected_final" in out


def test_value_at_risk():
    rng = np.random.default_rng(0)
    rets = rng.normal(0, 0.015, 252).tolist()
    out = risk_mgmt.value_at_risk(rets, confidence=0.95)
    assert "VaR_pct" in out
    assert "CVaR_pct" in out
    assert out["CVaR_pct"] <= out["VaR_pct"]  # CVaR is worse than VaR


def test_prob_hit_target_or_stop():
    rng = np.random.default_rng(0)
    rets = rng.normal(0.0001, 0.01, 200).tolist()
    out = risk_mgmt.prob_hit_target_or_stop(
        rets, entry_price=2000, target_price=2050, stop_price=1980,
        n_paths=500, max_steps=50,
    )
    assert "prob_target_first" in out
    assert "prob_stop_first" in out
    assert "expected_value_R" in out
    # Probabilities sum should approximately equal 1 - prob_no_hit
    total = out["prob_target_first"] + out["prob_stop_first"] + out["prob_neither_in_horizon"]
    assert 0.99 <= total <= 1.01
