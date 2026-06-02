"""CLI for issuing gold-mcp Pro/Premium licenses.

Usage:
    python -m gold_mcp.issue_license init-keys
    python -m gold_mcp.issue_license issue --tier pro --email u@x.com --days 30
    python -m gold_mcp.issue_license verify <license_key>
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

DEFAULT_KEY_DIR = Path(".dev_keys")
PRIVATE_KEY_FILE = "license_private.b64"
PUBLIC_KEY_FILE = "license_public.b64"


def _b64encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _b64decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def init_keys(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    if (out_dir / PRIVATE_KEY_FILE).exists():
        print(f"[!] {out_dir / PRIVATE_KEY_FILE} already exists. Refusing to overwrite.",
              file=sys.stderr)
        sys.exit(1)
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    priv_b64 = _b64encode(priv.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    ))
    pub_b64 = _b64encode(pub.public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw,
    ))
    (out_dir / PRIVATE_KEY_FILE).write_text(priv_b64 + "\n", encoding="utf-8")
    (out_dir / PUBLIC_KEY_FILE).write_text(pub_b64 + "\n", encoding="utf-8")
    print(f"[+] Wrote private key to {out_dir / PRIVATE_KEY_FILE}")
    print(f"[+] Wrote public key  to {out_dir / PUBLIC_KEY_FILE}")
    print()
    print("=" * 60)
    print("NEXT STEP — paste this PUBLIC key into gold_mcp/license.py")
    print(f'  PUBLIC_KEY_B64 = "{pub_b64}"')
    print("=" * 60)


def _load_private(key_dir: Path | None) -> Ed25519PrivateKey:
    env_key = os.environ.get("LICENSE_PRIVATE_KEY_B64", "").strip()
    if env_key:
        return Ed25519PrivateKey.from_private_bytes(_b64decode(env_key))
    if key_dir is None:
        raise FileNotFoundError(
            "No private key. Set LICENSE_PRIVATE_KEY_B64 env var or pass --key-dir."
        )
    path = key_dir / PRIVATE_KEY_FILE
    if not path.exists():
        raise FileNotFoundError(
            f"No private key at {path}. Run `python -m gold_mcp.issue_license init-keys`."
        )
    return Ed25519PrivateKey.from_private_bytes(
        _b64decode(path.read_text(encoding="utf-8").strip())
    )


def issue(tier: str, email: str, days: int, key_dir: Path | None = None) -> str:
    if tier not in ("pro", "premium", "ultra"):
        raise ValueError("tier must be 'pro', 'premium', or 'ultra'")
    priv = _load_private(key_dir)
    now = datetime.now(timezone.utc)
    payload = {
        "tier": tier,
        "email": email,
        "issued_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": (now + timedelta(days=days)).isoformat().replace("+00:00", "Z"),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig = priv.sign(payload_bytes)
    return f"{_b64encode(payload_bytes)}.{_b64encode(sig)}"


def verify_external(license_key: str, public_key_b64: str | None = None) -> dict:
    from . import license as lic
    pub_b64 = public_key_b64 or lic.PUBLIC_KEY_B64
    try:
        payload_b64, sig_b64 = license_key.strip().split(".", 1)
        payload_bytes = _b64decode(payload_b64)
        sig_bytes = _b64decode(sig_b64)
        pub = Ed25519PublicKey.from_public_bytes(_b64decode(pub_b64))
        pub.verify(sig_bytes, payload_bytes)
        return {"valid": True, "payload": json.loads(payload_bytes.decode("utf-8"))}
    except Exception as e:
        return {"valid": False, "error": str(e)}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="License issuer for gold-mcp")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init-keys", help="Generate a new keypair")
    p_init.add_argument("--out", default=str(DEFAULT_KEY_DIR))

    p_issue = sub.add_parser("issue", help="Issue a license key")
    p_issue.add_argument("--tier", required=True, choices=["pro", "premium", "ultra"])
    p_issue.add_argument("--email", required=True)
    p_issue.add_argument("--days", type=int, default=30)
    p_issue.add_argument("--key-dir", default=str(DEFAULT_KEY_DIR))

    p_verify = sub.add_parser("verify", help="Verify a license key")
    p_verify.add_argument("license_key")

    args = p.parse_args(argv)

    if args.cmd == "init-keys":
        init_keys(Path(args.out))
        return 0
    if args.cmd == "issue":
        print(issue(args.tier, args.email, args.days, Path(args.key_dir)))
        return 0
    if args.cmd == "verify":
        result = verify_external(args.license_key)
        print(json.dumps(result, indent=2))
        return 0 if result.get("valid") else 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
