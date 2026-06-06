"""Lemon Squeezy webhook handler.

Receives `subscription_created` / `subscription_updated` events, validates
the HMAC signature, issues a license key, and delivers it via SMTP (or
logs it if SMTP is not configured).

Required env vars:
    LEMONSQUEEZY_SIGNING_SECRET   — webhook signing secret from LS dashboard
    LICENSE_PRIVATE_KEY_B64       — your private signing key (Ed25519)
    LS_VARIANT_ID_PRO             — LS variant ID for your Pro plan
    LS_VARIANT_ID_PREMIUM         — LS variant ID for your Premium plan
    LS_VARIANT_ID_ULTRA           — LS variant ID for your Ultra plan

Optional (for email delivery):
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM

Run:
    pip install 'gold-mcp[webhook]'
    python -m gold_mcp.webhook.lemonsqueezy
    # then expose port 8000 (ngrok / fly.io / your VPS) and point LS at it
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import smtplib
import sys
from email.mime.text import MIMEText

logger = logging.getLogger("gold-mcp.webhook")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _verify_signature(body: bytes, signature_header: str) -> bool:
    secret = os.environ.get("LEMONSQUEEZY_SIGNING_SECRET", "").encode()
    if not secret:
        logger.error("LEMONSQUEEZY_SIGNING_SECRET not set")
        return False
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def _tier_for_variant(variant_id: str) -> str | None:
    if variant_id == os.environ.get("LS_VARIANT_ID_PRO", ""):
        return "pro"
    if variant_id == os.environ.get("LS_VARIANT_ID_PREMIUM", ""):
        return "premium"
    if variant_id == os.environ.get("LS_VARIANT_ID_ULTRA", ""):
        return "ultra"
    return None


def _send_email(to: str, license_key: str, tier: str, days: int) -> bool:
    host = os.environ.get("SMTP_HOST", "")
    if not host:
        logger.warning("SMTP not configured; license key NOT emailed: %s", license_key)
        return False
    msg = MIMEText(_email_body(license_key, tier, days), "plain")
    msg["Subject"] = f"Your gold-mcp {tier.capitalize()} license"
    msg["From"] = os.environ.get("SMTP_FROM", "noreply@example.com")
    msg["To"] = to
    try:
        with smtplib.SMTP_SSL(host, int(os.environ.get("SMTP_PORT", "465"))) as s:
            user = os.environ.get("SMTP_USER", "")
            if user:
                s.login(user, os.environ.get("SMTP_PASSWORD", ""))
            s.send_message(msg)
        logger.info("License emailed to %s (tier=%s)", to, tier)
        return True
    except Exception as e:
        logger.exception("SMTP send failed: %s", e)
        return False


def _email_body(license_key: str, tier: str, days: int) -> str:
    return f"""Thank you for upgrading to gold-mcp {tier.capitalize()}!

Your license key (valid for {days} days):

{license_key}

To activate, add it to your MCP client config:

  "env": {{
    "GOLD_MCP_LICENSE_KEY": "{license_key}",
    ...
  }}

Or export it before launching the server:

  export GOLD_MCP_LICENSE_KEY="{license_key}"

Verify activation by calling the `diagnostic` MCP tool — `tier_active`
should show "{tier}".

Need help? Reply to this email.
"""


def handle_event(event_name: str, payload: dict) -> dict:
    """Process a parsed LS event. Returns a summary dict for logging/HTTP body."""
    from .. import issue_license

    if event_name not in ("subscription_created", "subscription_updated", "order_created"):
        return {"ignored": event_name}

    data = payload.get("data", {}).get("attributes", {})
    customer_email = data.get("user_email") or payload.get("meta", {}).get("custom_data", {}).get("email")
    variant_id = str(data.get("variant_id") or data.get("first_subscription_item", {}).get("variant_id", ""))
    tier = _tier_for_variant(variant_id)
    if not tier:
        return {"ignored": "unknown_variant", "variant_id": variant_id}
    if not customer_email:
        return {"error": "no_customer_email", "event": event_name}

    days = 30 if "monthly" in (data.get("variant_name", "").lower()) else 365
    try:
        key = issue_license.issue(tier=tier, email=customer_email, days=days,
                                   key_dir=None)  # uses LICENSE_PRIVATE_KEY_B64 env
    except Exception as e:
        logger.exception("License issuance failed")
        return {"error": "issuance_failed", "detail": str(e)}

    _send_email(customer_email, key, tier, days)
    return {"issued": True, "tier": tier, "email": customer_email, "days": days}


# ---------- HTTP server (optional, requires Flask) ----------

def make_app():
    try:
        from flask import Flask, request
    except ImportError as e:
        raise SystemExit(
            "Flask required for webhook server. Install with: "
            "pip install 'gold-mcp[webhook]'"
        ) from e

    app = Flask(__name__)

    @app.post("/webhook/lemonsqueezy")
    def lemonsqueezy_webhook():
        body = request.get_data()
        sig = request.headers.get("X-Signature", "")
        if not _verify_signature(body, sig):
            return {"error": "invalid_signature"}, 401
        try:
            payload = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {"error": "invalid_json"}, 400
        event_name = payload.get("meta", {}).get("event_name", "")
        result = handle_event(event_name, payload)
        logger.info("Webhook handled: event=%s result=%s", event_name, result)
        return result, 200

    @app.get("/health")
    def health():
        return {"ok": True}

    return app


def main():
    app = make_app()
    port = int(os.environ.get("WEBHOOK_PORT", "8000"))
    logger.info("Starting webhook server on :%d", port)
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    sys.exit(main() or 0)
