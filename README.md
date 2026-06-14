# gold-mcp

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-4.1.1-green.svg)](https://github.com/ThaiTrevor/gold-mcp/releases)
[![MCP](https://img.shields.io/badge/MCP-compatible-orange.svg)](https://modelcontextprotocol.io)
[![CI](https://github.com/ThaiTrevor/gold-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/ThaiTrevor/gold-mcp/actions/workflows/test.yml)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/ThaiTrevor/gold-mcp/blob/main/CONTRIBUTING.md)

**An MCP server that brings public gold (XAUUSD) market data into
Claude, ChatGPT, Cursor, Windsurf, Cline, Zed, and any other Model
Context Protocol client.**

Free tier (13 tools + optional 8-tool MT5 BYOK adapter) is fully
functional and stays free forever. Pro, Premium, and Ultra tiers add
advanced TA, backtest, SMC suite, risk management, and AI analyst via
an offline Ed25519 license key — no SaaS, no phone-home.

> **Educational and research use only — not financial advice.**

## Tiers

| Tier | Tools | License | Suggested price |
|---|---|---|---|
| **Free** | 13 (+8 optional MT5 BYOK) | None | $0 |
| **Pro** | +7 (20 total) | `GOLD_MCP_LICENSE_KEY` env | $9-19/mo |
| **Premium** | +4 (24 total) | `GOLD_MCP_LICENSE_KEY` env | $29-49/mo |
| **Ultra** | +18 (42 total, 50 with MT5 BYOK) | `GOLD_MCP_LICENSE_KEY` env | $99-149/mo |

### Free — public gold data + realtime PAXG + MT5 BYOK (13 + 8 tools)

**Public gold data (Yahoo Finance):**
- `get_gold_price` — latest gold close + 24h change
- `get_gold_ohlcv` — historical bars (1m → 1mo)
- `get_macro_context` — DXY, US10Y/02Y, SPX, VIX, BTC, silver, oil
- `get_gold_correlations` — gold-vs-macro correlation matrix
- `get_gold_seasonality` — day-of-week / monthly return stats
- `get_vn_macro` — USD/VND + implied world-parity gold price in VND
- `estimate_vn_gold_premium` — compare local VN quote to world parity
- `gold_market_snapshot` — one-call aggregator + bulleted summary
- `diagnostic` — show license tier + available tools
- `cache_purge` — sweep expired cache entries

**Realtime PAXG via Binance public WebSocket (NEW v4.1, no API key):**
- `paxg_worker_status` — WS worker health + tick count
- `get_paxg_tick` — last PAXG tick (tracks XAU/USD within 0.1-0.3%)
- `get_paxg_ohlcv_realtime` — aggregated PAXG bars from local tick log

**MT5 BYOK adapter (NEW v4.1, optional via `pip install 'gold-mcp[mt5]'`, Windows):**
- `mt5_attach` / `mt5_detach` / `mt5_status` — manage attached terminal
- `mt5_find_symbol` — broker-specific XAUUSD symbol resolution
- `mt5_get_tick` / `mt5_get_ohlcv` / `mt5_get_ticks` — read from your terminal
- `mt5_account_info` — balance / equity / leverage
- *No credentials cross the server. You run your own MT5 terminal.*

### Pro — advanced TA + multi-timeframe + alerts
- `analyze_gold_advanced` — Bollinger + Ichimoku + Fibonacci
- `multi_timeframe_snapshot` — 5m / 1h / 4h / 1d in one call
- `gold_correlation_regime` — detects DXY decoupling, etc.
- `get_gold_setups` — multi-indicator confluence scanner
- `create_gold_alert` / `list_gold_alerts` / `delete_gold_alert`

### Premium — backtest + research
- `backtest_gold_strategy` — 4 strategies, vectorized
- `gold_walk_forward` — rolling out-of-sample validation
- `optimize_gold_strategy` — grid search by Sharpe / PF / return
- `gold_intraday_seasonality` — hourly / session bucketing

### Ultra — institutional analyst toolkit (18 exclusive tools)

**Smart Money Concepts (SMC)**
- `smc_full_scan` — composite SMC bias (structure + OB + FVG + sweeps)
- `detect_order_blocks` — bullish/bearish OB with impulse ATR filtering
- `detect_fair_value_gaps` — 3-candle imbalances + fill tracking
- `detect_liquidity_sweeps` — stop-hunt detection (breach + reverse)
- `detect_market_structure` — CHOCH/BOS labeling on swing fractals

**Regime + Multi-Timeframe**
- `classify_regime` — composite Hurst exponent + Lo-MacKinlay variance ratio
- `mtf_alignment` — D1/H4/H1 confluence with alignment score 0-100

**Position sizing + risk**
- `kelly_fraction` — half-Kelly default for safety
- `fixed_fractional_size` — classic R% sizing
- `optimal_f` — Ralph Vince geometric-mean-maximizing f
- `risk_of_ruin` — Monte Carlo ruin probability

**Monte Carlo + VaR**
- `monte_carlo_paths` — bootstrap or parametric path simulation
- `value_at_risk` — historical VaR + Conditional VaR
- `prob_hit_target_or_stop` — MC trade probability with EV in R-multiples

**AI Analyst (BYOK Anthropic)**
- `ai_daily_briefing` — structured JSON read from Claude Sonnet 4.6
- `ai_setup_explanation` — cheaper Haiku 4.5 plain-English read

**Report generation**
- `generate_html_tearsheet` — polished standalone HTML report
- `generate_markdown_briefing` — portable Markdown daily summary

## Quickstart

### 1. Install

```bash
git clone https://github.com/ThaiTrevor/gold-mcp.git
cd gold-mcp
pip install -e .
```

Python 3.10+. No other setup, no env vars, no data files.

### 2. Wire it into your MCP client

#### Claude Desktop

Edit `%APPDATA%\Claude\claude_desktop_config.json` (Windows) or
`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "gold-mcp": {
      "command": "python",
      "args": ["-m", "gold_mcp.server"]
    }
  }
}
```

Restart Claude Desktop. The tools appear under the plug icon.

#### Claude Code (CLI)

```bash
claude mcp add --scope user gold-mcp -- python -m gold_mcp.server
```

#### Cursor / Windsurf / Cline / Continue / Zed

`~/.cursor/mcp.json` (or the equivalent file for your client):

```json
{
  "mcpServers": {
    "gold-mcp": {
      "command": "python",
      "args": ["-m", "gold_mcp.server"]
    }
  }
}
```

#### ChatGPT Desktop / Agent mode

Settings → Connectors → Add MCP server:

```
Command: python
Args:    -m gold_mcp.server
```

### 3. Try it

Ask the model in plain English. Examples:

> "What is gold doing right now and how does it compare to today's
> macro tape (DXY, yields, VIX)?"

> "Show me the last 24 hourly bars of gold and the 60-day correlation
> with silver and DXY."

> "Give me a market snapshot for gold — combine price, macro context,
> correlations, and the day-of-week seasonality."

> "USD/VND right now and the implied world-parity gold price in VND
> per tael. If SJC is quoting 145 million, what's the premium?"

## Why this exists

LLMs reason well about gold but they don't see live market data, the
macro tape that moves gold, or a clean correlation matrix on demand.
This server is a tiny, free bridge between an MCP client and the
public Yahoo Finance data that any researcher already has access to —
exposed as well-typed tools so the model picks the right one
automatically.

It started as a study project to learn MCP architecture and turned
into something useful enough to publish for the community.

## Upgrading to Pro / Premium

Add `GOLD_MCP_LICENSE_KEY` to the env block of your MCP config:

```json
"env": {
  "GOLD_MCP_LICENSE_KEY": "eyJ0aWVy...Ijoi.MEUCI..."
}
```

Restart your MCP client. Call `diagnostic` — `tier_active` should
report `pro` or `premium`. New tools become available immediately.

See [examples/claude_desktop_config_pro.json](examples/claude_desktop_config_pro.json)
for the full template.

## Architecture

```
gold_mcp/
  server.py            FastMCP wiring with 3-tier gating (21 tools max)
  gold_data.py         yfinance price + OHLCV
  macro_data.py        DXY/yields/SPX/VIX/BTC + correlations
  analytics.py         seasonality
  analyst.py           one-call aggregator (gold_market_snapshot)
  cache.py             TTL filesystem cache (60s → 24h)
  license.py           Ed25519 offline license verification
  issue_license.py     CLI: init-keys, issue, verify
  pro_tools.py         Pro tier: advanced TA, alerts, multi-timeframe
  premium_tools.py     Premium tier: backtest, walk-forward, optimizer
  adapters/
    vn_macro.py        USD/VND + world-parity gold
```

For vendors selling licenses, see the CLI:

```bash
python -m gold_mcp.issue_license init-keys
# Paste printed PUBLIC_KEY_B64 into gold_mcp/license.py

python -m gold_mcp.issue_license issue --tier pro --email u@x.com --days 30
```

Or run the Lemon Squeezy webhook handler (port from
[mcp-byok-template](https://github.com/YOUR_GH/mcp-byok-template) —
swap the env-var name from `MCP_BYOK_LICENSE_KEY` to `GOLD_MCP_LICENSE_KEY`).

## Contributing

This project is small on purpose. We welcome contributions that fit
the same pattern:

- Small, focused tools that wrap one public data source
- Return structured JSON with named keys + a short interpretation field
- No private data, no scraped credentials, no broker-specific paths
- No tools that produce trading recommendations

See [CONTRIBUTING.md](CONTRIBUTING.md) for details and
[SECURITY.md](SECURITY.md) for how to report security issues.

## Testing

```bash
pip install -e ".[dev]"
pytest
```

CI runs the suite on Linux, macOS, and Windows across Python
3.10/3.11/3.12 on every push and pull request.

## Disclaimer

`gold-mcp` is a data and analysis tool for educational and research
purposes only. Nothing returned by any tool constitutes investment
advice, a recommendation, or a solicitation. Markets carry risk; you
are responsible for your own decisions.

## License

MIT — see [LICENSE](LICENSE).
