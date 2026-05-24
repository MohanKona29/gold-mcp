# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-05-24

Initial public release.

### Added

- **23 MCP tools across 4 layers** registered through FastMCP.
- **Foundation layer**: `get_gold_price`, `get_gold_ohlcv`,
  `get_gold_session_summary`, `get_gold_tick_velocity`,
  `get_gold_spread_stats`, `get_gold_session_microstructure`,
  `get_gold_top_of_book`.
- **Macro context layer**: `get_macro_context`,
  `get_gold_correlations`, `get_gold_seasonality`,
  `get_macro_strength`, `get_news_calendar`.
- **Strategy intelligence layer**: `get_xau_daily_setup_config`,
  `get_xau_asian_box_stats`, `get_xau_institutional_footprint`,
  `get_xau_gamma_regime`, `get_xau_trend_entry_signature`.
- **AI analyst layer**: `analyze_gold_setup`, `daily_briefing`,
  `risk_assessment`.
- **Vietnam regional bonus**: `get_vn_macro`, `estimate_vn_gold_premium`.
- **Health**: `get_data_freshness`.
- **Env-var-driven adapter architecture** keeping all proprietary
  file paths out of the public source tree.
- **Graceful degradation** for missing env vars
  (`{"error": "not_configured", "hint": "..."}`).
- **Static landing page** under `landing/` (drop-on-VPS friendly).
- **Tests**: `tests/test_registration.py` verifying tool registration
  and not-configured fallback paths.

### Security

- Adapters sanitize private path-shaped keys before returning JSON
  (`gold_mcp/adapters/strategy.py::_sanitize`).
- No hard-coded paths, credentials, or vendor names in the public source.
- `.gitignore` excludes raw data, logs, `.env`, and any
  `_PRIVATE_*.md` notes.

[Unreleased]: https://github.com/ThaiTrevor/gold-mcp/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/ThaiTrevor/gold-mcp/releases/tag/v1.0.0
