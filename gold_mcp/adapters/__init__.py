"""Private data adapters.

These modules read proprietary data from local files configured via
environment variables. They never hard-code paths, URLs, credentials,
or vendor names — only the shape of the data is described publicly.

If an env var is not set, the corresponding loader returns a structured
'not_configured' error so the MCP tool degrades gracefully on machines
that don't have the underlying data sources.
"""
