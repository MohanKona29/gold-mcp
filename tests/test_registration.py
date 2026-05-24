"""Tool registration smoke test — verifies the server boots and exposes
every expected tool by name. All tools use public data only and require
no configuration.
"""
import asyncio

EXPECTED_TOOLS = {
    # Price + OHLCV
    "get_gold_price",
    "get_gold_ohlcv",
    # Macro context
    "get_macro_context",
    "get_gold_correlations",
    "get_gold_seasonality",
    # Vietnam
    "get_vn_macro",
    "estimate_vn_gold_premium",
    # Aggregator
    "gold_market_snapshot",
}


def test_all_expected_tools_registered():
    from gold_mcp.server import mcp

    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    missing = EXPECTED_TOOLS - names
    extra = names - EXPECTED_TOOLS
    assert not missing, f"Missing tools: {missing}"
    assert not extra, f"Unexpected tools: {extra}"


def test_server_boots_with_empty_environment(monkeypatch):
    """Server must construct successfully without any environment variables."""
    for var in list(os_env_keys()):
        if var.startswith("GOLD_MCP_"):
            monkeypatch.delenv(var, raising=False)

    from gold_mcp.server import mcp
    tools = asyncio.run(mcp.list_tools())
    assert len(tools) == len(EXPECTED_TOOLS)


def os_env_keys():
    import os
    return list(os.environ.keys())
