"""gold-mcp FastMCP server with 3-tier licensing.

Free tier (always on): 8 tools wrapping public Yahoo Finance data —
price, OHLCV, macro, correlations, seasonality, VN parity, and the
one-call aggregator.

Pro tier (license required): +6 tools — advanced TA (Bollinger,
Ichimoku, Fibonacci), multi-timeframe snapshot, correlation regime
detection, setup scanner, gold-specific alerts.

Premium tier (license required): +4 tools — vectorized backtest engine
on 4 strategies, walk-forward validation, grid optimizer, intraday
seasonality.

License gating uses offline Ed25519 verification — no phone-home, no
SaaS backend. Set GOLD_MCP_LICENSE_KEY to unlock Pro/Premium tools.

Educational and research use only — not financial advice.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import (
    ai_analyst,
    analyst,
    analytics,
    cache,
    gold_data,
    macro_data,
    mtf,
    premium_tools,
    pro_tools,
    realtime,
    regime,
    reports,
    risk_mgmt,
    smart_money,
)
from . import license as lic
from .adapters import vn_macro as vn_macro_adapter

try:
    from .brokers import mt5 as mt5_adapter  # type: ignore
    _MT5_AVAILABLE = True
except ImportError:
    mt5_adapter = None  # type: ignore
    _MT5_AVAILABLE = False

mcp = FastMCP("gold-mcp")
_TIER = lic.current_tier()


# =====================================================================
# FREE TIER — always registered
# =====================================================================

@mcp.tool()
def diagnostic() -> dict:
    """Show server license tier and available tools."""
    return {
        "license": lic.status(),
        "tier_active": _TIER.name.lower(),
        "tier_unlocks": {
            "free": [
                "diagnostic", "get_gold_price", "get_gold_ohlcv",
                "get_macro_context", "get_gold_correlations",
                "get_gold_seasonality", "get_vn_macro",
                "estimate_vn_gold_premium", "gold_market_snapshot",
                "cache_purge",
                "paxg_worker_status", "get_paxg_tick", "get_paxg_ohlcv_realtime",
                "mt5_attach", "mt5_detach", "mt5_status", "mt5_find_symbol",
                "mt5_get_tick", "mt5_get_ohlcv", "mt5_get_ticks", "mt5_account_info",
            ] if _MT5_AVAILABLE else [
                "diagnostic", "get_gold_price", "get_gold_ohlcv",
                "get_macro_context", "get_gold_correlations",
                "get_gold_seasonality", "get_vn_macro",
                "estimate_vn_gold_premium", "gold_market_snapshot",
                "cache_purge",
                "paxg_worker_status", "get_paxg_tick", "get_paxg_ohlcv_realtime",
            ],
            "pro": [
                "analyze_gold_advanced", "multi_timeframe_snapshot",
                "gold_correlation_regime", "get_gold_setups",
                "create_gold_alert", "list_gold_alerts", "delete_gold_alert",
            ],
            "premium": [
                "backtest_gold_strategy", "gold_walk_forward",
                "optimize_gold_strategy", "gold_intraday_seasonality",
            ],
            "ultra": [
                "smc_full_scan", "detect_order_blocks",
                "detect_fair_value_gaps", "detect_liquidity_sweeps",
                "detect_market_structure",
                "classify_regime", "mtf_alignment",
                "kelly_fraction", "fixed_fractional_size",
                "optimal_f", "risk_of_ruin",
                "monte_carlo_paths", "value_at_risk",
                "prob_hit_target_or_stop",
                "ai_daily_briefing", "ai_setup_explanation",
                "generate_html_tearsheet", "generate_markdown_briefing",
            ],
        },
    }


@cache.cached("price", ttl_seconds=60)
def _get_gold_price_cached() -> dict:
    return gold_data.get_gold_price()


@mcp.tool()
def get_gold_price() -> dict:
    """Latest gold (XAUUSD / GC=F) price and 24h change from Yahoo Finance."""
    return _get_gold_price_cached()


@cache.cached("ohlcv", ttl_seconds=300)
def _get_gold_ohlcv_cached(timeframe: str, lookback: int) -> dict:
    return gold_data.get_gold_ohlcv(timeframe=timeframe, lookback=lookback)


@mcp.tool()
def get_gold_ohlcv(timeframe: str = "1h", lookback: int = 24) -> dict:
    """Historical OHLCV bars for gold from Yahoo Finance.

    Args:
        timeframe: One of "1m", "5m", "15m", "30m", "1h", "4h", "1d", "1wk", "1mo".
        lookback: Number of most recent bars to return.
    """
    return _get_gold_ohlcv_cached(timeframe, lookback)


@cache.cached("macro", ttl_seconds=600)
def _get_macro_context_cached() -> dict:
    return macro_data.get_macro_context()


@mcp.tool()
def get_macro_context() -> dict:
    """Macro snapshot relevant to gold: DXY, US10Y/02Y, SPX, VIX, BTC, silver, oil."""
    return _get_macro_context_cached()


@cache.cached("correlations", ttl_seconds=3600)
def _get_correlations_cached(lookback_days: int) -> dict:
    return macro_data.get_correlation_matrix(lookback_days=lookback_days)


@mcp.tool()
def get_gold_correlations(lookback_days: int = 60) -> dict:
    """Correlation of gold daily returns vs the macro basket."""
    return _get_correlations_cached(lookback_days)


@cache.cached("seasonality", ttl_seconds=86400)
def _get_seasonality_cached(group_by: str, lookback_years: int) -> dict:
    return analytics.get_seasonality(group_by=group_by, lookback_years=lookback_years)


@mcp.tool()
def get_gold_seasonality(group_by: str = "dow", lookback_years: int = 5) -> dict:
    """Historical seasonality stats for gold returns.

    Args:
        group_by: "dow" (day of week) or "month".
        lookback_years: Years of history to include.
    """
    return _get_seasonality_cached(group_by, lookback_years)


@cache.cached("vn_macro", ttl_seconds=3600)
def _get_vn_macro_cached() -> dict:
    return vn_macro_adapter.get_vn_macro()


@mcp.tool()
def get_vn_macro() -> dict:
    """USD/VND + cross rates + implied world-parity gold price in VND."""
    return _get_vn_macro_cached()


@mcp.tool()
def estimate_vn_gold_premium(local_price_vnd_per_tael: float) -> dict:
    """Compare a user-supplied local VN gold price to world parity."""
    return vn_macro_adapter.estimate_vn_gold_premium(local_price_vnd_per_tael)


@mcp.tool()
def gold_market_snapshot(timeframe: str = "1h") -> dict:
    """One-call structured snapshot of gold's current market state."""
    return analyst.gold_market_snapshot(timeframe=timeframe)


@mcp.tool()
def cache_purge() -> dict:
    """Sweep expired entries from the on-disk cache."""
    return cache.purge_expired()


# ---------- Realtime PAXG tick feed (Binance WebSocket) ----------
# These tools read from a SQLite file populated by a separate worker
# process. Start the worker with:  python -m gold_mcp.realtime
# PAXG (Paxos Gold) tracks XAU/USD within ~0.1-0.3%.

@mcp.tool()
def paxg_worker_status() -> dict:
    """Health of the local PAXG tick-capture worker.

    Returns alive=true if the last tick is fresher than 30 seconds.
    If alive=false with reason=db_missing or no_heartbeat, start the
    worker: `python -m gold_mcp.realtime`.
    """
    return realtime.worker_status()


@mcp.tool()
def get_paxg_tick() -> dict:
    """Most recent PAXG trade — free real-time gold proxy via Binance."""
    return realtime.latest_tick()


@mcp.tool()
def get_paxg_ohlcv_realtime(seconds_per_bar: int = 10, lookback_bars: int = 60) -> dict:
    """Build OHLCV bars from PAXG tick stream on the fly.

    Args:
        seconds_per_bar: Bar size in seconds (1-300). 10 = 10-second bars.
        lookback_bars: How many most-recent bars to return (1-500).
    """
    return realtime.realtime_ohlcv(seconds_per_bar, lookback_bars)


# ---------- BYOK: MT5 broker adapter (Windows only) ----------
# Users connect their own MT5 terminal. gold-mcp never stores credentials
# and never redistributes broker data — it only runs analysis on the
# user's already-licensed local feed.

if _MT5_AVAILABLE:

    @mcp.tool()
    def mt5_attach(terminal_path: str | None = None) -> dict:
        """Attach to a running MT5 terminal you have already logged into.

        Args:
            terminal_path: Full path to terminal64.exe, e.g.
                "C:\\\\Program Files\\\\MetaTrader 5 IC Markets Global\\\\terminal64.exe".
                If None, MT5 auto-detects.
        """
        return mt5_adapter.attach(terminal_path)

    @mcp.tool()
    def mt5_detach() -> dict:
        """Disconnect from the MT5 terminal."""
        return mt5_adapter.detach()

    @mcp.tool()
    def mt5_status() -> dict:
        """Connection status of the attached MT5 terminal."""
        return mt5_adapter.status()

    @mcp.tool()
    def mt5_find_symbol(query: str = "gold") -> dict:
        """List MT5 symbols whose name contains `query` (case-insensitive).

        Brokers name gold differently — XAUUSD, XAUUSD.r, XAUUSDm, GOLD,
        GOLD.cash — so resolve the right one before calling other tools.
        """
        return mt5_adapter.find_symbol(query)

    @mcp.tool()
    def mt5_get_tick(symbol: str = "XAUUSD") -> dict:
        """Latest bid/ask/last from the attached MT5 terminal."""
        return mt5_adapter.get_tick(symbol)

    @mcp.tool()
    def mt5_get_ohlcv(symbol: str = "XAUUSD", timeframe: str = "1h", lookback: int = 100) -> dict:
        """Broker OHLCV bars.

        Args:
            symbol: Broker-specific symbol (e.g. XAUUSD).
            timeframe: "1m" "5m" "15m" "30m" "1h" "4h" "1d" etc.
            lookback: Number of most recent bars (1-5000).
        """
        return mt5_adapter.get_ohlcv(symbol, timeframe, lookback)

    @mcp.tool()
    def mt5_get_ticks(symbol: str = "XAUUSD", seconds_back: int = 60, limit: int = 5000) -> dict:
        """Raw tick history for the last `seconds_back` seconds."""
        return mt5_adapter.get_ticks(symbol, seconds_back, limit)

    @mcp.tool()
    def mt5_account_info() -> dict:
        """Balance, equity, margin, leverage — used for position sizing."""
        return mt5_adapter.account_info()


# =====================================================================
# PRO TIER — registered only if tier >= PRO
# =====================================================================

if _TIER >= lic.Tier.PRO:

    @mcp.tool()
    def analyze_gold_advanced(timeframe: str = "1h", lookback: int = 120) -> dict:
        """Bollinger + Ichimoku + Fibonacci levels on XAUUSD. Pro tier."""
        return pro_tools.analyze_gold_advanced(timeframe, lookback)

    @mcp.tool()
    def multi_timeframe_snapshot(timeframes: list[str] | None = None) -> dict:
        """Pull gold OHLCV + RSI across several timeframes in one call. Pro tier.

        Args:
            timeframes: e.g. ["5m", "1h", "4h", "1d"]. Defaults to those four.
        """
        return pro_tools.multi_timeframe_snapshot(timeframes)

    @mcp.tool()
    def gold_correlation_regime(lookback_short: int = 20, lookback_long: int = 60) -> dict:
        """Detect regime shifts in gold ↔ macro correlations. Pro tier.

        Flags assets where short-window correlation diverges from
        long-window — e.g. "DXY decoupling".
        """
        return pro_tools.gold_correlation_regime(lookback_short, lookback_long)

    @mcp.tool()
    def get_gold_setups(timeframe: str = "1h", lookback: int = 100) -> dict:
        """Scan for confluence setups (RSI + Bollinger + Ichimoku). Pro tier."""
        return pro_tools.get_gold_setups(timeframe, lookback)

    @mcp.tool()
    def create_gold_alert(condition: str, threshold: float,
                          webhook_url: str | None = None) -> dict:
        """Create a gold alert rule. Pro tier.

        Args:
            condition: price_above | price_below | rsi_above | rsi_below | premium_above
            threshold: numeric threshold
            webhook_url: optional Discord/Slack webhook
        """
        return pro_tools.create_gold_alert(condition, threshold, webhook_url)

    @mcp.tool()
    def list_gold_alerts() -> dict:
        """List all stored gold alert rules. Pro tier."""
        return {"alerts": pro_tools.list_gold_alerts()}

    @mcp.tool()
    def delete_gold_alert(alert_id: int) -> dict:
        """Delete a gold alert by id. Pro tier."""
        return pro_tools.delete_gold_alert(alert_id)


# =====================================================================
# PREMIUM TIER — registered only if tier == PREMIUM
# =====================================================================

if _TIER >= lic.Tier.PREMIUM:

    @mcp.tool()
    def backtest_gold_strategy(strategy_name: str, params: dict | None = None,
                               lookback_days: int = 500,
                               fee_bps: float = 2.0) -> dict:
        """Vectorized backtest on XAUUSD daily bars. Premium tier.

        Args:
            strategy_name: rsi_mean_reversion | macd_trend | sma_crossover | breakout_donchian
            params: strategy-specific kwargs (e.g. {"window": 14, "oversold": 30})
            lookback_days: days of daily history
            fee_bps: round-trip fee in basis points
        """
        return premium_tools.backtest_gold_strategy(
            strategy_name, params, lookback_days, fee_bps
        )

    @mcp.tool()
    def gold_walk_forward(strategy_name: str, params: dict | None = None,
                          train_window: int = 252, test_window: int = 63,
                          lookback_days: int = 1500) -> dict:
        """Walk-forward backtest on XAUUSD: rolling out-of-sample. Premium tier."""
        return premium_tools.gold_walk_forward(
            strategy_name, params, train_window, test_window, lookback_days
        )

    @mcp.tool()
    def optimize_gold_strategy(strategy_name: str, param_grid: dict,
                               lookback_days: int = 1000,
                               metric: str = "sharpe") -> dict:
        """Grid-search optimizer on XAUUSD. Premium tier.

        Args:
            strategy_name: as in backtest_gold_strategy
            param_grid: e.g. {"window": [10, 14, 20], "oversold": [25, 30, 35]}
            metric: sharpe | total_return_pct | profit_factor
        """
        return premium_tools.optimize_gold_strategy(
            strategy_name, param_grid, lookback_days, metric
        )

    @mcp.tool()
    def gold_intraday_seasonality(group_by: str = "hour",
                                   lookback_days: int = 60) -> dict:
        """Intraday seasonality of gold returns. Premium tier.

        Args:
            group_by: "hour" or "session" (asia / london / ny overlap)
            lookback_days: history window (max 60 due to Yahoo 1h limit)
        """
        return premium_tools.gold_intraday_seasonality(group_by, lookback_days)


# =====================================================================
# ULTRA TIER — registered only if tier == ULTRA
# =====================================================================

if _TIER >= lic.Tier.ULTRA:

    # ---- Smart Money Concepts ----

    @mcp.tool()
    def smc_full_scan(timeframe: str = "1h", lookback: int = 100) -> dict:
        """Composite SMC scan: structure + order blocks + FVG + sweeps + bias. Ultra tier."""
        bars = gold_data.get_gold_ohlcv(timeframe=timeframe, lookback=lookback)
        if "error" in bars:
            return bars
        return smart_money.smc_full_scan(bars["bars"])

    @mcp.tool()
    def detect_order_blocks(timeframe: str = "1h", lookback: int = 100,
                            impulse_threshold_atr: float = 1.5) -> dict:
        """Detect bullish/bearish order blocks. Ultra tier."""
        bars = gold_data.get_gold_ohlcv(timeframe=timeframe, lookback=lookback)
        if "error" in bars:
            return bars
        return smart_money.detect_order_blocks(bars["bars"], lookback, impulse_threshold_atr)

    @mcp.tool()
    def detect_fair_value_gaps(timeframe: str = "1h", lookback: int = 100) -> dict:
        """Detect unfilled Fair Value Gaps (3-candle imbalances). Ultra tier."""
        bars = gold_data.get_gold_ohlcv(timeframe=timeframe, lookback=lookback)
        if "error" in bars:
            return bars
        return smart_money.detect_fair_value_gaps(bars["bars"], lookback)

    @mcp.tool()
    def detect_liquidity_sweeps(timeframe: str = "1h", lookback: int = 100) -> dict:
        """Detect stop-hunt liquidity sweeps (breach + reverse). Ultra tier."""
        bars = gold_data.get_gold_ohlcv(timeframe=timeframe, lookback=lookback)
        if "error" in bars:
            return bars
        return smart_money.detect_liquidity_sweeps(bars["bars"], lookback)

    @mcp.tool()
    def detect_market_structure(timeframe: str = "1h", lookback: int = 100) -> dict:
        """Label market structure: CHOCH (reversal) / BOS (continuation). Ultra tier."""
        bars = gold_data.get_gold_ohlcv(timeframe=timeframe, lookback=lookback)
        if "error" in bars:
            return bars
        return smart_money.detect_market_structure(bars["bars"])

    # ---- Regime ----

    @mcp.tool()
    def classify_regime(timeframe: str = "1d", lookback: int = 500,
                        q: int = 4, hurst_lag: int = 50) -> dict:
        """Composite regime tag: Hurst + Lo-MacKinlay variance ratio. Ultra tier."""
        bars = gold_data.get_gold_ohlcv(timeframe=timeframe, lookback=lookback)
        if "error" in bars:
            return bars
        closes = [b["close"] for b in bars["bars"]]
        return regime.classify_regime(closes, q=q, hurst_lag=hurst_lag)

    # ---- Multi-Timeframe ----

    @mcp.tool()
    def mtf_alignment() -> dict:
        """Composite confluence D1/H4/H1 with alignment score 0-100. Ultra tier."""
        return mtf.mtf_alignment()

    # ---- Position sizing & risk ----

    @mcp.tool()
    def kelly_fraction(win_rate: float, payoff_ratio: float,
                       kelly_multiplier: float = 0.5) -> dict:
        """Kelly criterion sizing (half-Kelly default for safety). Ultra tier."""
        return risk_mgmt.kelly_fraction(win_rate, payoff_ratio, kelly_multiplier)

    @mcp.tool()
    def fixed_fractional_size(account_size: float, risk_pct: float,
                              stop_distance: float,
                              contract_value: float = 1.0) -> dict:
        """Classic fixed-fractional position size. Ultra tier."""
        return risk_mgmt.fixed_fractional(account_size, risk_pct, stop_distance, contract_value)

    @mcp.tool()
    def optimal_f(returns: list[float]) -> dict:
        """Ralph Vince Optimal-f geometric-mean-maximizing fraction. Ultra tier."""
        return risk_mgmt.optimal_f(returns)

    @mcp.tool()
    def risk_of_ruin(win_rate: float, payoff_ratio: float, risk_pct: float,
                     ruin_threshold_pct: float = 50.0,
                     n_trades: int = 500, n_simulations: int = 5000) -> dict:
        """Monte Carlo probability of drawing down past ruin threshold. Ultra tier."""
        return risk_mgmt.risk_of_ruin(
            win_rate, payoff_ratio, risk_pct, ruin_threshold_pct,
            n_trades, n_simulations
        )

    # ---- Monte Carlo ----

    @mcp.tool()
    def monte_carlo_paths(lookback_days: int = 500, n_paths: int = 1000,
                          n_steps: int = 60, method: str = "bootstrap") -> dict:
        """Bootstrap or parametric MC simulation of gold's path. Ultra tier.

        Args:
            method: "bootstrap" (resample historical) or "parametric" (gaussian)
        """
        bars = gold_data.get_gold_ohlcv(timeframe="1d", lookback=lookback_days)
        if "error" in bars:
            return bars
        closes = [b["close"] for b in bars["bars"]]
        rets = [closes[i] / closes[i-1] - 1 for i in range(1, len(closes))]
        return risk_mgmt.simulate_paths(rets, n_paths=n_paths, n_steps=n_steps,
                                          method=method)

    @mcp.tool()
    def value_at_risk(lookback_days: int = 252, confidence: float = 0.95) -> dict:
        """Historical VaR + CVaR on gold daily returns. Ultra tier."""
        bars = gold_data.get_gold_ohlcv(timeframe="1d", lookback=lookback_days)
        if "error" in bars:
            return bars
        closes = [b["close"] for b in bars["bars"]]
        rets = [closes[i] / closes[i-1] - 1 for i in range(1, len(closes))]
        return risk_mgmt.value_at_risk(rets, confidence=confidence)

    @mcp.tool()
    def prob_hit_target_or_stop(entry_price: float, target_price: float,
                                 stop_price: float, max_steps: int = 100,
                                 n_paths: int = 5000,
                                 lookback_days: int = 252) -> dict:
        """Monte Carlo: probability target hits before stop in horizon. Ultra tier."""
        bars = gold_data.get_gold_ohlcv(timeframe="1d", lookback=lookback_days)
        if "error" in bars:
            return bars
        closes = [b["close"] for b in bars["bars"]]
        rets = [closes[i] / closes[i-1] - 1 for i in range(1, len(closes))]
        return risk_mgmt.prob_hit_target_or_stop(
            rets, entry_price, target_price, stop_price,
            n_paths=n_paths, max_steps=max_steps,
        )

    # ---- AI Analyst (BYOK Anthropic) ----

    @mcp.tool()
    def ai_daily_briefing(model: str = "claude-sonnet-4-6",
                          max_tokens: int = 1500) -> dict:
        """LLM-driven daily briefing with structured JSON output. Ultra tier.

        Requires ANTHROPIC_API_KEY in env. Bills against your Claude account.
        """
        return ai_analyst.ai_daily_briefing(model=model, max_tokens=max_tokens)

    @mcp.tool()
    def ai_setup_explanation(timeframe: str = "1h",
                             model: str = "claude-haiku-4-5-20251001",
                             max_tokens: int = 800) -> dict:
        """Cheaper Haiku-based plain-English read of current setup. Ultra tier.

        Requires ANTHROPIC_API_KEY in env.
        """
        return ai_analyst.ai_setup_explanation(timeframe, model, max_tokens)

    # ---- Report generation ----

    @mcp.tool()
    def generate_html_tearsheet() -> dict:
        """Build a polished HTML tearsheet (writes to disk, returns path). Ultra tier."""
        return reports.generate_html_tearsheet()

    @mcp.tool()
    def generate_markdown_briefing() -> dict:
        """Build a Markdown daily briefing (writes to disk, returns path + content). Ultra tier."""
        return reports.generate_markdown_briefing()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
