# Outreach playbook for gold-mcp launch

Copy-paste-ready content for each channel. Personalize the first line
where noted. Order matters — fire awesome-mcp first (sets a discovery
beachhead), then Hacker News (peak window 13:00-15:00 UTC, weekday),
then Reddit, then X. Spread across 24 hours, not all at once.

> **Note:** This file is in the repo for your reference only — feel
> free to gitignore or delete after the launch week.

---

## 1. awesome-mcp-servers PR

Repo: https://github.com/punkpeye/awesome-mcp-servers

### Fork + branch

```bash
gh repo fork punkpeye/awesome-mcp-servers --clone
cd awesome-mcp-servers
git checkout -b add-gold-mcp
```

### Edit README.md

Find the "Finance & Fintech" section (or similar). Add a line, keeping
alphabetical order:

```markdown
- [gold-mcp](https://github.com/ThaiTrevor/gold-mcp) - XAUUSD live tick microstructure, OOS-validated strategy intelligence (700+ days), macro context, and an AI analyst aggregator. Cross-platform.
```

### Open PR

```bash
git add README.md
git commit -m "Add gold-mcp to Finance & Fintech"
git push origin add-gold-mcp
gh pr create \
  --title "Add gold-mcp to Finance & Fintech" \
  --body "$(cat <<'BODY'
[gold-mcp](https://github.com/ThaiTrevor/gold-mcp) — MCP server exposing XAUUSD (gold) tick microstructure, macro context, and 700+ days of OOS-validated strategy intelligence to Claude, ChatGPT, Cursor, and any other MCP client.

- 23 tools across 4 layers (foundation, macro, strategy intelligence, AI analyst)
- Env-var-driven adapter architecture keeps user-private data paths out of the public source
- Cross-platform: works with Claude Desktop, Claude Code, ChatGPT Desktop, Cursor, Windsurf, Cline, Zed
- MIT licensed
- Tests on Linux/macOS/Windows x Python 3.10/3.11/3.12

Landing page: https://pthaicapital.io.vn/mcp
BODY
)"
```

---

## 2. Hacker News (Show HN)

URL: https://news.ycombinator.com/submit
Best window: weekday 13:00-15:00 UTC (early US morning)

**Title** (80-char limit; HN strips emoji):
```
Show HN: Gold-mcp – XAUUSD analytics for Claude, ChatGPT and Cursor
```

**URL field**: `https://github.com/ThaiTrevor/gold-mcp`

**Text field** (optional but recommended):
```
Hi HN — I built an MCP server that gives Claude, ChatGPT, Cursor and similar AI clients real-time XAUUSD (gold) microstructure plus 700+ days of OOS-validated strategy artifacts.

It exposes 23 tools across four layers:
- Foundation: tick velocity, spread regime vs 24h distribution, session microstructure, L2 top-of-book
- Macro: DXY/yields/SPX/VIX/BTC snapshot, gold-vs-macro correlation matrix, an 8-currency event-driven macro-strength engine, and an economic-calendar tool filtered to gold-relevant currencies
- Strategy intelligence: Asian-box state classifier (EXPANDED state → 1.2x London/NY range on 709 days), gamma-regime classifier, institutional-footprint signature, clean trend-entry signature, OOS-locked daily-setup scanner parameters
- AI analyst: aggregator tools that fan out to 10+ underlying calls and return a single structured read (analyze_gold_setup, daily_briefing, risk_assessment)

The interesting part architecturally is the private-data separation. Tools that depend on user-private data read paths from env vars only — no hard-coded paths in the source — and degrade gracefully to a structured `{"error": "not_configured", "hint": "..."}` response when an env var is missing. This lets the repo be public while the data sources that give it value stay private.

Stack: Python 3.10+, FastMCP, pandas, pyarrow, yfinance. MIT licensed. CI on Linux/macOS/Windows x three Python versions.

Happy to answer questions about MCP, the adapter architecture, or why I dropped derived L2 imbalance metrics after auditing the broker DOM asymmetry (short answer: the broker's quote stack is structurally lopsided, so any naive imbalance metric reads as constant sell pressure).
```

---

## 3. Reddit

### r/ClaudeAI

**Title**:
```
Built an MCP server for gold (XAUUSD) trading — 23 tools, works in Claude Desktop / Claude Code
```

**Body**:
```
After noticing Claude reasons well about markets but has no live data, I built gold-mcp — an MCP server exposing XAUUSD tick microstructure, macro context, and 700+ days of strategy artifacts. 23 tools total.

The aggregator layer is the most interesting in practice: `analyze_gold_setup` fans out to 10+ underlying tools (price, spread regime, tick velocity, macro snapshot, macro-strength engine, news calendar, Asian-box state) and returns one structured read with a top-line bulleted summary. So instead of asking 10 separate questions, you ask "what's gold doing" and get the model's combined opinion grounded in real data.

Open-source, MIT, env-var-driven so your data paths never end up in the public repo.

GitHub: https://github.com/ThaiTrevor/gold-mcp
Landing: https://pthaicapital.io.vn/mcp

Curious if anyone here has built similar finance MCPs — looking for prior art before I build the news-sentiment layer next.
```

### r/algotrading

**Title**:
```
Open-sourced an MCP server for XAUUSD: tick microstructure + Asian-box / gamma-regime analytics inside Claude
```

**Body**:
```
Quant-flavored MCP server I've been using personally and decided to open-source.

What's in it:
- Tick-derived microstructure: ticks/sec velocity, spread regime vs trailing 24h distribution, session character by Asia/EU/US
- 700+ days of OOS-validated strategy artifacts: Asian-box state classifier (TIGHT / NORMAL / EXPANDED), gamma-regime classifier, institutional-footprint signature, clean trend-entry signature
- Aggregator that combines all of the above into one structured read with a top-line bulleted summary

Example insight surfaced by the Asian-box tool: across 709 days, after an EXPANDED Asian-session box the London/NY range averaged 1.2x larger than after a TIGHT box. That's the kind of empirical context the model gets when you ask it about today's setup.

GitHub: https://github.com/ThaiTrevor/gold-mcp

MIT, Python 3.10+, FastMCP. The tick stream feeds in from MT5 (IC Markets) but you can point it at any tick archive that follows the same parquet schema — see the data notes in the README.

Anyone running similar setups? Curious about your approach to the broker-DOM asymmetry problem — I ended up dropping derived L2 imbalance metrics after auditing that the broker stack is structurally lopsided in a way that biases any naive imbalance reading.
```

### r/LocalLLaMA

**Title**:
```
Gold-mcp — first serious MCP server for XAUUSD trading data (works with Claude, ChatGPT, Cursor)
```

**Body** (shorter, this audience already knows MCP):
```
Built an MCP server that gives any MCP client (Claude Desktop, ChatGPT Desktop, Cursor, Windsurf, Cline, Zed…) real-time XAUUSD microstructure plus 700-day backtest artifacts. 23 tools.

The architecture that I think is worth a look: env-var-driven private-data adapters. Public source contains zero absolute paths or proprietary URLs. Tools whose env var is unset return `{"error": "not_configured", "hint": "..."}` so the server still works on a fresh clone for the tools you do have data for.

GitHub: https://github.com/ThaiTrevor/gold-mcp
MIT. Python 3.10+.
```

---

## 4. X / Twitter

Thread, fire one tweet per line, ~30 sec apart:

```
1/ Just open-sourced gold-mcp — an MCP server that gives Claude, ChatGPT, Cursor and other AI clients real-time XAUUSD (gold) microstructure plus 700+ days of OOS-validated strategy intelligence.

23 tools, 4 layers. 🧵
```

```
2/ Foundation layer: tick velocity, spread regime vs 24h distribution, session microstructure by Asia / EU / US, L2 top-of-book.

The kind of data retail traders rarely see surfaced as plain MCP tool calls.
```

```
3/ Strategy layer: 709 days of analysis baked into tools.

After an EXPANDED Asian-session box, London/NY range averages 1.2x larger than after a TIGHT box.

The model gets this empirical context every time it reasons about today's setup.
```

```
4/ AI analyst layer is where it earns its keep.

analyze_gold_setup, daily_briefing, risk_assessment — aggregator tools that fan out to 10+ underlying calls and return ONE structured read with a top-line bulleted summary.

Ask "what's gold doing" → get the combined opinion.
```

```
5/ Architecturally the bit I'm most happy with: env-var-driven adapters keep user-private file paths out of the public source. Tools whose env var is unset return a structured not_configured response.

Public repo is publishable. Data stays yours.
```

```
6/ MIT licensed, Python 3.10+, cross-vendor MCP. Tests on Linux/macOS/Windows × py3.10/3.11/3.12.

GitHub: github.com/ThaiTrevor/gold-mcp
Landing: pthaicapital.io.vn/mcp

@AnthropicAI @cursor_ai @windsurf_ai
```

---

## Timing schedule (24h window)

| Time (UTC) | Channel | Why this slot |
|---|---|---|
| 13:00 | **HN Show HN** | Peak US morning, EU lunch, AU evening |
| 13:30 | **awesome-mcp PR** | First listing while HN is climbing |
| 14:00 | **X thread** | Catch HN-driven attention |
| 17:00 | **r/algotrading** | EU evening, US afternoon (active hours) |
| 20:00 | **r/ClaudeAI** | US evening (active) |
| 02:00 next day | **r/LocalLLaMA** | EU morning + India (active) |

Don't post all on the same day on Reddit — get flagged as spam.

## Post-launch monitoring

Set up these to track signal:

- **GitHub Insights → Traffic**: clones, unique visitors, referrers
- **HN ranking**: refresh https://news.ycombinator.com/show every few hours
- **Reddit thread comments**: engage in first 2-3 hours (boosts ranking)
- **X notifications**: reply to first 5 comments, helps the algorithm

## What good looks like (first week targets)

- 50-200 GitHub stars (HN hit → 200-500 is possible)
- 5-20 issues / PRs from real users
- 1-2 contributors with merged PRs
- 50-200 landing page visits / day
- 20-100 waitlist subscribers (when you wire the form)
