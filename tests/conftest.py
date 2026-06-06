"""Global test fixtures.

v4.1 (2026-06-06): tests issue licenses with `.dev_keys`, but `license.py`
ships with the PRODUCTION public key hardcoded (so prod licenses verify
without any config). Without this fixture, every test that issues a license
in-test would fail because the signature was made with the dev private key.

Solution: autouse fixture loads `.dev_keys/license_public.b64` and patches
`gold_mcp.license.PUBLIC_KEY_B64` for the test session only. Real prod is
untouched.
"""
from pathlib import Path

import pytest

_DEV_PUB_PATH = Path(__file__).parent.parent / ".dev_keys" / "license_public.b64"


@pytest.fixture(autouse=True)
def _patch_public_key_for_tests(monkeypatch):
    if _DEV_PUB_PATH.exists():
        dev_pub = _DEV_PUB_PATH.read_text().strip()
        monkeypatch.setattr("gold_mcp.license.PUBLIC_KEY_B64", dev_pub)
    yield
