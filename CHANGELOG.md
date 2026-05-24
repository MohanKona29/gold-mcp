# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/ThaiTrevor/gold-mcp/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/ThaiTrevor/gold-mcp/releases/tag/v2.0.0
[1.0.0]: https://github.com/ThaiTrevor/gold-mcp/releases/tag/v1.0.0
