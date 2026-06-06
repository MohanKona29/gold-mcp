"""MetaTrader 5 BYOK adapter.

User is expected to already have an MT5 terminal installed and (ideally)
logged in. gold-mcp attaches to that terminal by path — no credentials
ever pass through this module, and no data crosses the network on our
behalf. The user's broker license terms apply to the data; we only run
analysis on it.

Common gold symbol names across brokers vary: XAUUSD, XAUUSD.r,
XAUUSDm, GOLD, GOLD.cash, GOLD#. `find_symbol` resolves the right one.
"""
from __future__ import annotations

import time
from typing import Any

import MetaTrader5 as mt5  # type: ignore

# Process-global state. FastMCP runs in a single process so this is fine.
_attached = False
_terminal_path: str | None = None


# ---- MT5 timeframe map (broker-side bars) --------------------------------
_TF_MAP = {
    "1m": mt5.TIMEFRAME_M1,
    "2m": mt5.TIMEFRAME_M2,
    "3m": mt5.TIMEFRAME_M3,
    "5m": mt5.TIMEFRAME_M5,
    "10m": mt5.TIMEFRAME_M10,
    "15m": mt5.TIMEFRAME_M15,
    "30m": mt5.TIMEFRAME_M30,
    "1h": mt5.TIMEFRAME_H1,
    "2h": mt5.TIMEFRAME_H2,
    "4h": mt5.TIMEFRAME_H4,
    "1d": mt5.TIMEFRAME_D1,
    "1wk": mt5.TIMEFRAME_W1,
    "1mo": mt5.TIMEFRAME_MN1,
}

_GOLD_HINTS = ("XAUUSD", "GOLD", "XAUUSD.r", "XAUUSDm", "GOLD#", "GOLD.cash")


def _last_error() -> dict:
    code, desc = mt5.last_error()
    return {"code": code, "detail": desc}


def attach(terminal_path: str | None = None, timeout_ms: int = 60_000) -> dict:
    """Attach to a running MT5 terminal. The user must already have it
    open and logged in. Returns the terminal + account fingerprint.
    """
    global _attached, _terminal_path
    kwargs: dict[str, Any] = {"timeout": timeout_ms}
    if terminal_path:
        kwargs["path"] = terminal_path
    ok = mt5.initialize(**kwargs)
    if not ok:
        return {"attached": False, "error": _last_error()}
    _attached = True
    _terminal_path = terminal_path

    term = mt5.terminal_info()
    acct = mt5.account_info()
    return {
        "attached": True,
        "terminal": {
            "company": getattr(term, "company", None),
            "name": getattr(term, "name", None),
            "build": getattr(term, "build", None),
            "connected": getattr(term, "connected", None),
            "path": getattr(term, "path", None),
        },
        "account": (
            {
                "login": acct.login,
                "server": acct.server,
                "name": acct.name,
                "currency": acct.currency,
                "leverage": acct.leverage,
                "trade_mode": ["demo", "contest", "real"][acct.trade_mode]
                if acct.trade_mode in (0, 1, 2) else acct.trade_mode,
                "balance": acct.balance,
                "equity": acct.equity,
            }
            if acct is not None
            else None
        ),
    }


def detach() -> dict:
    global _attached
    mt5.shutdown()
    _attached = False
    return {"detached": True}


def status() -> dict:
    if not _attached:
        return {"attached": False}
    term = mt5.terminal_info()
    if term is None:
        return {"attached": False, "error": _last_error()}
    return {
        "attached": True,
        "connected": term.connected,
        "company": term.company,
        "ping_last_ms": getattr(term, "ping_last", None),
        "terminal_path": _terminal_path,
    }


def _require() -> dict | None:
    if not _attached:
        return {"error": "not_attached", "hint": "Call mt5_attach(terminal_path) first."}
    return None


def find_symbol(query: str = "gold") -> dict:
    """Resolve broker-specific gold symbol name.

    Returns up to 10 matches. Each broker names gold differently.
    """
    err = _require()
    if err:
        return err
    q = query.upper()
    all_syms = mt5.symbols_get() or ()
    hits = []
    for s in all_syms:
        name = s.name.upper()
        if q in name or any(h in name for h in _GOLD_HINTS if q in {"GOLD", "XAU"}):
            hits.append(
                {
                    "name": s.name,
                    "description": s.description,
                    "path": s.path,
                    "visible": s.visible,
                    "trade_mode": s.trade_mode,
                }
            )
            if len(hits) >= 10:
                break
    return {"query": query, "matches": hits}


def _ensure_visible(symbol: str) -> bool:
    """Some brokers hide symbols by default — must select() before query."""
    info = mt5.symbol_info(symbol)
    if info is None:
        return False
    if not info.visible:
        return bool(mt5.symbol_select(symbol, True))
    return True


def get_tick(symbol: str = "XAUUSD") -> dict:
    err = _require()
    if err:
        return err
    if not _ensure_visible(symbol):
        return {"error": "symbol_not_found", "symbol": symbol, "hint": "Use mt5_find_symbol to discover broker name."}
    t = mt5.symbol_info_tick(symbol)
    if t is None:
        return {"error": "no_tick", "detail": _last_error()}
    info = mt5.symbol_info(symbol)
    return {
        "symbol": symbol,
        "broker_time_ms": int(t.time_msc),
        "local_time_ms": int(time.time() * 1000),
        "bid": t.bid,
        "ask": t.ask,
        "last": t.last,
        "spread_points": (round((t.ask - t.bid) / info.point, 1) if info and info.point else None),
        "volume": t.volume,
        "note": "broker_time_ms is in broker server timezone (often GMT+2/+3), not UTC. Compare ticks within the same broker, not against UTC clock.",
    }


def get_ohlcv(symbol: str = "XAUUSD", timeframe: str = "1h", lookback: int = 100) -> dict:
    err = _require()
    if err:
        return err
    if timeframe not in _TF_MAP:
        return {"error": "bad_timeframe", "supported": list(_TF_MAP.keys())}
    if not _ensure_visible(symbol):
        return {"error": "symbol_not_found", "symbol": symbol}
    lookback = max(1, min(int(lookback), 5000))
    bars = mt5.copy_rates_from_pos(symbol, _TF_MAP[timeframe], 0, lookback)
    if bars is None or len(bars) == 0:
        return {"error": "no_bars", "detail": _last_error()}
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "rows": len(bars),
        "bars": [
            {
                "time": int(b["time"]),
                "open": float(b["open"]),
                "high": float(b["high"]),
                "low": float(b["low"]),
                "close": float(b["close"]),
                "tick_volume": int(b["tick_volume"]),
                "spread": int(b["spread"]),
                "real_volume": int(b["real_volume"]),
            }
            for b in bars
        ],
        "source": f"mt5:{_terminal_path or 'auto'}",
    }


def get_ticks(symbol: str = "XAUUSD", seconds_back: int = 60, limit: int = 5000) -> dict:
    err = _require()
    if err:
        return err
    if not _ensure_visible(symbol):
        return {"error": "symbol_not_found", "symbol": symbol}
    seconds_back = max(1, min(int(seconds_back), 3600))
    limit = max(1, min(int(limit), 20_000))
    now = int(time.time())
    raw = mt5.copy_ticks_range(symbol, now - seconds_back, now, mt5.COPY_TICKS_ALL)
    if raw is None:
        return {"error": "no_ticks", "detail": _last_error()}
    raw = raw[-limit:]
    return {
        "symbol": symbol,
        "window_seconds": seconds_back,
        "count": len(raw),
        "ticks": [
            {
                "time_ms": int(t["time_msc"]),
                "bid": float(t["bid"]),
                "ask": float(t["ask"]),
                "last": float(t["last"]),
                "volume": int(t["volume"]),
            }
            for t in raw
        ],
        "source": f"mt5:{_terminal_path or 'auto'}",
    }


def account_info() -> dict:
    err = _require()
    if err:
        return err
    a = mt5.account_info()
    if a is None:
        return {"error": "no_account", "detail": _last_error()}
    return {
        "login": a.login,
        "server": a.server,
        "currency": a.currency,
        "leverage": a.leverage,
        "trade_mode": ["demo", "contest", "real"][a.trade_mode]
        if a.trade_mode in (0, 1, 2) else a.trade_mode,
        "balance": a.balance,
        "equity": a.equity,
        "margin": a.margin,
        "margin_free": a.margin_free,
        "margin_level": a.margin_level,
        "profit": a.profit,
    }
