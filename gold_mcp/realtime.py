"""Realtime tick storage + Binance PAXG WebSocket worker.

PAXG (Paxos Gold) is an ERC-20 token backed 1:1 by physical gold and
tracks XAU/USD closely (typically within 0.1-0.3%). Binance exposes its
trade stream over a public, unauthenticated WebSocket — making it the
cheapest source of tick-level "gold" data available.

Architecture:
- Worker (run in a separate process): connects to Binance WS, writes
  every trade to a local SQLite database with WAL mode enabled.
- MCP tools: read recent ticks from the same SQLite file. Workers and
  readers never share Python objects — only the database file.

The worker writes a heartbeat row on every tick so MCP tools can answer
"is the feed alive?" without scanning the trades table.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from pathlib import Path

import websocket

_DEFAULT_SYMBOL = "paxgusdt"
_WS_URL_TEMPLATE = "wss://stream.binance.com:9443/ws/{symbol}@trade"


def _db_path() -> Path:
    raw = os.environ.get("GOLD_MCP_REALTIME_DB", "").strip()
    if raw:
        p = Path(raw).expanduser()
    else:
        p = Path.home() / ".cache" / "gold-mcp" / "realtime.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _connect(read_only: bool = False, allow_threads: bool = False) -> sqlite3.Connection:
    path = _db_path()
    if read_only and path.exists():
        uri = f"file:{path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=2.0, check_same_thread=not allow_threads)
    else:
        conn = sqlite3.connect(str(path), timeout=5.0, check_same_thread=not allow_threads)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db() -> None:
    conn = _connect()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS paxg_trades (
                trade_id      INTEGER PRIMARY KEY,
                ts_ms         INTEGER NOT NULL,
                price         REAL    NOT NULL,
                qty           REAL    NOT NULL,
                buyer_maker   INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_trades_ts ON paxg_trades(ts_ms);

            CREATE TABLE IF NOT EXISTS worker_heartbeat (
                id              INTEGER PRIMARY KEY CHECK (id = 1),
                last_tick_ms    INTEGER NOT NULL,
                last_price      REAL    NOT NULL,
                trades_written  INTEGER NOT NULL,
                started_at_ms   INTEGER NOT NULL
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Reader API — used by MCP tools
# ---------------------------------------------------------------------------

def _heartbeat(conn: sqlite3.Connection) -> dict | None:
    row = conn.execute(
        "SELECT last_tick_ms, last_price, trades_written, started_at_ms "
        "FROM worker_heartbeat WHERE id = 1"
    ).fetchone()
    if row is None:
        return None
    return {
        "last_tick_ms": row[0],
        "last_price": row[1],
        "trades_written": row[2],
        "started_at_ms": row[3],
    }


def worker_status() -> dict:
    """Return heartbeat + freshness info. No exceptions on missing data."""
    if not _db_path().exists():
        return {"alive": False, "reason": "db_missing", "db_path": str(_db_path())}
    try:
        conn = _connect(read_only=True)
    except sqlite3.OperationalError as e:
        return {"alive": False, "reason": "db_open_failed", "detail": str(e)}
    try:
        hb = _heartbeat(conn)
    finally:
        conn.close()
    if hb is None:
        return {"alive": False, "reason": "no_heartbeat", "db_path": str(_db_path())}

    now_ms = int(time.time() * 1000)
    age_ms = now_ms - hb["last_tick_ms"]
    return {
        "alive": age_ms < 30_000,
        "last_tick_age_seconds": round(age_ms / 1000, 2),
        "last_price": hb["last_price"],
        "trades_written": hb["trades_written"],
        "uptime_seconds": round((now_ms - hb["started_at_ms"]) / 1000, 1),
        "db_path": str(_db_path()),
    }


def latest_tick() -> dict:
    """Most recent trade. Returns error dict if no data yet."""
    if not _db_path().exists():
        return {"error": "no_db", "hint": "Start the worker first: python -m gold_mcp.realtime"}
    try:
        conn = _connect(read_only=True)
    except sqlite3.OperationalError as e:
        return {"error": "db_open_failed", "detail": str(e)}
    try:
        row = conn.execute(
            "SELECT trade_id, ts_ms, price, qty, buyer_maker "
            "FROM paxg_trades ORDER BY ts_ms DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return {"error": "no_ticks_yet"}
    now_ms = int(time.time() * 1000)
    return {
        "symbol": "PAXGUSDT",
        "trade_id": row[0],
        "ts_ms": row[1],
        "age_seconds": round((now_ms - row[1]) / 1000, 3),
        "price": row[2],
        "qty": row[3],
        "side": "sell" if row[4] else "buy",
    }


def recent_ticks(seconds: int = 60, limit: int = 1000) -> dict:
    """Trades within the last `seconds` window (newest first)."""
    seconds = max(1, min(int(seconds), 3600))
    limit = max(1, min(int(limit), 10_000))
    if not _db_path().exists():
        return {"error": "no_db"}
    cutoff_ms = int(time.time() * 1000) - seconds * 1000
    try:
        conn = _connect(read_only=True)
    except sqlite3.OperationalError as e:
        return {"error": "db_open_failed", "detail": str(e)}
    try:
        rows = conn.execute(
            "SELECT ts_ms, price, qty, buyer_maker FROM paxg_trades "
            "WHERE ts_ms >= ? ORDER BY ts_ms DESC LIMIT ?",
            (cutoff_ms, limit),
        ).fetchall()
    finally:
        conn.close()
    return {
        "symbol": "PAXGUSDT",
        "window_seconds": seconds,
        "count": len(rows),
        "ticks": [
            {"ts_ms": r[0], "price": r[1], "qty": r[2], "side": "sell" if r[3] else "buy"}
            for r in rows
        ],
    }


def realtime_ohlcv(seconds_per_bar: int = 10, lookback_bars: int = 60) -> dict:
    """Build OHLCV bars from raw ticks on the fly.

    Uses SQLite arithmetic to bucket ticks — no Python aggregation, so
    a 60-bar / 10-second-per-bar request scans at most ~600 seconds of
    trades and returns in <50 ms on a warm cache.
    """
    seconds_per_bar = max(1, min(int(seconds_per_bar), 300))
    lookback_bars = max(1, min(int(lookback_bars), 500))
    if not _db_path().exists():
        return {"error": "no_db"}
    window_ms = seconds_per_bar * lookback_bars * 1000
    cutoff_ms = int(time.time() * 1000) - window_ms
    bucket_ms = seconds_per_bar * 1000
    try:
        conn = _connect(read_only=True)
    except sqlite3.OperationalError as e:
        return {"error": "db_open_failed", "detail": str(e)}
    try:
        rows = conn.execute(
            f"""
            SELECT
                (ts_ms / {bucket_ms}) * {bucket_ms}     AS bucket_ms,
                (SELECT price FROM paxg_trades t2
                 WHERE (t2.ts_ms / {bucket_ms}) = (paxg_trades.ts_ms / {bucket_ms})
                 ORDER BY t2.ts_ms ASC LIMIT 1)         AS open,
                MAX(price)                              AS high,
                MIN(price)                              AS low,
                (SELECT price FROM paxg_trades t3
                 WHERE (t3.ts_ms / {bucket_ms}) = (paxg_trades.ts_ms / {bucket_ms})
                 ORDER BY t3.ts_ms DESC LIMIT 1)        AS close,
                SUM(qty)                                AS volume,
                COUNT(*)                                AS tick_count
            FROM paxg_trades
            WHERE ts_ms >= ?
            GROUP BY bucket_ms
            ORDER BY bucket_ms ASC
            """,
            (cutoff_ms,),
        ).fetchall()
    finally:
        conn.close()
    bars = [
        {
            "time_ms": r[0],
            "open": r[1],
            "high": r[2],
            "low": r[3],
            "close": r[4],
            "volume": round(r[5], 6),
            "tick_count": r[6],
        }
        for r in rows
    ]
    return {
        "symbol": "PAXGUSDT",
        "seconds_per_bar": seconds_per_bar,
        "lookback_bars": lookback_bars,
        "rows": len(bars),
        "bars": bars,
        "note": "PAXG (Paxos Gold) tracks XAU/USD within 0.1-0.3%. Free, real-time Binance feed.",
    }


# ---------------------------------------------------------------------------
# Worker — run in a long-lived process via __main__
# ---------------------------------------------------------------------------

class _Worker:
    def __init__(self, symbol: str = _DEFAULT_SYMBOL):
        self.symbol = symbol.lower()
        self.url = _WS_URL_TEMPLATE.format(symbol=self.symbol)
        self.conn = _connect(allow_threads=True)
        self.started_at_ms = int(time.time() * 1000)
        self.trades_written = 0
        self._buffer: list[tuple] = []
        self._buffer_lock = threading.Lock()
        self._stop = False
        # initialise heartbeat row so worker_status() doesn't return no_heartbeat
        # until the first real tick arrives
        self.conn.execute(
            "INSERT OR REPLACE INTO worker_heartbeat "
            "(id, last_tick_ms, last_price, trades_written, started_at_ms) "
            "VALUES (1, ?, 0.0, 0, ?)",
            (self.started_at_ms, self.started_at_ms),
        )
        self.conn.commit()

    def _flush(self) -> None:
        with self._buffer_lock:
            if not self._buffer:
                return
            batch = self._buffer
            self._buffer = []
        try:
            self.conn.executemany(
                "INSERT OR IGNORE INTO paxg_trades "
                "(trade_id, ts_ms, price, qty, buyer_maker) VALUES (?, ?, ?, ?, ?)",
                batch,
            )
            last = batch[-1]
            self.conn.execute(
                "UPDATE worker_heartbeat SET last_tick_ms = ?, last_price = ?, "
                "trades_written = ? WHERE id = 1",
                (last[1], last[2], self.trades_written),
            )
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"[worker] db error: {e}", flush=True)

    def _flusher_loop(self) -> None:
        while not self._stop:
            time.sleep(0.25)
            self._flush()

    def on_message(self, _ws, message: str) -> None:
        try:
            data = json.loads(message)
            tid = int(data["t"])
            ts_ms = int(data["T"])
            price = float(data["p"])
            qty = float(data["q"])
            buyer_maker = 1 if data.get("m") else 0
        except (KeyError, ValueError, TypeError) as e:
            print(f"[worker] bad message: {e}", flush=True)
            return
        with self._buffer_lock:
            self._buffer.append((tid, ts_ms, price, qty, buyer_maker))
            self.trades_written += 1

    def on_error(self, _ws, error) -> None:
        print(f"[worker] ws error: {error}", flush=True)

    def on_close(self, _ws, code, reason) -> None:
        print(f"[worker] ws closed code={code} reason={reason}", flush=True)

    def on_open(self, _ws) -> None:
        print(f"[worker] connected to {self.url}", flush=True)

    def run_forever(self) -> None:
        flusher = threading.Thread(target=self._flusher_loop, daemon=True)
        flusher.start()
        backoff = 1
        try:
            while not self._stop:
                ws = websocket.WebSocketApp(
                    self.url,
                    on_open=self.on_open,
                    on_message=self.on_message,
                    on_error=self.on_error,
                    on_close=self.on_close,
                )
                try:
                    ws.run_forever(ping_interval=180, ping_timeout=10)
                except Exception as e:
                    print(f"[worker] run_forever crashed: {e}", flush=True)
                if self._stop:
                    break
                print(f"[worker] reconnecting in {backoff}s", flush=True)
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
        finally:
            self._stop = True
            self._flush()
            self.conn.close()


def run_worker(symbol: str = _DEFAULT_SYMBOL) -> None:
    init_db()
    w = _Worker(symbol=symbol)
    print(f"[worker] db = {_db_path()}", flush=True)
    try:
        w.run_forever()
    except KeyboardInterrupt:
        print("[worker] interrupted, flushing...", flush=True)
        w._stop = True
        w._flush()


if __name__ == "__main__":
    import sys
    sym = sys.argv[1] if len(sys.argv) > 1 else _DEFAULT_SYMBOL
    run_worker(sym)
