"""Vietnam-specific macro context for XAUUSD analysis.

Lightweight implementation using public FX feeds. Provides USD/VND and
related rates, plus an implied world-parity gold price in VND that
local trader can compare against observed local gold prices (e.g. SJC,
DOJI, PNJ) to estimate the local premium.

Note: live SJC/DOJI/PNJ scraping is deferred — those endpoints sit
behind Cloudflare / anti-bot protection and require dedicated
infrastructure. Until then, this tool gives the "world parity" anchor
and the user (or the LLM) can compare against locally observed prices.
"""
from __future__ import annotations

import pandas as pd
import yfinance as yf

VN_FX_SYMBOLS = {
    "USDVND": "USDVND=X",
    "EURVND": "EURVND=X",
    "CNYVND": "CNYVND=X",
}
GOLD_USD_SYMBOL = "GC=F"  # gold futures, USD per troy ounce


def get_vn_macro() -> dict:
    """USD/VND + cross rates + implied world-parity gold price in VND."""
    symbols = list(VN_FX_SYMBOLS.values()) + [GOLD_USD_SYMBOL]
    data = yf.download(symbols, period="10d", interval="1d", progress=False, auto_adjust=True)
    if data is None or data.empty:
        return {"error": "yfinance returned no data"}

    closes = data["Close"] if isinstance(data.columns, pd.MultiIndex) else data
    if closes.empty:
        return {"error": "no close data"}

    fx_out = {}
    for label, ticker in VN_FX_SYMBOLS.items():
        if ticker not in closes.columns:
            continue
        s = closes[ticker].dropna()
        if len(s) < 2:
            continue
        last = float(s.iloc[-1])
        prev_week = float(s.iloc[0])
        fx_out[label] = {
            "ticker": ticker,
            "last": round(last, 2),
            "change_5d": round(last - prev_week, 2),
            "change_5d_pct": round((last - prev_week) / prev_week * 100, 3),
        }

    # Implied world-parity gold (USD/oz -> VND/tael)
    # 1 tael (lượng) = 1.20556 troy oz
    OZ_PER_TAEL = 1.20556
    parity_vnd_per_tael = None
    parity_vnd_per_oz = None
    if GOLD_USD_SYMBOL in closes.columns and "USDVND=X" in closes.columns:
        gold_usd = closes[GOLD_USD_SYMBOL].dropna()
        usdvnd = closes["USDVND=X"].dropna()
        if not gold_usd.empty and not usdvnd.empty:
            g_last = float(gold_usd.iloc[-1])
            v_last = float(usdvnd.iloc[-1])
            parity_vnd_per_oz = g_last * v_last
            parity_vnd_per_tael = parity_vnd_per_oz * OZ_PER_TAEL

    return {
        "asof": pd.Timestamp(closes.index[-1]).isoformat(),
        "fx_rates": fx_out,
        "world_parity_gold": {
            "vnd_per_oz": round(parity_vnd_per_oz, 0) if parity_vnd_per_oz else None,
            "vnd_per_tael": round(parity_vnd_per_tael, 0) if parity_vnd_per_tael else None,
            "vnd_per_tael_millions": (
                round(parity_vnd_per_tael / 1_000_000, 3)
                if parity_vnd_per_tael else None
            ),
            "tael_to_oz": OZ_PER_TAEL,
            "note": (
                "World-parity price = world gold (USD/oz) x USD/VND. "
                "Compare with locally observed prices (SJC, DOJI, PNJ) "
                "to estimate local premium. SJC tael typically trades "
                "10-20% above parity."
            ),
        },
        "interpretation_hint": (
            "VN gold premium = (local_price - world_parity) / world_parity. "
            "Premium widening signals strong local demand (or import constraint); "
            "narrowing signals normalization. USD/VND weakness lifts the parity "
            "anchor and pressures local sellers."
        ),
    }


def estimate_vn_gold_premium(local_price_vnd_per_tael: float) -> dict:
    """Compute VN gold premium given a user-supplied local price."""
    parity = get_vn_macro()
    if "error" in parity:
        return parity
    p = parity.get("world_parity_gold", {}).get("vnd_per_tael")
    if not p:
        return {"error": "world_parity_unavailable"}
    premium_abs = local_price_vnd_per_tael - p
    premium_pct = premium_abs / p * 100
    return {
        "local_price_vnd_per_tael": local_price_vnd_per_tael,
        "world_parity_vnd_per_tael": round(p, 0),
        "premium_vnd": round(premium_abs, 0),
        "premium_pct": round(premium_pct, 2),
        "interpretation": (
            f"Local gold trades at {premium_pct:+.1f}% vs world parity. "
            + (
                "Within typical VN premium range (10-20%)."
                if 5 <= premium_pct <= 25
                else (
                    "Below parity — unusual; check input or arbitrage opportunity."
                    if premium_pct < 0
                    else "Outside typical range — investigate local demand/supply."
                )
            )
        ),
    }
