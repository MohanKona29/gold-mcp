"""Tool registration smoke test — verifies the server boots and exposes
every expected tool by name. Doesn't require any private data sources.
"""
import asyncio

EXPECTED_TOOLS = {
    # Foundation
    "get_gold_price",
    "get_gold_ohlcv",
    "get_gold_session_summary",
    "get_gold_tick_velocity",
    "get_gold_spread_stats",
    "get_gold_session_microstructure",
    "get_gold_top_of_book",
    # Public macro
    "get_macro_context",
    "get_gold_correlations",
    "get_gold_seasonality",
    # Layer 1 — proprietary data
    "get_macro_strength",
    "get_news_calendar",
    # Layer 2 — strategy intelligence
    "get_xau_daily_setup_config",
    "get_xau_asian_box_stats",
    "get_xau_institutional_footprint",
    "get_xau_gamma_regime",
    "get_xau_trend_entry_signature",
    # Vietnam macro
    "get_vn_macro",
    "estimate_vn_gold_premium",
    # Layer 3 — AI analyst
    "analyze_gold_setup",
    "daily_briefing",
    "risk_assessment",
    # Health
    "get_data_freshness",
}


def test_all_expected_tools_registered():
    from gold_mcp.server import mcp

    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    missing = EXPECTED_TOOLS - names
    extra = names - EXPECTED_TOOLS
    assert not missing, f"Missing tools: {missing}"
    assert not extra, f"Unexpected tools: {extra}"


def test_graceful_degradation_without_env_vars(monkeypatch):
    """Private-data tools must return a structured 'not_configured' error
    rather than crashing when env vars are unset.
    """
    for var in [
        "GOLD_MCP_MACRO_STRENGTH_FILE",
        "GOLD_MCP_NEWS_CALENDAR_FILE",
        "GOLD_MCP_STRATEGY_RESULTS_DIR",
    ]:
        monkeypatch.delenv(var, raising=False)

    from gold_mcp.adapters.macro_strength import get_macro_strength
    from gold_mcp.adapters.news_calendar import get_news_calendar
    from gold_mcp.adapters.strategy import get_xau_daily_setup_config

    for fn in (get_macro_strength, get_news_calendar, get_xau_daily_setup_config):
        out = fn()
        assert out.get("error") == "not_configured", f"{fn.__name__}: {out}"
        assert "hint" in out
