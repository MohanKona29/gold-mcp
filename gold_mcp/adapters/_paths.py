"""Resolve data file paths from environment variables.

All proprietary data locations are read from env vars so the public
repo never contains absolute paths to user-private sources.
"""
import os
from pathlib import Path


def _resolve(env_var: str) -> Path | None:
    """Return Path from env var, or None if unset."""
    val = os.environ.get(env_var)
    if not val:
        return None
    p = Path(val).expanduser()
    return p if p.exists() else None


def macro_strength_file() -> Path | None:
    """Path to the precomputed macro strength JSON.

    Expected schema (top-level keys): meta, rankings, currencies, trade_signals.
    """
    return _resolve("GOLD_MCP_MACRO_STRENGTH_FILE")


def news_calendar_file() -> Path | None:
    """Path to the news calendar CSV.

    Expected columns: date, currency, event, actual, forecast, previous, impact.
    """
    return _resolve("GOLD_MCP_NEWS_CALENDAR_FILE")


def radar_signals_file() -> Path | None:
    """Path to the VSA radar signals config JSON (pattern rules + thresholds)."""
    return _resolve("GOLD_MCP_RADAR_SIGNALS_FILE")


def strategy_results_dir() -> Path | None:
    """Directory containing strategy engine result JSON/CSV outputs."""
    return _resolve("GOLD_MCP_STRATEGY_RESULTS_DIR")


def broker_consensus_dir() -> Path | None:
    """Directory containing aggregated broker consensus data."""
    return _resolve("GOLD_MCP_BROKER_CONSENSUS_DIR")


def not_configured(name: str, env_var: str) -> dict:
    """Standard 'this tool is not wired up on this machine' response."""
    return {
        "error": "not_configured",
        "tool": name,
        "hint": f"Set environment variable {env_var} to enable this tool.",
    }
