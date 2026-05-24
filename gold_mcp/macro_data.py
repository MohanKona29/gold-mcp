"""Macro context for gold: DXY, yields, equities, BTC, silver, oil."""
from __future__ import annotations

import pandas as pd
import yfinance as yf

from .config import MACRO_SYMBOLS, YF_SYMBOL


def get_macro_context() -> dict:
    symbols = {"GOLD": YF_SYMBOL, **MACRO_SYMBOLS}
    tickers = list(symbols.values())
    data = yf.download(tickers, period="5d", interval="1d", progress=False, auto_adjust=True)
    if data is None or data.empty:
        return {"error": "yfinance returned no data"}

    closes = data["Close"] if isinstance(data.columns, pd.MultiIndex) else data
    if closes.empty:
        return {"error": "no close data"}

    out = {}
    for label, ticker in symbols.items():
        if ticker not in closes.columns:
            continue
        series = closes[ticker].dropna()
        if len(series) < 2:
            continue
        last = float(series.iloc[-1])
        prev = float(series.iloc[-2])
        change = last - prev
        change_pct = change / prev * 100
        out[label] = {
            "ticker": ticker,
            "last": round(last, 3),
            "change": round(change, 3),
            "change_pct": round(change_pct, 3),
        }

    return {
        "asof": pd.Timestamp(closes.index[-1]).isoformat(),
        "data": out,
        "interpretation_hint": (
            "Strong DXY / rising US10Y typically pressures gold. "
            "Falling real yields and risk-off (rising VIX) usually support gold."
        ),
    }


def get_correlation_matrix(lookback_days: int = 60) -> dict:
    symbols = {"GOLD": YF_SYMBOL, **MACRO_SYMBOLS}
    tickers = list(symbols.values())
    period = f"{max(lookback_days + 5, 30)}d"
    data = yf.download(tickers, period=period, interval="1d", progress=False, auto_adjust=True)
    if data is None or data.empty:
        return {"error": "yfinance returned no data"}

    closes = data["Close"] if isinstance(data.columns, pd.MultiIndex) else data
    rename = {v: k for k, v in symbols.items() if v in closes.columns}
    closes = closes.rename(columns=rename)
    returns = closes.pct_change().dropna().tail(lookback_days)
    if len(returns) < 5:
        return {"error": "insufficient data for correlation"}

    corr = returns.corr().round(3)
    if "GOLD" not in corr.columns:
        return {"error": "GOLD column missing"}
    gold_corr = corr["GOLD"].drop("GOLD").sort_values(ascending=False)

    return {
        "lookback_days": int(len(returns)),
        "asof": returns.index[-1].isoformat(),
        "gold_correlations": {k: float(v) for k, v in gold_corr.items()},
        "full_matrix": corr.to_dict(),
    }
