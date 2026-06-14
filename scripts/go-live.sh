#!/usr/bin/env bash
# gold-mcp go-live helper.
# Bundles step 5 (edit landing checkout URLs) + step 6 (deploy to VPS)
# + verification of pthaicapital.io.vn/mcp into a single command.
#
# Run AFTER:
#  - PyPI upload done (`twine upload dist/*`)
#  - 3 Lemon Squeezy products created, "Buy" URLs copied
#
# Usage:
#   bash scripts/go-live.sh \
#     <PRO_URL> <PREMIUM_URL> <ULTRA_URL> \
#     <VPS_SSH_TARGET> [<REMOTE_PATH>]
#
# Example:
#   bash scripts/go-live.sh \
#     https://pthaicapital.lemonsqueezy.com/buy/abc-pro \
#     https://pthaicapital.lemonsqueezy.com/buy/abc-premium \
#     https://pthaicapital.lemonsqueezy.com/buy/abc-ultra \
#     user@vps.pthaicapital.io.vn \
#     /var/www/pthaicapital.io.vn/public/mcp
#
# Idempotent: re-running with same args is safe.

set -euo pipefail

PRO_URL="${1:?missing PRO_URL}"
PREMIUM_URL="${2:?missing PREMIUM_URL}"
ULTRA_URL="${3:?missing ULTRA_URL}"
VPS_TARGET="${4:?missing VPS_SSH_TARGET (vd: user@vps.host)}"
REMOTE_PATH="${5:-/var/www/pthaicapital.io.vn/public/mcp}"

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LANDING_DIR="$REPO_ROOT/landing"
INDEX_HTML="$LANDING_DIR/index.html"

echo "==> Verify each URL looks like Lemon Squeezy checkout"
for url in "$PRO_URL" "$PREMIUM_URL" "$ULTRA_URL"; do
  case "$url" in
    https://*lemonsqueezy.com/buy/*|https://*lemonsqueezy.com/checkout/*)
      ;;
    *)
      echo "WARN: '$url' không match dạng LS checkout URL chuẩn."
      echo "      Vẫn tiếp tục — bạn confirm là URL đúng?"
      ;;
  esac
done

echo "==> Backup landing/index.html → index.html.bak"
cp "$INDEX_HTML" "$INDEX_HTML.bak"

echo "==> Replace placeholder checkout URLs in landing"
# Use a delimiter unlikely to appear in URLs
sed -i "s|href=\"#pro-checkout\"|href=\"$PRO_URL\"|g"         "$INDEX_HTML"
sed -i "s|href=\"#premium-checkout\"|href=\"$PREMIUM_URL\"|g" "$INDEX_HTML"
sed -i "s|href=\"#ultra-checkout\"|href=\"$ULTRA_URL\"|g"     "$INDEX_HTML"

echo "==> Verify no placeholders left"
remaining=$(grep -cE 'href="#(pro|premium|ultra)-checkout"' "$INDEX_HTML" || true)
if [[ "$remaining" != "0" ]]; then
  echo "ERROR: vẫn còn placeholder chưa replace. Aborting (đã restore từ .bak)"
  mv "$INDEX_HTML.bak" "$INDEX_HTML"
  exit 1
fi
echo "    ✓ all 3 checkout URLs written"

echo "==> Deploy landing files to $VPS_TARGET:$REMOTE_PATH"
# Use scp for max compatibility. -p preserves mtime.
scp -p "$LANDING_DIR/index.html" "$LANDING_DIR/styles.css" "$LANDING_DIR/script.js" \
    "$VPS_TARGET:$REMOTE_PATH/" || {
  echo "ERROR: scp deploy fail. Backup landing tại $INDEX_HTML.bak — restore nếu cần."
  exit 2
}

echo "==> Verify deployed version (curl)"
# Wait briefly for VPS cache
sleep 2
deployed=$(curl -sL https://pthaicapital.io.vn/mcp/ 2>&1)

# Check v4.1 markers
checks_passed=0
checks_total=4

if echo "$deployed" | grep -q "pip install gold-mcp"; then
  echo "    ✓ v4.1 PyPI install instructions present"
  ((checks_passed++)) || true
else
  echo "    ✗ MISSING: 'pip install gold-mcp' marker"
fi

if echo "$deployed" | grep -q "$PRO_URL"; then
  echo "    ✓ Pro checkout URL deployed"
  ((checks_passed++)) || true
else
  echo "    ✗ MISSING: Pro checkout URL"
fi

if echo "$deployed" | grep -q "$PREMIUM_URL"; then
  echo "    ✓ Premium checkout URL deployed"
  ((checks_passed++)) || true
else
  echo "    ✗ MISSING: Premium checkout URL"
fi

if echo "$deployed" | grep -q "$ULTRA_URL"; then
  echo "    ✓ Ultra checkout URL deployed"
  ((checks_passed++)) || true
else
  echo "    ✗ MISSING: Ultra checkout URL"
fi

echo "==> Summary: $checks_passed/$checks_total verification checks passed"

if [[ "$checks_passed" == "$checks_total" ]]; then
  echo ""
  echo "✓ Go-live deploy DONE. https://pthaicapital.io.vn/mcp live with v4.1 + paid tier URLs."
  echo ""
  echo "Next: open GO_LIVE_PROMO.md and post to X / r/algotrading / MCP Discord / Show HN."
  rm "$INDEX_HTML.bak"
else
  echo ""
  echo "WARN: $((checks_total - checks_passed)) check fail. Kiểm tra VPS cache hoặc nginx reload."
  echo "Backup: $INDEX_HTML.bak (restore: mv \"$INDEX_HTML.bak\" \"$INDEX_HTML\")"
fi
