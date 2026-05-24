# Security policy

## Supported versions

| Version | Supported          |
| ------- | ------------------ |
| 2.0.x   | :white_check_mark: |
| 1.0.x   | :x: (superseded — see CHANGELOG)  |

## Reporting a vulnerability

If you believe you have found a security vulnerability in `gold-mcp`,
please report it privately. **Do not file a public issue or PR.**

- Open a private security advisory on GitHub:
  [Report a vulnerability](https://github.com/ThaiTrevor/gold-mcp/security/advisories/new)
- Or contact the maintainer via the GitHub profile.

Please include:

- A clear description of the vulnerability and impact
- Steps to reproduce (proof of concept)
- Affected version(s)
- Any suggested mitigation

We will acknowledge receipt within 72 hours and aim to provide an
initial assessment within 7 days.

## Scope

In scope:

- `gold_mcp/` Python package
- `tests/` test suite
- `landing/` static landing page

Out of scope:

- Third-party MCP clients that consume this server
- The `yfinance` library or Yahoo Finance itself
- Vulnerabilities that require local OS / user-level access to a
  machine already running the server

## Notes for operators

`gold-mcp` v2.x reads no environment variables and no local data
files. The only network calls go to Yahoo Finance via `yfinance`.
There is no auth, no persistence, no telemetry.

If you fork the project to add adapters that read private data or
make outbound calls to other services, make sure to:

- Read credentials from env vars only — never hard-code.
- Add the new env-var names to `.env.example` (empty values).
- Audit any third-party endpoint before merging.
