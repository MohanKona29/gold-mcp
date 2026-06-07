# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [4.1.1] - 2026-06-08

Ships the production license public key. 4.1.0 inadvertently shipped a DEV
placeholder pubkey — licenses signed with the operator's production key
could not be verified by customer installs. No code/feature changes; this
release exists solely to unblock license activation. **Yank 4.1.0
recommended.**

### Fixed

- `license.py` now embeds the production Ed25519 public key matching the
  private key used to issue licenses via `python -m gold_mcp.issue_license`.
  Previously embedded a dev placeholder with no matching private key in
  circulation, breaking activation for every paid tier.

## [4.1.0] - 2026-06-06

Adds **realtime gold tick data** (free) and **MT5 BYOK adapter** (free) — no
private credentials cross the server, everything is BYOK or public-WS. 11
new tools, total 50 at Ultra. PyPI publication.

### Added

- **`realtime.py`** — Binance public WebSocket worker captures PAXG (Paxos
  Gold ERC-20, tracks XAU/USD within ~0.1-0.3%) ticks into a local SQLite
  file. Tools: `paxg_worker_status`, `get_paxg_tick`,
  `get_paxg_ohlcv_realtime` (build N-second OHLCV bars on the fly). Free.
- **`brokers/mt5.py`** — BYOK MetaTrader 5 adapter. The user runs their
  own MT5 terminal locally; gold-mcp attaches by path. No credentials
  pass through the server, no broker data is redistributed. Tools:
  `mt5_attach`, `mt5_detach`, `mt5_status`, `mt5_find_symbol` (broker-
  agnostic XAUUSD resolution), `mt5_get_tick`, `mt5_get_ohlcv`,
  `mt5_get_ticks`, `mt5_account_info`. Free, Windows-only, requires
  `pip install gold-mcp[mt5]`.
- **`websocket-client`** added to base dependencies (realtime worker).
- **`MetaTrader5`** added as optional extra `[mt5]` (Windows-only marker).
- **PyPI distribution**: `pip install gold-mcp`, optional extras
  `[ai]`, `[mt5]`, `[webhook]`, `[dev]`.
- **Classifiers + Repository URL** added to pyproject.toml metadata.

### Fixed

- License test infrastructure (`tests/conftest.py`) patches `PUBLIC_KEY_B64`
  to dev keypair during test session — previous test failures were due to
  v4.0 shipping the prod public key for runtime, which dev-signed test
  licenses couldn't verify.
- Test registration sets now include conditional MT5 tools (skipped when
  MetaTrader5 not importable, e.g. Linux CI).
- `gold_mcp/__init__.py` version string was stale (`0.1.0`), now matches
  pyproject (`4.1.0`).

## [4.0.0] - 2026-05-30

Adds the **Ultra** tier — the institutional analyst toolkit. 18 new
tools spanning Smart Money Concepts, regime classification, MTF
confluence, position-sizing math, Monte Carlo risk simulation, BYOK
Claude API analyst chain, and HTML/Markdown report generation.
Suggested price $99-149/mo. Free/Pro/Premium tiers unchanged.

### Added

- **`Tier.ULTRA`** enum value + license issuance support.
- **`smart_money.py`** — SMC suite: `detect_market_structure` (CHOCH/BOS),
  `detect_order_blocks`, `detect_fair_value_gaps`,
  `detect_liquidity_sweeps`, `smc_full_scan` composite.
- **`regime.py`** — `hurst_exponent` (R/S analysis), `variance_ratio`
  (Lo-MacKinlay 1988 with heteroscedasticity-robust z-stat),
  `classify_regime` composite tagger with trading implications.
- **`mtf.py`** — `mtf_alignment` cross-timeframe (D1/H4/H1) confluence
  with score 0-100.
- **`risk_mgmt.py`** — `kelly_fraction`, `fixed_fractional`, `optimal_f`,
  `risk_of_ruin` (MC), `simulate_paths` (bootstrap + parametric),
  `value_at_risk` (VaR + CVaR), `prob_hit_target_or_stop` (MC trade prob
  with EV in R-multiples).
- **`ai_analyst.py`** — BYOK Anthropic Claude integration:
  `ai_daily_briefing` (Sonnet 4.6, structured JSON), `ai_setup_explanation`
  (Haiku 4.5, plain English). Requires `ANTHROPIC_API_KEY`.
- **`reports.py`** — `generate_html_tearsheet` and
  `generate_markdown_briefing`, writes to disk under
  `GOLD_MCP_REPORTS_DIR` (default `~/.cache/gold-mcp/reports/`).
- **`cryptography`** dependency carried over from v3.0.0;
  **`anthropic`** is an optional extra: `pip install 'gold-mcp[ai]'`.
- Ultra tier section added to landing page and README.
- Tests: 20 new Ultra-tier unit tests, 39 total passing, ruff clean.

### Changed

- Bumped to v4.0.0 (semver major because new tier reshapes pricing).

## [3.0.0] - 2026-05-30

Adds a 3-tier monetization layer on top of the v2.0 free tools. The
free tier remains exactly as it was; Pro and Premium unlock additional
tools via an offline-verified Ed25519 license key. No SaaS, no
phone-home, no user accounts — paste the key into the
`GOLD_MCP_LICENSE_KEY` env var and the server registers the additional
tools at startup.

### Added

- **License gating module** (`gold_mcp/license.py`): offline Ed25519
  verification, `Tier` enum, `current_tier()` / `status()` helpers.
- **CLI license issuer** (`gold_mcp/issue_license.py`): `init-keys`,
  `issue --tier --email --days`, `verify` subcommands. Used to mint
  signed Pro/Premium keys for customers.
- **TTL filesystem cache** (`gold_mcp/cache.py`): wraps Yahoo Finance
  calls; default TTLs 60s (price) → 24h (seasonality). Reduces request
  volume ~80% on busy sessions.
- **Pro tier tools** (7 new):
  - `analyze_gold_advanced` — Bollinger + Ichimoku + Fibonacci levels
  - `multi_timeframe_snapshot` — 5m / 1h / 4h / 1d in one call
  - `gold_correlation_regime` — detects DXY decoupling, etc.
  - `get_gold_setups` — multi-indicator confluence scanner
  - `create_gold_alert` / `list_gold_alerts` / `delete_gold_alert`
- **Premium tier tools** (4 new):
  - `backtest_gold_strategy` — 4 strategies, vectorized
  - `gold_walk_forward` — rolling out-of-sample validation
  - `optimize_gold_strategy` — grid search by Sharpe / PF / return
  - `gold_intraday_seasonality` — hourly / session bucketing
- **Free tier additions**: `diagnostic` (show license + available
  tools), `cache_purge` (admin tool).
- Pricing section + tier comparison on the landing page.

### Changed

- `cryptography` added to runtime dependencies (license verification).
- Yahoo calls now route through `cache.cached()` decorators.
- `examples/claude_desktop_config.json` cleaned of stale v1 env vars
  (`GOLD_MCP_L2_DIR`, `GOLD_MCP_TICKS_DIR`, etc.) — those keys are not
  read by v2/v3 code.
- New `examples/claude_desktop_config_pro.json` shows the
  `GOLD_MCP_LICENSE_KEY` env wiring.

### Migration

Existing v2.0.0 users see no behavior change. Free tier remains free,
all v2 tools still work identically. To unlock Pro/Premium, purchase a
license key and add it to your MCP client config under `env`.

## [2.0.0] - 2026-05-24

Repositioned as a small, free, community-driven OSS project. All
tools now run on public Yahoo Finance data only. No tick stream, no
broker account, no environment variables.

### Breaking changes

- **Removed all tick / L2 / microstructure tools**:
  `get_gold_session_summary`, `get_gold_tick_velocity`,
  `get_gold_spread_stats`, `get_gold_session_microstructure`,
  `get_gold_top_of_book`, `get_data_freshness`.
- **Removed all strategy-intelligence tools**:
  `get_xau_daily_setup_config`, `get_xau_asian_box_stats`,
  `get_xau_institutional_footprint`, `get_xau_gamma_regime`,
  `get_xau_trend_entry_signature`.
- **Removed proprietary-data adapters**: `macro_strength`,
  `news_calendar`, `strategy`, `_paths`.
- **Removed analyst tools that implied advice**: `daily_briefing`,
  `risk_assessment`.
- **Removed all `GOLD_MCP_*` environment variables.** The server now
  takes no configuration.
- **Renamed** `analyze_gold_setup` → `gold_market_snapshot` to avoid
  any suggestion of trading guidance.

### Added

- `get_gold_price` and `get_gold_ohlcv` rewritten to use Yahoo Finance
  directly (was previously backed by local MT5 tick parquet files).
- `gold_market_snapshot` aggregator returns price + bars + macro +
  correlations + seasonality + VN parity with a concise bulleted
  summary and an explicit "not financial advice" disclaimer.
- Stronger educational disclaimers throughout.

### Removed

- `gold_mcp/tick_data.py`, `gold_mcp/l2_data.py`,
  `gold_mcp/microstructure.py`
- `gold_mcp/adapters/macro_strength.py`,
  `gold_mcp/adapters/news_calendar.py`,
  `gold_mcp/adapters/strategy.py`, `gold_mcp/adapters/_paths.py`
- `landing/self-host-fonts/` (out of scope for the slimmed core)

### Migration

There is no migration path — v2.0 is intentionally a different
product (community OSS, no private data). Users who relied on v1.x
tick / strategy tools should pin to `v1.0.0`:

```
git checkout v1.0.0
```

## [1.0.0] - 2026-05-24

Initial public release with 23 tools spanning tick microstructure,
strategy intelligence, macro context, AI analyst aggregation, and
Vietnam regional tools. Superseded by v2.0.0 (community pivot).

[Unreleased]: https://github.com/ThaiTrevor/gold-mcp/compare/v4.0.0...HEAD
[4.0.0]: https://github.com/ThaiTrevor/gold-mcp/releases/tag/v4.0.0
[3.0.0]: https://github.com/ThaiTrevor/gold-mcp/releases/tag/v3.0.0
[2.0.0]: https://github.com/ThaiTrevor/gold-mcp/releases/tag/v2.0.0
[1.0.0]: https://github.com/ThaiTrevor/gold-mcp/releases/tag/v1.0.0
