"""L2 orderbook data access for XAUUSD DOM snapshots."""
from __future__ import annotations

import pandas as pd

from .config import L2_DIR


def _latest_l2_file() -> pd.DataFrame | None:
    if not L2_DIR or not L2_DIR.exists():
        return None
    files = sorted(L2_DIR.glob("XAUUSD_L2_*.parquet"))
    if not files:
        return None
    return pd.read_parquet(files[-1])


def _latest_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    last_id = df["snapshot_id"].max()
    return df[df["snapshot_id"] == last_id].copy()


def get_top_of_book() -> dict:
    df = _latest_l2_file()
    if df is None or df.empty:
        return {"error": "no L2 data available", "l2_dir": str(L2_DIR)}

    snap = _latest_snapshot(df)
    bids = snap[snap["side"] == "bid"].sort_values("level")
    asks = snap[snap["side"] == "ask"].sort_values("level")

    if bids.empty or asks.empty:
        return {"error": "incomplete snapshot"}

    best_bid = float(bids.iloc[0]["price"])
    best_ask = float(asks.iloc[0]["price"])
    ts_us = int(snap["ts_us"].iloc[0])

    return {
        "ts_us": ts_us,
        "timestamp": pd.Timestamp(ts_us, unit="us", tz="UTC").isoformat(),
        "best_bid": best_bid,
        "best_ask": best_ask,
        "mid": (best_bid + best_ask) / 2,
        "spread": best_ask - best_bid,
        "spread_bps": (best_ask - best_bid) / best_bid * 10_000,
        "bid_size_top": float(bids.iloc[0]["volume"]),
        "ask_size_top": float(asks.iloc[0]["volume"]),
    }


def get_l2_imbalance(depth: int = 3) -> dict:
    df = _latest_l2_file()
    if df is None or df.empty:
        return {"error": "no L2 data available"}

    snap = _latest_snapshot(df)
    bids = snap[(snap["side"] == "bid") & (snap["level"] < depth)]
    asks = snap[(snap["side"] == "ask") & (snap["level"] < depth)]

    bid_vol = float(bids["volume"].sum())
    ask_vol = float(asks["volume"].sum())
    total = bid_vol + ask_vol

    if total == 0:
        return {"error": "zero volume in book"}

    imbalance = (bid_vol - ask_vol) / total
    pressure = "neutral"
    if imbalance > 0.2:
        pressure = "strong buy"
    elif imbalance > 0.05:
        pressure = "buy"
    elif imbalance < -0.2:
        pressure = "strong sell"
    elif imbalance < -0.05:
        pressure = "sell"

    ts_us = int(snap["ts_us"].iloc[0])

    return {
        "ts_us": ts_us,
        "timestamp": pd.Timestamp(ts_us, unit="us", tz="UTC").isoformat(),
        "depth_levels": depth,
        "bid_volume": bid_vol,
        "ask_volume": ask_vol,
        "imbalance": round(imbalance, 4),
        "pressure": pressure,
        "interpretation": (
            f"Top {depth} levels: bid {bid_vol:,.0f} vs ask {ask_vol:,.0f}. "
            f"Imbalance {imbalance:+.1%} → {pressure} pressure."
        ),
    }


def get_l2_depth(depth: int = 3) -> dict:
    df = _latest_l2_file()
    if df is None or df.empty:
        return {"error": "no L2 data available"}

    snap = _latest_snapshot(df)
    bids = snap[(snap["side"] == "bid") & (snap["level"] < depth)].sort_values("level")
    asks = snap[(snap["side"] == "ask") & (snap["level"] < depth)].sort_values("level")

    ts_us = int(snap["ts_us"].iloc[0])

    return {
        "ts_us": ts_us,
        "timestamp": pd.Timestamp(ts_us, unit="us", tz="UTC").isoformat(),
        "bids": [
            {"level": int(r.level), "price": float(r.price), "volume": float(r.volume)}
            for r in bids.itertuples()
        ],
        "asks": [
            {"level": int(r.level), "price": float(r.price), "volume": float(r.volume)}
            for r in asks.itertuples()
        ],
    }
