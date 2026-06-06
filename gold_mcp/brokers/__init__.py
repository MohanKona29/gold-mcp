"""BYOK (Bring Your Own Key) broker adapters.

The user connects their own broker terminal (MT5, etc.) and gold-mcp
reads from it. gold-mcp never stores credentials, never re-distributes
the broker's price feed to anyone else — it only invokes analysis tools
against the user's already-licensed local data.

This is the clean separation that makes a commercial MCP product
possible without violating broker / exchange data-redistribution
terms: we sell the analysis layer, the customer brings the feed.
"""
