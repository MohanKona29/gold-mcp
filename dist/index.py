import asyncio
import yfinance as yf
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route
import uvicorn

# Initialize the MCP Server
server = Server("gold-mcp")

@server.list_tools()
async def handle_list_tools():
    """List available financial tools."""
    return [
        {
            "name": "get_gold_price",
            "description": "Fetch the current real-time or latest spot price of Gold (XAU/USD).",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        }
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None):
    """Execute the gold price tool lookup."""
    if name == "get_gold_price":
        try:
            # Fetch Gold Spot ticker data from Yahoo Finance
            ticker = yf.Ticker("XAUUSD=X")
            data = ticker.fast_info
            current_price = data.last_price
            currency = data.currency
            
            return [
                {
                    "type": "text",
                    "text": f"Current XAU/USD (Gold Spot) Price: {current_price:.2f} {currency}"
                }
            ]
        except Exception as e:
            return [
                {
                    "type": "text",
                    "text": f"Error fetching gold data: {str(e)}"
                }
            ]
    raise ValueError(f"Unknown tool: {name}")

# Set up the network transport layer for web communication
sse = SseServerTransport("/sse")

async def handle_sse(request):
    async with sse.connect_sse(request.scope, request.receive, request._send):
        await server.run(
            request.scope,
            request.receive,
            request._send,
            InitializationOptions(
                server_name="gold-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

# Wrap inside a standard web app for Render deployment
app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse, methods=["GET", "POST"]),
        Route("/messages", endpoint=sse.handle_post_message, methods=["POST"]),
    ]
)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
