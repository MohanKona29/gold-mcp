"""Server configuration constants.

This server reads no local files and requires no environment variables.
All market data comes from Yahoo Finance.
"""
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
