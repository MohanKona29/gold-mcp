import os
import yfinance as yf
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("Gold-Tracker")

@mcp.tool()
def get_gold_price() -> str:
    """Fetch the current real-time spot price of Gold (XAU/USD)."""
    try:
        ticker = yf.Ticker("XAUUSD=X")
        data = ticker.fast_info
        current_price = data.last_price
        currency = data.currency
        return f"Current XAU/USD (Gold Spot) Price: {current_price:.2f} {currency}"
    except Exception as e:
        return f"Error fetching gold data: {str(e)}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    # Tell FastMCP to host its own official Streamable HTTP server natively
    mcp.run(transport="http", host="0.0.0.0", port=port)
