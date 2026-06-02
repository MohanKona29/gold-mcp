"""Position sizing + Monte Carlo risk toolkit — Ultra tier.

Kelly criterion, fixed fractional, Ralph Vince optimal-f, risk-of-ruin,
Monte Carlo path simulation, VaR/CVaR, probability of touching target.
"""
from __future__ import annotations

import numpy as np

# ---------- Position sizing ----------

def kelly_fraction(win_rate: float, payoff_ratio: float,
                   kelly_multiplier: float = 0.5) -> dict:
    """Kelly fraction with safety multiplier.

    Args:
        win_rate: probability of winning trade, 0-1
        payoff_ratio: avg_win / avg_loss
        kelly_multiplier: 0.5 = half-Kelly (recommended), 1.0 = full Kelly
    """
    if not 0 < win_rate < 1:
        return {"error": "win_rate must be in (0, 1)"}
    if payoff_ratio <= 0:
        return {"error": "payoff_ratio must be > 0"}
    full_kelly = (payoff_ratio * win_rate - (1 - win_rate)) / payoff_ratio
    applied = max(0.0, full_kelly * kelly_multiplier)
    return {
        "win_rate": win_rate,
        "payoff_ratio": payoff_ratio,
        "full_kelly_pct": round(full_kelly * 100, 3),
        "applied_kelly_pct": round(applied * 100, 3),
        "kelly_multiplier": kelly_multiplier,
        "warning": (
            "Full Kelly is negative — strategy has negative expectancy. Do not trade."
            if full_kelly <= 0
            else "Half-Kelly is a common safety cushion; full Kelly maximizes geometric growth but is very volatile."
        ),
    }


def fixed_fractional(account_size: float, risk_pct: float,
                     stop_distance: float, contract_value: float = 1.0) -> dict:
    """Classic fixed-fractional sizing.

    Args:
        account_size: total account currency
        risk_pct: percent of account to risk per trade (e.g. 1.0 = 1%)
        stop_distance: price distance from entry to stop
        contract_value: monetary value of one unit movement (default 1.0)
    """
    if risk_pct <= 0 or stop_distance <= 0:
        return {"error": "risk_pct and stop_distance must be > 0"}
    risk_amount = account_size * (risk_pct / 100)
    units = risk_amount / (stop_distance * contract_value)
    return {
        "account_size": account_size,
        "risk_pct": risk_pct,
        "risk_amount": round(risk_amount, 2),
        "stop_distance": stop_distance,
        "position_units": round(units, 4),
        "notes": "Units are abstract — multiply by your symbol's lot size / contract multiplier.",
    }


def optimal_f(returns: list[float]) -> dict:
    """Ralph Vince Optimal-f — geometric-mean-maximizing fraction
    of capital to risk per trade given a series of trade returns.

    Args:
        returns: list of per-trade returns as decimal fractions
                 (e.g. [0.02, -0.01, 0.03, -0.015])
    """
    arr = np.asarray(returns, dtype=float)
    if len(arr) < 5:
        return {"error": "need_at_least_5_trades"}
    worst = arr.min()
    if worst >= 0:
        return {"error": "no_losing_trades_in_series"}

    def hpr(f: float) -> float:
        # Geometric Holding Period Return
        return float(np.prod(1 + f * (-arr / worst)))

    # Grid search f in (0, 1)
    fs = np.linspace(0.01, 0.99, 99)
    hprs = np.array([hpr(f) for f in fs])
    best_idx = int(np.argmax(hprs))
    best_f = float(fs[best_idx])
    return {
        "n_trades": int(len(arr)),
        "worst_trade": round(float(worst), 5),
        "optimal_f": round(best_f, 4),
        "twr_at_optimal_f": round(float(hprs[best_idx]), 4),
        "risk_per_trade_pct": round(best_f * abs(worst) * 100, 3),
        "warning": "Optimal-f is geometrically optimal but assumes returns are stationary; in practice use a fraction (e.g. 0.5 × optimal_f).",
    }


# ---------- Risk of Ruin (Monte Carlo) ----------

def risk_of_ruin(win_rate: float, payoff_ratio: float,
                 risk_pct: float, ruin_threshold_pct: float = 50.0,
                 n_trades: int = 500, n_simulations: int = 5000,
                 seed: int = 42) -> dict:
    """Monte Carlo estimate of probability of drawing down to ruin_threshold."""
    if not 0 < win_rate < 1:
        return {"error": "win_rate must be in (0, 1)"}
    rng = np.random.default_rng(seed)
    win_pct = risk_pct * payoff_ratio / 100
    loss_pct = risk_pct / 100
    ruin_count = 0
    final_equities = []
    for _ in range(n_simulations):
        equity = 1.0
        wins = rng.random(n_trades) < win_rate
        ruined = False
        for w in wins:
            equity *= (1 + win_pct) if w else (1 - loss_pct)
            if equity <= 1.0 - ruin_threshold_pct / 100:
                ruined = True
                break
        if ruined:
            ruin_count += 1
        final_equities.append(equity)

    final_arr = np.array(final_equities)
    return {
        "win_rate": win_rate,
        "payoff_ratio": payoff_ratio,
        "risk_pct_per_trade": risk_pct,
        "ruin_threshold_pct": ruin_threshold_pct,
        "n_trades": n_trades,
        "n_simulations": n_simulations,
        "prob_of_ruin": round(ruin_count / n_simulations, 4),
        "expected_final_equity": round(float(final_arr.mean()), 4),
        "median_final_equity": round(float(np.median(final_arr)), 4),
        "best_path_final": round(float(final_arr.max()), 4),
        "worst_path_final": round(float(final_arr.min()), 4),
    }


# ---------- Monte Carlo path simulation ----------

def simulate_paths(returns_history: list[float], n_paths: int = 1000,
                   n_steps: int = 252, method: str = "bootstrap",
                   seed: int = 42) -> dict:
    """Bootstrap or parametric MC path simulation.

    Args:
        returns_history: historical returns (decimal, e.g. 0.005)
        n_paths: number of paths to simulate
        n_steps: horizon length
        method: "bootstrap" (resample) or "parametric" (gaussian with mu/sigma)
    """
    arr = np.asarray(returns_history, dtype=float)
    if len(arr) < 30:
        return {"error": "need_30_plus_returns"}
    rng = np.random.default_rng(seed)
    if method == "bootstrap":
        sampled = rng.choice(arr, size=(n_paths, n_steps), replace=True)
    elif method == "parametric":
        mu, sigma = arr.mean(), arr.std()
        sampled = rng.normal(mu, sigma, size=(n_paths, n_steps))
    else:
        return {"error": "method must be 'bootstrap' or 'parametric'"}
    cumulative = np.cumprod(1 + sampled, axis=1)
    final = cumulative[:, -1]
    return {
        "method": method,
        "n_paths": n_paths,
        "n_steps": n_steps,
        "expected_final": round(float(final.mean()), 4),
        "median_final": round(float(np.median(final)), 4),
        "p5_final": round(float(np.percentile(final, 5)), 4),
        "p95_final": round(float(np.percentile(final, 95)), 4),
        "best_final": round(float(final.max()), 4),
        "worst_final": round(float(final.min()), 4),
        "prob_positive_final": round(float((final > 1.0).mean()), 4),
    }


def value_at_risk(returns: list[float], confidence: float = 0.95) -> dict:
    """Historical VaR and Conditional VaR (Expected Shortfall)."""
    arr = np.asarray(returns, dtype=float)
    if len(arr) < 30:
        return {"error": "need_30_plus_returns"}
    if not 0.5 < confidence < 1.0:
        return {"error": "confidence must be in (0.5, 1.0)"}
    var = float(np.percentile(arr, (1 - confidence) * 100))
    cvar = float(arr[arr <= var].mean()) if (arr <= var).any() else var
    return {
        "n_observations": len(arr),
        "confidence_level": confidence,
        "VaR_pct": round(var * 100, 4),
        "CVaR_pct": round(cvar * 100, 4),
        "interpretation": (
            f"With {confidence*100:.0f}% confidence, the worst expected single-period "
            f"loss is {var*100:.2f}%. In the worst {(1-confidence)*100:.0f}% of cases, "
            f"the average loss is {cvar*100:.2f}%."
        ),
    }


def prob_hit_target_or_stop(returns_history: list[float], entry_price: float,
                            target_price: float, stop_price: float,
                            n_paths: int = 5000, max_steps: int = 100,
                            seed: int = 42) -> dict:
    """Monte Carlo: what's the probability of hitting target before stop?"""
    arr = np.asarray(returns_history, dtype=float)
    if len(arr) < 30:
        return {"error": "need_30_plus_returns"}
    rng = np.random.default_rng(seed)
    target_hits = 0
    stop_hits = 0
    no_hit = 0
    steps_to_outcome = []
    for _ in range(n_paths):
        price = entry_price
        for step in range(1, max_steps + 1):
            r = rng.choice(arr)
            price *= (1 + r)
            if (entry_price < target_price and price >= target_price) or \
               (entry_price > target_price and price <= target_price):
                target_hits += 1
                steps_to_outcome.append(step)
                break
            if (entry_price > stop_price and price <= stop_price) or \
               (entry_price < stop_price and price >= stop_price):
                stop_hits += 1
                steps_to_outcome.append(step)
                break
        else:
            no_hit += 1

    total = n_paths
    return {
        "entry": entry_price, "target": target_price, "stop": stop_price,
        "n_paths": total, "max_steps": max_steps,
        "prob_target_first": round(target_hits / total, 4),
        "prob_stop_first": round(stop_hits / total, 4),
        "prob_neither_in_horizon": round(no_hit / total, 4),
        "expected_steps_to_outcome": (
            round(float(np.mean(steps_to_outcome)), 1) if steps_to_outcome else None
        ),
        "expected_value_R": (
            round(target_hits / total * abs(target_price - entry_price) /
                  abs(entry_price - stop_price)
                  - stop_hits / total, 3)
            if abs(entry_price - stop_price) > 0 else None
        ),
    }
