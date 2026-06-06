"""Tool registration smoke tests — verifies tier-gated registration."""
import asyncio
import importlib
import os
from pathlib import Path

FREE_TOOLS = {
    "diagnostic",
    "get_gold_price", "get_gold_ohlcv",
    "get_macro_context", "get_gold_correlations", "get_gold_seasonality",
    "get_vn_macro", "estimate_vn_gold_premium",
    "gold_market_snapshot",
    "cache_purge",
    # v4.1 (2026-06-06): realtime PAXG via Binance public WS — always free, OS-independent
    "paxg_worker_status", "get_paxg_tick", "get_paxg_ohlcv_realtime",
}

# v4.1 (2026-06-06): MT5 BYOK adapter — only loads if MetaTrader5 importable
# (Windows-only + user-installed). Tests must conditionally include these.
try:
    import MetaTrader5  # noqa: F401
    _MT5_AVAILABLE = True
except ImportError:
    _MT5_AVAILABLE = False

if _MT5_AVAILABLE:
    FREE_TOOLS = FREE_TOOLS | {
        "mt5_attach", "mt5_detach", "mt5_status", "mt5_find_symbol",
        "mt5_get_tick", "mt5_get_ohlcv", "mt5_get_ticks", "mt5_account_info",
    }

PRO_TOOLS = FREE_TOOLS | {
    "analyze_gold_advanced", "multi_timeframe_snapshot",
    "gold_correlation_regime", "get_gold_setups",
    "create_gold_alert", "list_gold_alerts", "delete_gold_alert",
}

PREMIUM_TOOLS = PRO_TOOLS | {
    "backtest_gold_strategy", "gold_walk_forward",
    "optimize_gold_strategy", "gold_intraday_seasonality",
}

ULTRA_TOOLS = PREMIUM_TOOLS | {
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
}


def _reload_server():
    import gold_mcp.server as srv
    importlib.reload(srv)
    return srv


def _registered_names(srv):
    return {t.name for t in asyncio.run(srv.mcp.list_tools())}


def _issue(tier: str) -> str:
    from gold_mcp import issue_license
    return issue_license.issue(
        tier, "test@x.com", days=7,
        key_dir=Path(__file__).parent.parent / ".dev_keys",
    )


def test_free_tier_registers_only_free_tools(monkeypatch):
    monkeypatch.delenv("GOLD_MCP_LICENSE_KEY", raising=False)
    names = _registered_names(_reload_server())
    assert names == FREE_TOOLS, f"diff: {names ^ FREE_TOOLS}"


def test_pro_tier_unlocks_pro_tools(monkeypatch):
    monkeypatch.setenv("GOLD_MCP_LICENSE_KEY", _issue("pro"))
    names = _registered_names(_reload_server())
    assert names == PRO_TOOLS, f"diff: {names ^ PRO_TOOLS}"


def test_premium_tier_unlocks_premium_tools(monkeypatch):
    monkeypatch.setenv("GOLD_MCP_LICENSE_KEY", _issue("premium"))
    names = _registered_names(_reload_server())
    assert names == PREMIUM_TOOLS, f"diff: {names ^ PREMIUM_TOOLS}"


def test_ultra_tier_unlocks_all_tools(monkeypatch):
    monkeypatch.setenv("GOLD_MCP_LICENSE_KEY", _issue("ultra"))
    names = _registered_names(_reload_server())
    assert names == ULTRA_TOOLS, f"diff: {names ^ ULTRA_TOOLS}"


def test_invalid_license_falls_back_to_free(monkeypatch):
    monkeypatch.setenv("GOLD_MCP_LICENSE_KEY", "garbage.invalid")
    names = _registered_names(_reload_server())
    assert names == FREE_TOOLS


def test_server_boots_with_empty_environment(monkeypatch):
    for var in list(os.environ.keys()):
        if var.startswith("GOLD_MCP_"):
            monkeypatch.delenv(var, raising=False)
    names = _registered_names(_reload_server())
    assert len(names) == len(FREE_TOOLS)
