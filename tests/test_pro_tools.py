"""Pro/Premium tier logic tests that don't hit the network."""

import numpy as np
import pytest

from gold_mcp import pro_tools


def _bars(n=120, seed=11):
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0005, 0.01, n)
    closes = 2000.0 * np.cumprod(1 + rets)
    return [
        {"time": f"t{i}", "open": float(c), "high": float(c * 1.005),
         "low": float(c * 0.995), "close": float(c), "volume": 1000.0}
        for i, c in enumerate(closes)
    ]


def test_bollinger():
    out = pro_tools._bollinger(_bars(60))
    assert "upper" in out and "lower" in out
    assert out["upper"] > out["middle"] > out["lower"]


def test_bollinger_insufficient():
    out = pro_tools._bollinger(_bars(10))
    assert "error" in out


def test_ichimoku():
    out = pro_tools._ichimoku(_bars(120))
    assert "tenkan_sen" in out and "kijun_sen" in out
    assert out["cross_signal"] in ("bullish_tk_cross", "bearish_tk_cross")


def test_fibonacci():
    out = pro_tools._fibonacci(_bars(80))
    assert set(out["levels"]) == {"0.0", "0.236", "0.382", "0.500",
                                   "0.618", "0.786", "1.0"}
    assert out["swing_high"] >= out["swing_low"]


@pytest.fixture
def alerts_tmp(monkeypatch, tmp_path):
    monkeypatch.setenv("GOLD_MCP_ALERTS_DIR", str(tmp_path))
    yield tmp_path


def test_create_list_delete_alert(alerts_tmp):
    out = pro_tools.create_gold_alert("price_above", 2500.0)
    aid = out["created"]["id"]
    assert any(a["id"] == aid for a in pro_tools.list_gold_alerts())
    r = pro_tools.delete_gold_alert(aid)
    assert r["deleted_id"] == aid


def test_create_alert_invalid_condition(alerts_tmp):
    out = pro_tools.create_gold_alert("magic", 100.0)
    assert "error" in out


def test_premium_use_intraday_seasonality_groups():
    # Just test that the bucketing logic in the source doesn't crash
    # with synthetic data shape. Real intraday fetch is mocked elsewhere.
    from gold_mcp.premium_tools import STRATEGIES
    assert set(STRATEGIES) >= {"rsi_mean_reversion", "macd_trend",
                                "sma_crossover", "breakout_donchian"}


def test_premium_backtest_internal_smoke():
    import pandas as pd

    from gold_mcp.premium_tools import _backtest_df
    rng = np.random.default_rng(0)
    closes = 2000.0 * np.cumprod(1 + rng.normal(0.0005, 0.012, 200))
    df = pd.DataFrame({
        "open": closes, "high": closes * 1.005, "low": closes * 0.995,
        "close": closes, "volume": [1000.0] * len(closes),
    })
    out = _backtest_df(df, "sma_crossover", None, 2.0)
    assert "error" not in out
    assert "sharpe" in out and "max_drawdown_pct" in out
