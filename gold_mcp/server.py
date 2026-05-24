"""gold-mcp FastMCP server.

Exposes XAUUSD (gold) market data with rich tick-level microstructure
features over the Model Context Protocol. Compatible with Claude
Desktop, ChatGPT Desktop / Agent mode, Cursor, Windsurf, and other
MCP clients.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import analyst, analytics, l2_data, macro_data, microstructure, tick_data
from .adapters import macro_strength as macro_strength_adapter
from .adapters import news_calendar as news_calendar_adapter
from .adapters import strategy as strategy_adapter
from .adapters import vn_macro as vn_macro_adapter

mcp = FastMCP("gold-mcp")


# ---------- Price / OHLCV ----------

@mcp.tool()
def get_gold_price() -> dict:
    """Latest XAUUSD bid/ask/mid price and spread from the live tick feed.

    Returns the most recent quote captured by the MT5 stream including
    timestamp, bid, ask, mid, spread, and spread in basis points.
    """
    return tick_data.get_latest_price()


@mcp.tool()
def get_gold_ohlcv(timeframe: str = "1h", lookback: int = 24) -> dict:
    """OHLCV bars for XAUUSD built from raw tick data.

    Args:
        timeframe: One of "1m", "5m", "15m", "30m", "1h", "4h", "1d".
        lookback: Number of most recent bars to return.
    """
    return tick_data.get_ohlcv(timeframe=timeframe, lookback=lookback)


@mcp.tool()
def get_gold_session_summary() -> dict:
    """Today's session stats: open, last, high, low, range, % change, tick count."""
    return tick_data.get_session_summary()


# ---------- Microstructure (the differentiator) ----------

@mcp.tool()
def get_gold_tick_velocity(window_seconds: int = 60) -> dict:
    """Recent tick activity: ticks/sec, price movement, average tick size.

    Detects whether the market is quiet, normal, active, or in a news
    burst. Useful before sizing into a trade.

    Args:
        window_seconds: How far back to measure activity (default 60s).
    """
    return microstructure.get_tick_velocity(window_seconds=window_seconds)


@mcp.tool()
def get_gold_spread_stats(lookback_hours: int = 24) -> dict:
    """Spread distribution and percentile rank of the current spread.

    Tells you whether the current bid-ask spread is tight (normal
    liquidity), wide (illiquid / news), or extreme.

    Args:
        lookback_hours: History window for the distribution (default 24h).
    """
    return microstructure.get_spread_stats(lookback_hours=lookback_hours)


@mcp.tool()
def get_gold_session_microstructure(lookback_days: int = 20) -> dict:
    """Asia / Europe / US session character: tick volume, range, spread.

    Computed from the tick archive — shows which session is most active
    and has the widest range on average.

    Args:
        lookback_days: Days of tick history to aggregate (default 20).
    """
    return microstructure.get_session_microstructure(lookback_days=lookback_days)


# ---------- L2 (factual top-of-book only; derived metrics deferred) ----------

@mcp.tool()
def get_gold_top_of_book() -> dict:
    """Best bid / best ask snapshot from the latest L2 orderbook.

    Reports the raw top-level prices and sizes from the MT5 DOM. Note
    that the IC Markets DOM publishes 3-5 levels of broker-aggregated
    liquidity, not interbank depth, so deeper-book imbalance metrics
    are intentionally not exposed in this version.
    """
    return l2_data.get_top_of_book()


# ---------- Macro context ----------

@mcp.tool()
def get_macro_context() -> dict:
    """Macro snapshot relevant to gold: DXY, US10Y/02Y, SPX, VIX, BTC, silver, oil.

    Each entry gives last close, day change, and day % change.
    """
    return macro_data.get_macro_context()


@mcp.tool()
def get_gold_correlations(lookback_days: int = 60) -> dict:
    """Correlation of gold daily returns vs macro assets.

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


# ---------- Proprietary macro (event-driven currency strength) ----------

@mcp.tool()
def get_macro_strength() -> dict:
    """Event-driven macro strength score for 8 major currencies.

    Aggregates economic-calendar surprises (actual vs forecast) with
    exponential time-decay (default 30-day half-life over a 90-day
    window). Each currency receives a macro coefficient in [-10, +10]
    where positive means recent data surprised hawkish.

    Includes a derived gold macro bias: positive USD coefficient is
    typically bearish for gold and vice-versa.

    Configure with `GOLD_MCP_MACRO_STRENGTH_FILE` env var pointing at
    the engine's JSON output. Returns `not_configured` otherwise.
    """
    return macro_strength_adapter.get_macro_strength()


@mcp.tool()
def get_news_calendar(
    lookforward_days: int = 7,
    lookback_days: int = 2,
    min_impact: str = "medium",
    gold_only: bool = True,
) -> dict:
    """Upcoming + recent macro-calendar events relevant to gold.

    Filters a local economic-calendar archive by date window, impact
    level, and (by default) gold-relevant currencies (USD, EUR, JPY,
    GBP, CNY, CHF). Highlights the next high-impact USD event since
    USD releases dominate gold's macro reaction function.

    Args:
        lookforward_days: Days ahead to include (default 7).
        lookback_days: Days behind to include (default 2).
        min_impact: "low", "medium", or "high" (default "medium").
        gold_only: Restrict to gold-relevant currencies (default True).

    Configure with `GOLD_MCP_NEWS_CALENDAR_FILE` env var.
    """
    return news_calendar_adapter.get_news_calendar(
        lookforward_days=lookforward_days,
        lookback_days=lookback_days,
        min_impact=min_impact,
        gold_only=gold_only,
    )


# ---------- Proprietary strategy intelligence ----------

@mcp.tool()
def get_xau_daily_setup_config() -> dict:
    """OOS-validated parameters and performance of the daily-setup scanner.

    Returns the locked configuration (swing lookback, vol z-score
    thresholds, wick ratio, time-of-day filters) and recent backtest
    summary stats.

    Configure with `GOLD_MCP_STRATEGY_RESULTS_DIR`.
    """
    return strategy_adapter.get_xau_daily_setup_config()


@mcp.tool()
def get_xau_asian_box_stats() -> dict:
    """Asian-box state distribution and range-expansion correlations.

    Classifies each day's Asian-session box as TIGHT / NORMAL / EXPANDED
    based on Average Daily Range, and reports the empirical follow-up
    behavior of the London/NY session range conditional on that state.
    """
    return strategy_adapter.get_xau_asian_box_stats()


@mcp.tool()
def get_xau_institutional_footprint() -> dict:
    """Historical institutional footprint signature on XAUUSD."""
    return strategy_adapter.get_xau_institutional_footprint()


@mcp.tool()
def get_xau_gamma_regime() -> dict:
    """Gamma-regime classification and its effect on XAUUSD daily behavior."""
    return strategy_adapter.get_xau_gamma_regime()


@mcp.tool()
def get_xau_trend_entry_signature() -> dict:
    """Statistical signature of clean trend entries derived from OOS analysis."""
    return strategy_adapter.get_xau_trend_entry_signature()


# ---------- Vietnam macro ----------

@mcp.tool()
def get_vn_macro() -> dict:
    """Vietnam-specific macro context for XAUUSD analysis.

    Returns USD/VND, EUR/VND, CNY/VND with 5-day change plus an implied
    world-parity gold price (VND per troy oz and per tael / lượng) that
    Vietnamese traders can compare against locally observed prices
    (SJC, DOJI, PNJ) to estimate the local premium.
    """
    return vn_macro_adapter.get_vn_macro()


@mcp.tool()
def estimate_vn_gold_premium(local_price_vnd_per_tael: float) -> dict:
    """Estimate VN gold premium given a user-supplied local price.

    Compares the user-observed local gold price (e.g. SJC ask in VND
    per tael / lượng) against the world-parity benchmark to compute
    the local premium in absolute VND and percent terms.

    Args:
        local_price_vnd_per_tael: User-observed local gold price.
    """
    return vn_macro_adapter.estimate_vn_gold_premium(local_price_vnd_per_tael)


# ---------- AI analyst (Layer 3) ----------

@mcp.tool()
def analyze_gold_setup(timeframe: str = "1h") -> dict:
    """One-call structured read on the current XAUUSD setup.

    Aggregates 10+ underlying tools (price, spread regime, tick activity,
    session, L2 top of book, macro snapshot, macro strength, upcoming
    events, Asian-box context, data freshness) into a single structured
    object plus a concise top-line bulleted read.

    Args:
        timeframe: Bar timeframe used for recent_bars (default "1h").
    """
    return analyst.analyze_gold_setup(timeframe=timeframe)


@mcp.tool()
def daily_briefing() -> dict:
    """Morning briefing aggregator for XAUUSD.

    Returns a sectioned briefing: overnight recap, macro context, today
    event watch, session microstructure, Asian-box context, seasonality,
    and a health check.
    """
    return analyst.daily_briefing()


@mcp.tool()
def risk_assessment(side: str, entry_price: float, stop_price: float, size_usd: float) -> dict:
    """Quick risk assessment for a hypothetical XAUUSD position.

    Combines spread regime, tick velocity, upcoming high-impact events,
    and Asian-box state to flag elevated execution / event / volatility
    risks for the proposed trade.

    Args:
        side: "long" or "short".
        entry_price: planned entry price.
        stop_price: planned stop-loss price.
        size_usd: notional size in USD.
    """
    return analyst.risk_assessment(
        side=side, entry_price=entry_price, stop_price=stop_price, size_usd=size_usd,
    )


# ---------- Health ----------

@mcp.tool()
def get_data_freshness() -> dict:
    """Health check — how recent is the underlying tick data?

    Returns status (live / recent / stale / very_stale), last tick time,
    and a warning if the stream appears down.
    """
    return microstructure.get_data_freshness()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
