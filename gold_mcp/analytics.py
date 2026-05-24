"""Higher-level analytics: seasonality, recent stats."""
from __future__ import annotations

import pandas as pd
import yfinance as yf

from .config import YF_SYMBOL


def get_seasonality(group_by: str = "dow", lookback_years: int = 5) -> dict:
    if group_by not in ("dow", "month"):
        return {"error": "group_by must be 'dow' or 'month'"}

    period = f"{lookback_years}y"
    df = yf.download(YF_SYMBOL, period=period, interval="1d", progress=False, auto_adjust=True)
    if df is None or df.empty:
        return {"error": "no historical data"}

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[["Close"]].copy()
    df["ret"] = df["Close"].pct_change()
    df = df.dropna()

    if group_by == "dow":
        df["bucket"] = df.index.day_name()
        order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    else:
        df["bucket"] = df.index.month_name()
        order = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]

    stats = df.groupby("bucket")["ret"].agg(["mean", "median", "std", "count"])
    stats = stats.reindex([b for b in order if b in stats.index])
    stats["mean_bps"] = stats["mean"] * 10_000
    stats["win_rate"] = df.groupby("bucket")["ret"].apply(lambda s: (s > 0).mean()).reindex(stats.index)

    return {
        "group_by": group_by,
        "lookback_years": lookback_years,
        "samples": int(len(df)),
        "buckets": {
            str(idx): {
                "mean_return_bps": round(float(row["mean_bps"]), 2),
                "median_return_pct": round(float(row["median"]) * 100, 4),
                "std_pct": round(float(row["std"]) * 100, 4),
                "win_rate": round(float(row["win_rate"]), 3),
                "n_days": int(row["count"]),
            }
            for idx, row in stats.iterrows()
        },
    }
