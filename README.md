# gold-mcp

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-2.0.0-green.svg)](https://github.com/ThaiTrevor/gold-mcp/releases)
[![MCP](https://img.shields.io/badge/MCP-compatible-orange.svg)](https://modelcontextprotocol.io)
[![CI](https://github.com/ThaiTrevor/gold-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/ThaiTrevor/gold-mcp/actions/workflows/test.yml)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/ThaiTrevor/gold-mcp/blob/main/CONTRIBUTING.md)

**A small, free, community-driven MCP server that brings public gold
(XAUUSD) market data into Claude, ChatGPT, Cursor, Windsurf, Cline,
Zed, and any other Model Context Protocol client.**

No broker account. No tick stream. No environment variables. No paid
tier. Just clone, `pip install -e .`, wire to your MCP client, and ask
your AI assistant about gold.

> **Educational and research use only — not financial advice.**

## What it does

Eight small tools that wrap Yahoo Finance so the model can pull live
numbers about gold and the macro context that drives it.

- `get_gold_price` — latest gold close + 24h change
- `get_gold_ohlcv` — historical bars (1m → 1mo)
- `get_macro_context` — DXY, US10Y/02Y, SPX, VIX, BTC, silver, oil
- `get_gold_correlations` — gold-vs-macro correlation matrix
- `get_gold_seasonality` — day-of-week / monthly return stats
- `get_vn_macro` — USD/VND + implied world-parity gold price in VND
- `estimate_vn_gold_premium` — compare a local VN gold quote against
  world parity
- `gold_market_snapshot` — one-call structured aggregator over the
  tools above, with a concise bulleted summary

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

## Architecture

```
gold_mcp/
  server.py        FastMCP tool wiring (8 tools)
  gold_data.py     yfinance price + OHLCV
  macro_data.py    DXY/yields/SPX/VIX/BTC + correlations
  analytics.py     seasonality
  analyst.py       one-call aggregator (gold_market_snapshot)
  adapters/
    vn_macro.py    USD/VND + world-parity gold (community contribution)
```

Every module is small and self-contained — read through it in 15
minutes. PRs that add similar small tools are very welcome.

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
