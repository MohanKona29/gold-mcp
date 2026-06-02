"""License issuance + verification round-trip for gold-mcp."""
from pathlib import Path

import pytest

from gold_mcp import issue_license
from gold_mcp import license as lic

KEY_DIR = Path(__file__).parent.parent / ".dev_keys"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("GOLD_MCP_LICENSE_KEY", raising=False)
    monkeypatch.delenv("LICENSE_PRIVATE_KEY_B64", raising=False)
    yield


def test_no_license_means_free():
    assert lic.current_tier() == lic.Tier.FREE


def test_issue_and_verify_pro(monkeypatch):
    key = issue_license.issue("pro", "alice@x.com", days=30, key_dir=KEY_DIR)
    monkeypatch.setenv("GOLD_MCP_LICENSE_KEY", key)
    info = lic.current_license()
    assert info is not None
    assert info.tier == lic.Tier.PRO
    assert info.email == "alice@x.com"
    assert info.is_valid


def test_issue_and_verify_premium(monkeypatch):
    key = issue_license.issue("premium", "bob@x.com", days=365, key_dir=KEY_DIR)
    monkeypatch.setenv("GOLD_MCP_LICENSE_KEY", key)
    assert lic.current_tier() == lic.Tier.PREMIUM


def test_expired_license_rejected(monkeypatch):
    key = issue_license.issue("pro", "x@x.com", days=-1, key_dir=KEY_DIR)
    monkeypatch.setenv("GOLD_MCP_LICENSE_KEY", key)
    assert lic.current_license() is None


def test_tampered_payload_rejected(monkeypatch):
    key = issue_license.issue("pro", "x@x.com", days=30, key_dir=KEY_DIR)
    p, s = key.split(".", 1)
    tampered = f"{p[:-1]}{'A' if p[-1] != 'A' else 'B'}.{s}"
    monkeypatch.setenv("GOLD_MCP_LICENSE_KEY", tampered)
    assert lic.current_license() is None


def test_verify_external_helper():
    key = issue_license.issue("premium", "v@x.com", days=14, key_dir=KEY_DIR)
    result = issue_license.verify_external(key)
    assert result["valid"] is True
    assert result["payload"]["tier"] == "premium"
