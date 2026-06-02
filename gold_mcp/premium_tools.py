"""Premium-tier tools for gold-mcp: backtest, walk-forward, intraday seasonality."""
from __future__ import annotations

from itertools import product

import numpy as np
import pandas as pd
import yfinance as yf

from .config import YF_SYMBOL

# ---------- Strategy library (gold-tuned defaults) ----------

def _rsi_mean_reversion(df: pd.DataFrame, *, window: int = 14,
                         oversold: int = 30, overbought: int = 70) -> pd.Series:
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = (-delta.clip(upper=0)).rolling(window).mean()
    rs = gain / loss.where(loss != 0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    sig = pd.Series(0, index=df.index)
    sig[rsi < oversold] = 1
    sig[rsi > overbought] = -1
    return sig.shift(1).fillna(0)


def _macd_trend(df: pd.DataFrame, *, fast: int = 12, slow: int = 26,
                signal_window: int = 9) -> pd.Series:
    ema_f = df["close"].ewm(span=fast, adjust=False).mean()
    ema_s = df["close"].ewm(span=slow, adjust=False).mean()
    macd = ema_f - ema_s
    sig_line = macd.ewm(span=signal_window, adjust=False).mean()
    sig = pd.Series(0, index=df.index)
    sig[macd > sig_line] = 1
    sig[macd < sig_line] = -1
    return sig.shift(1).fillna(0)


def _sma_crossover(df: pd.DataFrame, *, fast: int = 20, slow: int = 50) -> pd.Series:
    f = df["close"].rolling(fast).mean()
    s = df["close"].rolling(slow).mean()
    sig = pd.Series(0, index=df.index)
    sig[f > s] = 1
    sig[f < s] = -1
    return sig.shift(1).fillna(0)


def _breakout_donchian(df: pd.DataFrame, *, window: int = 20) -> pd.Series:
    hi = df["high"].rolling(window).max().shift(1)
    lo = df["low"].rolling(window).min().shift(1)
    sig = pd.Series(0, index=df.index)
    sig[df["close"] > hi] = 1
    sig[df["close"] < lo] = -1
    return sig.fillna(0)


STRATEGIES = {
    "rsi_mean_reversion": _rsi_mean_reversion,
    "macd_trend": _macd_trend,
    "sma_crossover": _sma_crossover,
    "breakout_donchian": _breakout_donchian,
}


# ---------- Bars fetcher (with Premium-grade lookback) ----------

def _fetch_daily_gold(lookback: int) -> pd.DataFrame | None:
    period = f"{max(lookback + 50, 365)}d"
    df = yf.download(YF_SYMBOL, period=period, interval="1d",
                     progress=False, auto_adjust=True)
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.tail(lookback).copy()
    df.columns = [c.lower() for c in df.columns]
    return df.astype({"open": float, "high": float, "low": float,
                       "close": float, "volume": float}, errors="ignore")


# ---------- Backtester ----------

def _backtest_df(df: pd.DataFrame, strategy_name: str, params: dict | None,
                 fee_bps: float) -> dict:
    if strategy_name not in STRATEGIES:
        return {"error": "unknown_strategy", "available": list(STRATEGIES)}
    if len(df) < 60:
        return {"error": "insufficient_bars", "have": len(df), "need": 60}
    signal = STRATEGIES[strategy_name](df, **(params or {}))
    rets = df["close"].pct_change().fillna(0)
    pos_change = signal.diff().abs().fillna(signal.abs())
    fees = pos_change * (fee_bps / 10_000)
    strat_rets = signal * rets - fees
    equity = (1 + strat_rets).cumprod()
    drawdown = equity / equity.cummax() - 1
    n = len(strat_rets)
    ann_factor = 252 if n > 100 else max(1, n)
    mean_ret, std_ret = strat_rets.mean(), strat_rets.std()
    sharpe = (mean_ret / std_ret) * np.sqrt(ann_factor) if std_ret > 0 else 0.0
    wins = strat_rets[strat_rets > 0]
    losses = strat_rets[strat_rets < 0]
    pf = (wins.sum() / abs(losses.sum())
          if len(losses) > 0 and losses.sum() != 0 else None)
    return {
        "strategy": strategy_name,
        "params": params or {},
        "n_bars": n,
        "fee_bps": fee_bps,
        "total_return_pct": round(float(equity.iloc[-1] - 1) * 100, 3),
        "sharpe": round(float(sharpe), 3),
        "max_drawdown_pct": round(float(drawdown.min()) * 100, 3),
        "n_trades": int(pos_change[pos_change > 0].count()),
        "win_rate": round(float((strat_rets > 0).mean()), 3),
        "profit_factor": round(float(pf), 3) if pf else None,
        "final_equity": round(float(equity.iloc[-1]), 4),
    }


def backtest_gold_strategy(strategy_name: str, params: dict | None = None,
                           lookback_days: int = 500, fee_bps: float = 2.0) -> dict:
    """Vectorized backtest on XAUUSD daily bars."""
    df = _fetch_daily_gold(lookback_days)
    if df is None or df.empty:
        return {"error": "no_data"}
    out = _backtest_df(df, strategy_name, params, fee_bps)
    out["symbol"] = "XAUUSD"
    out["source"] = "yfinance"
    return out


def gold_walk_forward(strategy_name: str, params: dict | None = None,
                      train_window: int = 252, test_window: int = 63,
                      lookback_days: int = 1500, fee_bps: float = 2.0) -> dict:
    """Walk-forward backtest on XAUUSD."""
    df = _fetch_daily_gold(lookback_days)
    if df is None or df.empty:
        return {"error": "no_data"}
    if len(df) < train_window + test_window:
        return {"error": "insufficient_bars",
                "have": len(df), "need": train_window + test_window}
    folds = []
    start = 0
    while start + train_window + test_window <= len(df):
        sub = df.iloc[start + train_window: start + train_window + test_window]
        r = _backtest_df(sub, strategy_name, params, fee_bps)
        if "error" not in r:
            folds.append({
                "start_idx": start,
                "test_return_pct": r["total_return_pct"],
                "test_sharpe": r["sharpe"],
                "test_drawdown_pct": r["max_drawdown_pct"],
            })
        start += test_window
    if not folds:
        return {"error": "no_valid_folds"}
    returns = [f["test_return_pct"] for f in folds]
    sharpes = [f["test_sharpe"] for f in folds]
    return {
        "symbol": "XAUUSD",
        "strategy": strategy_name,
        "params": params or {},
        "train_window": train_window,
        "test_window": test_window,
        "n_folds": len(folds),
        "mean_test_return_pct": round(float(np.mean(returns)), 3),
        "std_test_return_pct": round(float(np.std(returns)), 3),
        "mean_test_sharpe": round(float(np.mean(sharpes)), 3),
        "consistency": round(float(sum(r > 0 for r in returns) / len(returns)), 3),
        "folds": folds,
    }


def optimize_gold_strategy(strategy_name: str, param_grid: dict,
                           lookback_days: int = 1000, metric: str = "sharpe",
                           fee_bps: float = 2.0) -> dict:
    """Grid-search optimizer on XAUUSD."""
    if strategy_name not in STRATEGIES:
        return {"error": "unknown_strategy", "available": list(STRATEGIES)}
    if metric not in ("sharpe", "total_return_pct", "profit_factor"):
        return {"error": "unknown_metric"}
    df = _fetch_daily_gold(lookback_days)
    if df is None or df.empty:
        return {"error": "no_data"}
    keys = list(param_grid.keys())
    combos = list(product(*[param_grid[k] for k in keys]))
    if len(combos) > 200:
        return {"error": "grid_too_large", "combinations": len(combos), "max": 200}
    results = []
    for c in combos:
        p = dict(zip(keys, c, strict=False))
        r = _backtest_df(df, strategy_name, p, fee_bps)
        if "error" in r:
            continue
        results.append({
            "params": p,
            "metric": r.get(metric),
            "sharpe": r["sharpe"],
            "total_return_pct": r["total_return_pct"],
            "max_drawdown_pct": r["max_drawdown_pct"],
            "n_trades": r["n_trades"],
        })
    valid = [r for r in results if r["metric"] is not None]
    valid.sort(key=lambda r: r["metric"], reverse=True)
    return {
        "symbol": "XAUUSD",
        "strategy": strategy_name,
        "metric": metric,
        "n_combinations": len(combos),
        "best": valid[0] if valid else None,
        "top_5": valid[:5],
    }


# ---------- Intraday seasonality (more granular than daily seasonality) ----------

def gold_intraday_seasonality(group_by: str = "hour", lookback_days: int = 60) -> dict:
    """Intraday seasonality of gold returns by hour of day or by trading session.

    Args:
        group_by: "hour" or "session" (asia / london / ny overlap).
        lookback_days: history window.
    """
    if group_by not in ("hour", "session"):
        return {"error": "group_by must be 'hour' or 'session'"}
    period = f"{min(max(lookback_days, 7), 60)}d"
    df = yf.download(YF_SYMBOL, period=period, interval="1h",
                     progress=False, auto_adjust=True)
    if df is None or df.empty:
        return {"error": "no_data"}
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Close"]].copy()
    df["ret"] = df["Close"].pct_change()
    df = df.dropna()

    if group_by == "hour":
        df["bucket"] = df.index.hour
    else:
        def _session(h):
            if 0 <= h < 8:
                return "asia"
            if 8 <= h < 13:
                return "london"
            if 13 <= h < 17:
                return "london_ny_overlap"
            if 17 <= h < 22:
                return "ny"
            return "late_ny"
        df["bucket"] = df.index.hour.map(_session)

    stats = df.groupby("bucket")["ret"].agg(["mean", "std", "count"])
    stats["mean_bps"] = stats["mean"] * 10_000
    stats["win_rate"] = df.groupby("bucket")["ret"].apply(lambda s: (s > 0).mean())
    return {
        "symbol": "XAUUSD",
        "group_by": group_by,
        "lookback_days": lookback_days,
        "samples": int(len(df)),
        "buckets": {
            str(idx): {
                "mean_return_bps": round(float(row["mean_bps"]), 2),
                "std_pct": round(float(row["std"]) * 100, 4),
                "win_rate": round(float(row["win_rate"]), 3),
                "n_bars": int(row["count"]),
            }
            for idx, row in stats.iterrows()
        },
    }
