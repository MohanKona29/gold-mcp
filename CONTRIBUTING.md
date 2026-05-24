# Contributing to gold-mcp

Thanks for the interest. This is a small, focused community project.
Contributions are welcome — please keep them in the same spirit.

## Quick start

```bash
git clone https://github.com/ThaiTrevor/gold-mcp.git
cd gold-mcp
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
pytest
```

## Project layout

```
gold_mcp/             core package
  server.py           FastMCP tool wiring
  gold_data.py        Yahoo Finance gold price + OHLCV
  macro_data.py       macro snapshot + correlation matrix
  analytics.py        seasonality
  analyst.py          one-call aggregator
  adapters/
    vn_macro.py       Vietnam macro context (community contribution)
tests/                pytest suite
examples/             example MCP client configs
landing/              static landing page used by the project site
```

## What kinds of contributions fit

**Welcome**:

- Small tools that wrap a single public data source
- Improvements to existing tool docstrings (the docstring is what the
  LLM sees — clarity helps everyone)
- Cross-platform compatibility fixes
- Tests
- README / docs improvements
- New MCP-client install snippets

**Not a fit (please open a discussion first)**:

- Tools that need a paid API key or scraped private data
- Tools that recommend trades, allocate capital, or otherwise function
  as financial advice
- Heavy dependencies that meaningfully grow the install footprint
- Anything tick / L2 / orderbook — the project intentionally stays on
  public daily / intraday data

## How to add a new tool

1. Write the implementation in the appropriate module (or a new
   single-file module under `adapters/` if it's a community-specific
   data source).
2. Return a `dict` with explicit, named keys. Include a `summary` or
   `interpretation` field with a one-line read whenever it makes sense.
3. Register the tool in `server.py` with `@mcp.tool()` and a clear
   docstring. The docstring becomes the tool's description in MCP and
   is what LLMs reason on — be specific about args and return shape.
4. Add the tool name to `EXPECTED_TOOLS` in
   `tests/test_registration.py`.
5. Run `pytest` and `ruff check gold_mcp tests`.

## Coding conventions

- Python 3.10+; type hints encouraged on public functions.
- Use `from __future__ import annotations` in new modules.
- Run `ruff check --fix` before committing.
- No hard-coded paths, credentials, or vendor names in the source.
- No tools that produce trading recommendations.

## Tests

- `tests/test_registration.py` checks that every expected tool is
  registered and the server boots with no environment configured.
- Add a test when you add a tool. Even a smoke test (`fn()` returns a
  dict without raising) is valuable.
- Run: `pytest -q`.

## Pull requests

- Open a draft PR early if the change is non-trivial — happy to align
  on direction before you invest time.
- One logical change per PR.
- Include a short rationale ("why"), not just "what changed".
- Don't bump version numbers in PRs — releases are tagged separately.

## Reporting bugs

Use the issue templates under
[New issue](https://github.com/ThaiTrevor/gold-mcp/issues/new/choose).

For security issues, see [SECURITY.md](SECURITY.md) — do not file a
public bug report.
