# gold-mcp

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-1.0.0-green.svg)](https://github.com/ThaiTrevor/gold-mcp/releases)
[![MCP](https://img.shields.io/badge/MCP-compatible-orange.svg)](https://modelcontextprotocol.io)
[![CI](https://github.com/ThaiTrevor/gold-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/ThaiTrevor/gold-mcp/actions/workflows/test.yml)

**Bloomberg-grade analytics for XAUUSD inside Claude, ChatGPT, Cursor, and
any other Model Context Protocol client.**

23 tools spanning live tick microstructure, OOS-validated strategy
intelligence, macro context, and an AI analyst aggregator layer.
Cross-platform, open-source core, hosted paid tier coming.

> **Why this exists.** Every LLM reasons well about gold, but none of
> them have live price, tick microstructure, an economic-calendar
> awareness, or an opinion on whether the current Asian-box state
> historically precedes a wider London/NY range. `gold-mcp` is a thin
> server that exposes well-typed tools so the model can pull the right
> numbers — and the right interpretation — on demand instead of
> guessing.

## Who is this for?

- **Retail XAUUSD traders** (MT4/MT5 on Exness, IC Markets, FXTM, FBS…)
  who already use Claude or ChatGPT for research and want the AI to
  actually see live market state.
- **Quant developers and researchers** building trading systems inside
  Cursor / Claude Code — wire in real microstructure data and 700+
  days of pre-computed strategy artifacts in one command.
- **Prop-firm traders** (FTMO, MFF, The5ers, FundedNext…) who need
  event-aware risk management and tight slippage control.
- **Content creators / analysts** in the gold space who want
  one-command daily briefings backed by real numbers.

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

### Proprietary data
- `get_macro_strength` — 8-currency event-driven macro coefficient
- `get_news_calendar` — gold-relevant upcoming + recent macro events

### Strategy intelligence (700+ days OOS-validated)
- `get_xau_daily_setup_config` — locked daily-setup scanner parameters
- `get_xau_asian_box_stats` — Asian-box state distribution + range-expansion correlations
- `get_xau_institutional_footprint` — historical footprint signature
- `get_xau_gamma_regime` — gamma-regime classification + behavior
- `get_xau_trend_entry_signature` — clean trend-entry pattern signature

### AI analyst (aggregators)
- `analyze_gold_setup` — one-call structured read combining 10+ underlying tools
- `daily_briefing` — sectioned morning briefing
- `risk_assessment` — risk read on a hypothetical XAUUSD position

### Regional bonus (Vietnam)
- `get_vn_macro` — USD/VND + cross rates + implied world-parity gold price in VND
- `estimate_vn_gold_premium` — compare a user-supplied local VN gold price to world parity

### Health
- `get_data_freshness` — is the underlying tick feed live, recent, stale?

## Why it stands out

| | gold-mcp | Bloomberg | TradingView | yfinance wrappers |
|---|---|---|---|---|
| Price | OSS free / paid tier | $24k/yr | $15–60/mo | $0 |
| Native AI integration | yes | no | limited | hand-rolled |
| Tick microstructure | yes | yes | limited | no |
| 700-day strategy artifacts | yes | no | no | no |
| Risk assessment AI | yes | no | no | no |
| Cross-vendor (Claude/ChatGPT/Cursor/…) | yes | n/a | n/a | n/a |

## Quickstart

### 1. Install

```bash
git clone https://github.com/<you>/gold-mcp.git
cd gold-mcp
pip install -e .
```

Python 3.10+.

### 2. Configure (optional)

Copy `.env.example` → `.env` and fill in the paths you have available.
Every variable is optional. Tools whose env var is unset return a
structured `{"error": "not_configured", "hint": "…"}` response so the
rest of the server keeps working on fresh clones.

Minimum useful setup is `GOLD_MCP_TICKS_DIR` plus `GOLD_MCP_L2_DIR`
for tick-derived tools; the public macro tools work standalone via
Yahoo Finance.

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
claude mcp add --scope user gold-mcp \
  -e GOLD_MCP_L2_DIR=/path/to/XAUUSD_L2 \
  -e GOLD_MCP_TICKS_DIR=/path/to/XAUUSD_L2/ticks \
  -e GOLD_MCP_MACRO_STRENGTH_FILE=/path/to/macro_strength.json \
  -e GOLD_MCP_NEWS_CALENDAR_FILE=/path/to/history.csv \
  -e GOLD_MCP_STRATEGY_RESULTS_DIR=/path/to/strategy/results \
  -- python -m gold_mcp.server
```

#### ChatGPT Desktop / Agent mode, Cursor, Windsurf, Cline, Zed

Same shape — point them at `python -m gold_mcp.server` with the env
vars above.

### 4. Try it

Ask the model in plain English:

> "Analyze the current gold setup and give me a daily briefing."
>
> "Gold is down 0.7% today. Is the macro tape (DXY, yields, VIX, macro
> strength) confirming or fighting this? Any high-impact USD events on
> the calendar in the next 48 hours?"
>
> "Walk me through the Asian-box state today and tell me what the
> historical follow-up has looked like under that state."
>
> "I want to go long XAUUSD at 4508 with stop at 4495, size $10,000.
> Run a risk assessment."

The model picks the right tools, calls them, and combines the answers.

## Architecture

```
gold_mcp/
  server.py            FastMCP tool wiring
  tick_data.py         Live + recent ticks (price, OHLCV, session)
  l2_data.py           L2 DOM top-of-book
  microstructure.py    Tick velocity, spread regime, session character
  macro_data.py        yfinance macro snapshot, correlations
  analytics.py         Seasonality
  analyst.py           AI-analyst aggregators
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
structured `not_configured` response so the rest of the server keeps
working on machines that don't have the underlying sources.

This lets you publish the server publicly while keeping the data
that gives it value private.

## Data notes (honest)

- **Tick archive** is the live foundation: ~100 trading days of MT5
  ticks (bid/ask/last/volume) feeds every microstructure tool.
- **L2 DOM** is supplementary: the broker DOM publishes 3–5 levels of
  aggregated liquidity, not interbank depth. We expose only the raw
  top-of-book snapshot and defer derived imbalance metrics until a
  deeper / cleaner feed is available.
- **Strategy results** are pre-computed JSON / CSV artifacts from an
  out-of-sample-validated research pipeline. The MCP wraps the
  artifacts — it doesn't rerun the backtest.
- **Macro / correlation / seasonality** come from Yahoo Finance.
- **Stream health** is reported by `get_data_freshness`. If your live
  stream is down, tick-derived tools operate on the latest archive
  and freshness reports `stale` / `very_stale` so the LLM knows.

## Roadmap

- **v1.1** — scraped local-market gold prices (SJC / DOJI / PNJ),
  broker-consensus integration
- **v1.2** — real-time alert webhooks, freshness pings
- **v2.0** — hosted HTTPS MCP + API key + tiered plans

## Tests

```bash
pip install -e ".[dev]"
pytest
```

## Contributing

PRs welcome. Open an issue first for non-trivial changes so we can
align on direction.

## License

MIT.
