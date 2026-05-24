"""Server configuration read from environment variables.

Paths to local data directories are resolved from env vars. They default
to empty so the public source code does not encode any user-specific
file layout. The tick / L2 modules check whether the resolved path
actually exists before using it.
"""
import os
from pathlib import Path

L2_DIR = Path(os.environ.get("GOLD_MCP_L2_DIR", ""))
TICKS_DIR = Path(os.environ.get("GOLD_MCP_TICKS_DIR", ""))

SYMBOL = "XAUUSD"
YF_SYMBOL = "GC=F"

MACRO_SYMBOLS = {
    "DXY": "DX-Y.NYB",
    "US10Y": "^TNX",
    "US02Y": "^IRX",
    "SPX": "^GSPC",
    "VIX": "^VIX",
    "BTC": "BTC-USD",
    "SILVER": "SI=F",
    "OIL": "CL=F",
}
