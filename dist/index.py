import os
import uvicorn
import yfinance as yf
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.middleware.cors import CORSMiddleware

# Initialize the Core Server Engine
server = Server("Gold-Tracker")

@server.list_tools()
async def handle_list_tools():
    return [
        {
            "name": "get_gold_price",
            "description": "Fetch the current real-time spot price of Gold (XAU/USD).",
            "inputSchema": {"type": "object", "properties": {}}
        }
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None):
    if name == "get_gold_price":
        try:
            ticker = yf.Ticker("XAUUSD=X")
            data = ticker.fast_info
            current_price = data.last_price
            currency = data.currency
            return [{"type": "text", "text": f"Current XAU/USD (Gold Spot) Price: {current_price:.2f} {currency}"}]
        except Exception as e:
            return [{"type": "text", "text": f"Error: {str(e)}"}]
    raise ValueError(f"Unknown tool: {name}")

# Web network integration layer
sse = SseServerTransport("/sse")

async def handle_sse(request):
    async with sse.connect_sse(request.scope, request.receive, request._send):
        await server.run(
            request.scope, request.receive, request._send,
            InitializationOptions(
                server_name="Gold-Tracker",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

# Starlette App Wrapper with browser security unlocked
app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse, methods=["GET", "POST"]),
        Route("/messages", endpoint=sse.handle_post_message, methods=["POST"]),
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
