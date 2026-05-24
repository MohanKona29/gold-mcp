# gold-mcp

MCP server exposing **XAUUSD (gold)** microstructure, macro context, and
proprietary strategy intelligence to Claude, ChatGPT, Cursor, Windsurf,
and any other Model Context Protocol client.

> **Why this exists.** LLMs reason well about gold, but they have no
> live price, no tick history, no economic-calendar awareness, and no
> opinion on whether the current Asian-box state historically precedes
> a wider London/NY range. `gold-mcp` is a thin server that exposes
> well-typed tools so the model can pull the right numbers on demand
> instead of guessing.

## What's inside (23 tools, 4 layers)

### Foundation — live price + microstructure
- `get_gold_price` — latest bid / ask / mid / spread
- `get_gold_ohlcv` — OHLCV bars (1m / 5m / 15m / 30m / 1h / 4h / 1d)
- `get_gold_session_summary` — today's open / high / low / range / % change
- `get_gold_tick_velocity` — ticks/sec, news-burst detector
- `get_gold_spread_stats` — current spread vs. its 24h distribution
- `get_gold_session_microstructure` — Asia vs. Europe vs. US character
- `get_gold_top_of_book` — best bid / ask from the L2 DOM

### Public macro
- `get_macro_context` — DXY, US10Y/02Y, SPX, VIX, BTC, silver, oil
- `get_gold_correlations` — gold-vs-macro correlation matrix
- `get_gold_seasonality` — day-of-week / monthly return stats

### Layer 1 — Proprietary data
- `get_macro_strength` — 8-currency event-driven macro coefficient
- `get_news_calendar` — gold-relevant upcoming + recent macro events
- `get_vn_macro` — USD/VND + cross rates + implied world-parity gold price (VND)
- `estimate_vn_gold_premium` — compare a user-supplied local VN gold price to world parity

### Layer 2 — Strategy intelligence
- `get_xau_daily_setup_config` — OOS-locked daily-setup scanner parameters
- `get_xau_asian_box_stats` — Asian-box state distribution + range-expansion correlations
- `get_xau_institutional_footprint` — historical footprint signature
- `get_xau_gamma_regime` — gamma-regime classification + behavior
- `get_xau_trend_entry_signature` — clean trend-entry pattern signature

### Layer 3 — AI analyst (aggregators)
- `analyze_gold_setup` — one-call structured read combining 10+ underlying tools
- `daily_briefing` — sectioned morning briefing
- `risk_assessment` — risk read on a hypothetical XAUUSD position

### Health
- `get_data_freshness` — is the underlying tick feed live, recent, stale?

## Architecture

```
gold_mcp/
  server.py            FastMCP tool wiring
  tick_data.py         Live + recent ticks (price, OHLCV, session)
  l2_data.py           L2 DOM top-of-book
  microstructure.py    Tick velocity, spread regime, session character
  macro_data.py        yfinance macro snapshot, correlations
  analytics.py         Seasonality
  analyst.py           Layer 3 aggregators
  adapters/            Private-data adapters (env-var driven)
    _paths.py          Resolves file locations from env vars only
    macro_strength.py
    news_calendar.py
    strategy.py        Strategy engine result artifacts
    vn_macro.py        Vietnam-specific macro context
```

### Private-data separation

Every tool that depends on user-private data (precomputed macro
engine output, news archive, strategy engine results) reads file
paths from environment variables. **No absolute paths are hard-coded
in the public source.** Tools whose env var is unset return a
structured `{"error": "not_configured", "hint": "Set ..."}` response
so the rest of the server keeps working on machines that don't have
the underlying sources.

This lets you push the public repo without leaking where any of your
proprietary data lives.

## Quickstart

### 1. Install

```bash
git clone https://github.com/<you>/gold-mcp.git
cd gold-mcp
pip install -e .
```

Python 3.10+.

### 2. Configure (optional but recommended)

Copy `.env.example` → `.env` and fill in the paths you have available.
Every variable is optional. Minimum useful setup is `GOLD_MCP_TICKS_DIR`
plus `GOLD_MCP_L2_DIR` for tick-derived tools; the public macro tools
work standalone via Yahoo Finance.

### 3. Wire it into your MCP client

#### Claude Desktop

`%APPDATA%\Claude\claude_desktop_config.json` (Windows) or
`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "gold-mcp": {
      "command": "python",
      "args": ["-m", "gold_mcp.server"],
      "env": {
        "GOLD_MCP_L2_DIR": "/path/to/XAUUSD_L2",
        "GOLD_MCP_TICKS_DIR": "/path/to/XAUUSD_L2/ticks",
        "GOLD_MCP_MACRO_STRENGTH_FILE": "/path/to/macro_strength.json",
        "GOLD_MCP_NEWS_CALENDAR_FILE": "/path/to/history.csv",
        "GOLD_MCP_STRATEGY_RESULTS_DIR": "/path/to/strategy/results"
      }
    }
  }
}
```

#### Claude Code CLI

```bash
claude mcp add gold-mcp \
  -e GOLD_MCP_L2_DIR=/path/to/XAUUSD_L2 \
  -e GOLD_MCP_TICKS_DIR=/path/to/XAUUSD_L2/ticks \
  -e GOLD_MCP_MACRO_STRENGTH_FILE=/path/to/macro_strength.json \
  -e GOLD_MCP_NEWS_CALENDAR_FILE=/path/to/history.csv \
  -e GOLD_MCP_STRATEGY_RESULTS_DIR=/path/to/strategy/results \
  -- python -m gold_mcp.server
```

#### ChatGPT Desktop / Agent mode, Cursor, Windsurf, Cline, Zed

Same shape — point them at `python -m gold_mcp.server` with the env vars above.

### 4. Try it

Ask the model in plain English:

> "Analyze the current gold setup and give me a daily briefing."
>
> "Gold is down 0.7% today. Is the macro tape (DXY, yields, VIX,
> macro strength) confirming or fighting this? Any high-impact USD
> events on the calendar in the next 48 hours?"
>
> "Walk me through the Asian-box state today and tell me what the
> historical follow-up has looked like under that state."
>
> "I want to go long XAUUSD at 4508 with stop at 4495, size $10,000.
> Run a risk assessment."
>
> "VN SJC tael is quoting 145M. Compute the premium vs world parity."

The model picks the right tools, calls them, and combines the answers.

## Data notes (honest)

- **Tick archive** is the live foundation: ~100 trading days of MT5
  ticks (bid/ask/last/volume) feeds every microstructure tool.
- **L2 DOM** is supplementary: the broker DOM publishes 3-5 levels of
  aggregated liquidity, not interbank depth. We expose only the raw
  top-of-book snapshot and defer derived imbalance metrics until a
  deeper / cleaner feed is available.
- **Strategy results** are pre-computed JSON/CSV artifacts from an
  out-of-sample-validated research pipeline. The MCP wraps the
  artifacts — it doesn't rerun the backtest.
- **Macro / correlation / seasonality** come from Yahoo Finance.
- **VN gold premium**: the live SJC/DOJI/PNJ scrape is deferred (those
  endpoints are behind anti-bot protection). For now the tool returns
  the world-parity anchor and accepts a user-supplied local price.
- **Stream health** is reported by `get_data_freshness`. If your live
  stream is down, the tick-derived tools operate on the latest archive
  and freshness reports `stale` / `very_stale`.

## Roadmap

- v1.1: scraped VN local gold prices, broker consensus integration
- v1.2: real-time alert webhooks, freshness pings
- v2.0: hosted HTTPS MCP + API key + tiered plans

## Running tests

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT.
