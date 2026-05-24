# Contributing to gold-mcp

Thanks for the interest. This file describes how to propose changes
and the conventions we follow.

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
  tick_data.py
  l2_data.py
  microstructure.py
  macro_data.py
  analytics.py
  analyst.py          AI-analyst aggregator layer
  adapters/           private-data adapters (env-var driven)
tests/                pytest suite
examples/             example MCP client configs
landing/              static landing page
```

## How to add a new tool

1. Write the implementation in the appropriate module
   (`tick_data.py`, `microstructure.py`, or a new file under `adapters/`).
2. Return a `dict` with explicit, named keys. Include an
   `interpretation` or `summary` field with a one-line read.
3. Register the tool in `server.py` with `@mcp.tool()` and a clear
   docstring. The docstring becomes the tool's description in MCP and
   is what LLMs reason on — be specific about args and return shape.
4. Add the tool name to `EXPECTED_TOOLS` in
   `tests/test_registration.py`.
5. Run `pytest` to confirm everything still loads.

## Coding conventions

- Python 3.10+, type hints encouraged on public functions.
- Use `from __future__ import annotations` in new modules.
- One blank line between top-level definitions, two between sections.
- Adapters that read user-private data must:
  - Read paths from environment variables only (never hard-code).
  - Return `{"error": "not_configured", "hint": "..."}` when the env
    var is missing.
  - Strip absolute paths and other private metadata from any returned
    JSON (see `gold_mcp/adapters/strategy.py::_sanitize`).
- Never commit `.env`, parquet files, or anything inside a Gold Force
  / GOLDFORE folder.

## Tests

- `tests/test_registration.py` checks that every expected tool is
  registered and that adapters degrade gracefully without env vars.
- Add a test when you add a tool. Even a smoke test (`fn()` returns a
  dict without raising) is valuable.
- Run: `pytest -q`.

## Pull requests

- Open a draft PR early if the change is non-trivial — happy to align
  on direction before you invest time.
- One logical change per PR.
- Include a short rationale ("why"), not just "what changed".
- Don't bump version numbers unless asked — releases are tagged
  separately.

## Reporting bugs

Use the issue templates under
[New issue](https://github.com/ThaiTrevor/gold-mcp/issues/new/choose).
Include:

- MCP client (Claude Desktop / Cursor / Windsurf / Cline / etc.) +
  version
- Python version
- Tool that misbehaved + arguments
- Expected vs actual output

For security issues, see [SECURITY.md](SECURITY.md) — do not file a
public bug report.
