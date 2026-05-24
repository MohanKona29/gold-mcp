"""gold-mcp FastMCP server.

A small, free, community-driven MCP server that brings public gold
(XAUUSD) market data into Claude, ChatGPT, Cursor, Windsurf, Cline,
Zed, and any other Model Context Protocol client.

All data comes from Yahoo Finance. No broker account, no tick stream,
no environment variables, no local data files required.

Educational and research use only — not financial advice.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import analyst, analytics, gold_data, macro_data
from .adapters import vn_macro as vn_macro_adapter

mcp = FastMCP("gold-mcp")


# ---------- Price + OHLCV ----------

@mcp.tool()
def get_gold_price() -> dict:
    """Latest gold (XAUUSD / GC=F) price and 24h change from Yahoo Finance.

    Returns the most recent intraday close, the 24-hour absolute and
    percentage change, and the recent 30-minute intraday high/low.
    """
    return gold_data.get_gold_price()


@mcp.tool()
def get_gold_ohlcv(timeframe: str = "1h", lookback: int = 24) -> dict:
    """Historical OHLCV bars for gold from Yahoo Finance.

    Args:
        timeframe: One of "1m", "5m", "15m", "30m", "1h", "4h", "1d",
            "1wk", "1mo".
        lookback: Number of most recent bars to return.
    """
    return gold_data.get_gold_ohlcv(timeframe=timeframe, lookback=lookback)


# ---------- Macro context ----------

@mcp.tool()
def get_macro_context() -> dict:
    """Macro snapshot relevant to gold: DXY, US10Y/02Y, SPX, VIX, BTC,
    silver, oil. Each entry reports last close, day change, and day % change.
    """
    return macro_data.get_macro_context()


@mcp.tool()
def get_gold_correlations(lookback_days: int = 60) -> dict:
    """Correlation of gold daily returns vs the macro basket.

    Args:
        lookback_days: Number of trading days for the correlation window.
    """
    return macro_data.get_correlation_matrix(lookback_days=lookback_days)


@mcp.tool()
def get_gold_seasonality(group_by: str = "dow", lookback_years: int = 5) -> dict:
    """Historical seasonality stats for gold returns.

    Args:
        group_by: "dow" (day of week) or "month".
        lookback_years: Years of history to include.
    """
    return analytics.get_seasonality(group_by=group_by, lookback_years=lookback_years)


# ---------- Vietnam context (community contribution) ----------

@mcp.tool()
def get_vn_macro() -> dict:
    """USD/VND + cross rates + implied world-parity gold price in VND.

    Returns USD/VND, EUR/VND, CNY/VND with 5-day change, plus an implied
    world-parity gold price (VND per troy ounce and per tael / lượng)
    derived from world gold and USD/VND.

    Useful for Vietnamese users comparing local gold quotes (SJC, DOJI,
    PNJ) against the international reference.
    """
    return vn_macro_adapter.get_vn_macro()


@mcp.tool()
def estimate_vn_gold_premium(local_price_vnd_per_tael: float) -> dict:
    """Compare a user-supplied local VN gold price to world parity.

    Args:
        local_price_vnd_per_tael: User-observed local gold price
            (e.g. SJC ask in VND per tael / lượng).
    """
    return vn_macro_adapter.estimate_vn_gold_premium(local_price_vnd_per_tael)


# ---------- Aggregator ----------

@mcp.tool()
def gold_market_snapshot(timeframe: str = "1h") -> dict:
    """One-call structured snapshot of gold's current market state.

    Aggregates price, recent bars, macro context, correlations,
    seasonality, and VN parity into a single response with a concise
    bulleted summary. Educational only — no recommendations.

    Args:
        timeframe: Bar timeframe used for recent_bars (default "1h").
    """
    return analyst.gold_market_snapshot(timeframe=timeframe)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
