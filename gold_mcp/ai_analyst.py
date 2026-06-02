"""AI Analyst chain — Ultra tier.

Optional BYOK Anthropic Claude integration that orchestrates multiple
gold-mcp tools, feeds results to Claude, and returns a structured
trading thesis. The user supplies ANTHROPIC_API_KEY in env.

No data flows to Anthropic that the user didn't authorize via their
own key. The server uses the user's key directly.
"""
from __future__ import annotations

import json
import os

try:
    from anthropic import Anthropic
    _HAS_ANTHROPIC = True
except ImportError:
    Anthropic = None  # type: ignore
    _HAS_ANTHROPIC = False


SYSTEM_PROMPT = """You are an experienced gold (XAUUSD) market analyst writing
for a sophisticated trader audience. You receive a structured snapshot of
the current gold market and produce a concise, evidence-based read.

Rules:
- Be direct. State the bias and the key levels.
- Cite the specific numbers from the snapshot (not vague language).
- Acknowledge uncertainty and conflicting signals explicitly.
- Never make explicit "buy" / "sell" recommendations. Frame as scenarios
  with conditions: "If price reclaims X with momentum, watch Y."
- Always end with: 1 invalidation level, 1 confirmation trigger.
- Maximum 250 words.

Output a JSON object with these fields:
  bias: "bullish" | "bearish" | "neutral"
  conviction: 1-5 (5 = highest)
  key_levels: { support: float, resistance: float, pivot: float }
  read: string (the 250-word analysis)
  invalidation: string (1 sentence)
  confirmation_trigger: string (1 sentence)
"""


def _build_snapshot(symbol: str = "XAUUSD") -> dict:
    """Pull all relevant gold-mcp data into a single structured snapshot."""
    from . import analyst, analytics, gold_data, macro_data, mtf, regime, smart_money
    from .adapters import vn_macro as vn_macro_adapter

    snapshot = {}
    try:
        snapshot["price"] = gold_data.get_gold_price()
        snapshot["bars_h1"] = gold_data.get_gold_ohlcv(timeframe="1h", lookback=120)
        snapshot["macro"] = macro_data.get_macro_context()
        snapshot["correlations"] = macro_data.get_correlation_matrix(lookback_days=60)
        snapshot["seasonality_dow"] = analytics.get_seasonality(group_by="dow")
        snapshot["vn_parity"] = vn_macro_adapter.get_vn_macro()
        snapshot["snapshot"] = analyst.gold_market_snapshot()

        bars = snapshot["bars_h1"].get("bars", [])
        if bars:
            snapshot["smc"] = smart_money.smc_full_scan(bars)
            closes = [b["close"] for b in bars]
            snapshot["regime"] = regime.classify_regime(closes)

        snapshot["mtf"] = mtf.mtf_alignment()
    except Exception as e:
        snapshot["partial_error"] = str(e)
    return snapshot


def ai_daily_briefing(model: str = "claude-sonnet-4-6",
                      max_tokens: int = 1500) -> dict:
    """Generate a structured AI-driven daily briefing.

    Requires ANTHROPIC_API_KEY in env. Pulls a full snapshot of current
    gold conditions and asks Claude for a JSON-structured read.
    """
    if not _HAS_ANTHROPIC:
        return {"error": "anthropic_sdk_not_installed",
                "install": "pip install 'gold-mcp[ai]' or 'pip install anthropic'"}
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return {"error": "ANTHROPIC_API_KEY not set",
                "get_key": "https://console.anthropic.com/"}

    snapshot = _build_snapshot()
    client = Anthropic(api_key=api_key)
    try:
        msg = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": (
                    "Here is the current gold market snapshot. Produce the "
                    "structured analyst read described in your instructions.\n\n"
                    f"```json\n{json.dumps(snapshot, default=str, indent=2)[:18000]}\n```"
                ),
            }],
        )
    except Exception as e:
        return {"error": "claude_api_failed", "detail": str(e)}

    text = msg.content[0].text if msg.content else ""
    parsed = None
    try:
        # Try to extract JSON from response
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            parsed = json.loads(text[start: end + 1])
    except json.JSONDecodeError:
        parsed = None

    return {
        "model": model,
        "input_tokens": msg.usage.input_tokens,
        "output_tokens": msg.usage.output_tokens,
        "structured": parsed,
        "raw_text": text if parsed is None else None,
        "snapshot_keys": list(snapshot.keys()),
    }


def ai_setup_explanation(timeframe: str = "1h",
                         model: str = "claude-haiku-4-5-20251001",
                         max_tokens: int = 800) -> dict:
    """Cheaper, faster version: explain the current setup in plain language.

    Uses Haiku for cost efficiency. Returns prose + level summary, no JSON.
    """
    if not _HAS_ANTHROPIC:
        return {"error": "anthropic_sdk_not_installed"}
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return {"error": "ANTHROPIC_API_KEY not set"}

    from . import gold_data, smart_money
    bars_resp = gold_data.get_gold_ohlcv(timeframe=timeframe, lookback=100)
    if "error" in bars_resp:
        return bars_resp
    smc = smart_money.smc_full_scan(bars_resp["bars"])

    client = Anthropic(api_key=api_key)
    try:
        msg = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{
                "role": "user",
                "content": (
                    f"You are a gold market technician. The {timeframe} chart "
                    "SMC analysis is below. Explain the setup in plain English "
                    "for a sophisticated trader. 5 sentences max. No 'buy/sell' "
                    "language, only scenarios.\n\n"
                    f"```json\n{json.dumps(smc, default=str, indent=2)[:8000]}\n```"
                ),
            }],
        )
    except Exception as e:
        return {"error": "claude_api_failed", "detail": str(e)}

    return {
        "model": model,
        "timeframe": timeframe,
        "input_tokens": msg.usage.input_tokens,
        "output_tokens": msg.usage.output_tokens,
        "explanation": msg.content[0].text if msg.content else "",
        "smc_bias": smc.get("composite_bias"),
        "smc_bias_score": smc.get("composite_bias_score"),
    }
