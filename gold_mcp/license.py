"""Offline Ed25519 license verification for gold-mcp Pro / Premium tiers.

Free tier requires no license. Pro/Premium tiers require a valid
license key in the `GOLD_MCP_LICENSE_KEY` env var.

Key format:  base64url(payload_json) + "." + base64url(signature)
Payload:     {"tier": "pro", "email": "u@x", "issued_at": "...", "expires_at": "..."}

The public key below is the DEV key shipped with this repo — replace
it with your production public key before issuing real licenses
(`python -m gold_mcp.issue_license init-keys`).
"""
from __future__ import annotations

import base64
import enum
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

# DEV public key — REPLACE IN PRODUCTION.
PUBLIC_KEY_B64 = "PN9ZFgB88YSAgENsEaHllBwI-LwWa4rk9NDKA0i-Pp8"


class Tier(enum.IntEnum):
    FREE = 0
    PRO = 10
    PREMIUM = 20
    ULTRA = 30

    @classmethod
    def from_string(cls, s: str) -> Tier:
        return {"free": cls.FREE, "pro": cls.PRO,
                "premium": cls.PREMIUM, "ultra": cls.ULTRA}[s.lower()]


@dataclass(frozen=True)
class LicenseInfo:
    tier: Tier
    email: str
    issued_at: datetime
    expires_at: datetime
    raw_payload: dict

    @property
    def is_valid(self) -> bool:
        return datetime.now(timezone.utc) < self.expires_at

    @property
    def days_remaining(self) -> int:
        delta = self.expires_at - datetime.now(timezone.utc)
        return max(0, delta.days)


def _b64decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def verify_key(license_key: str) -> LicenseInfo | None:
    try:
        payload_b64, sig_b64 = license_key.strip().split(".", 1)
    except ValueError:
        return None
    try:
        payload_bytes = _b64decode(payload_b64)
        sig_bytes = _b64decode(sig_b64)
    except (ValueError, TypeError):
        return None
    try:
        pub = Ed25519PublicKey.from_public_bytes(_b64decode(PUBLIC_KEY_B64))
        pub.verify(sig_bytes, payload_bytes)
    except (InvalidSignature, ValueError):
        return None
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
        return LicenseInfo(
            tier=Tier.from_string(payload["tier"]),
            email=payload.get("email", ""),
            issued_at=datetime.fromisoformat(payload["issued_at"].replace("Z", "+00:00")),
            expires_at=datetime.fromisoformat(payload["expires_at"].replace("Z", "+00:00")),
            raw_payload=payload,
        )
    except (KeyError, ValueError):
        return None


def current_license() -> LicenseInfo | None:
    key = os.environ.get("GOLD_MCP_LICENSE_KEY", "").strip()
    if not key:
        return None
    info = verify_key(key)
    if info is None or not info.is_valid:
        return None
    return info


def current_tier() -> Tier:
    info = current_license()
    return info.tier if info else Tier.FREE


def status() -> dict:
    info = current_license()
    if info is None:
        raw = os.environ.get("GOLD_MCP_LICENSE_KEY", "").strip()
        return {
            "tier": "free",
            "license_present": bool(raw),
            "license_valid": False,
            "message": (
                "Free tier active. Set GOLD_MCP_LICENSE_KEY to unlock Pro/Premium tools."
                if not raw
                else "License key present but invalid or expired."
            ),
        }
    return {
        "tier": info.tier.name.lower(),
        "license_present": True,
        "license_valid": True,
        "email": info.email,
        "expires_at": info.expires_at.isoformat(),
        "days_remaining": info.days_remaining,
    }
