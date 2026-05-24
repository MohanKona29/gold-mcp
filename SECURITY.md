# Security policy

## Supported versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a vulnerability

If you believe you have found a security vulnerability in `gold-mcp`,
please report it privately. **Do not file a public issue or PR.**

- Open a private security advisory on GitHub:
  [Report a vulnerability](https://github.com/ThaiTrevor/gold-mcp/security/advisories/new)
- Or email: see the contact in the GitHub profile.

Please include:

- A clear description of the vulnerability and impact
- Steps to reproduce (proof of concept)
- Affected version(s)
- Any suggested mitigation

We will acknowledge receipt within 72 hours and aim to provide an
initial assessment within 7 days. We will keep you informed about the
fix progress and credit you in the release notes (if desired) once a
fix is published.

## Scope

In scope:

- `gold_mcp/` Python package and adapters
- `tests/` test suite
- `landing/` static landing page
- Any official deploy artifacts published from this repo

Out of scope:

- User-private data files referenced via environment variables
- Third-party MCP clients that consume this server
- Vulnerabilities that require local OS / user-level access to a
  machine already running the server

## Hardening guidance for operators

`gold-mcp` reads file paths from environment variables. When deploying
to a multi-tenant or remote environment:

- Restrict env-var values to paths inside a known data root.
- Run the process with a least-privilege OS user.
- Front the server with rate limiting and authentication if exposing
  it over HTTP / SSE.
- Audit any custom adapters before merging.
