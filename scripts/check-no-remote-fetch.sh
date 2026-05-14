#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# check-no-remote-fetch.sh — FND-02
#
# Fails if anything under viewer/ adds a remote fetch / axios / XHR call to
# an external origin. MRI data must never leave the browser; the viewer is
# allowed to call its own /api/* routes and localhost (dev) only.
#
# Run via pre-commit or GitHub Actions (see .github/workflows/trust-boundary.yml).
# ---------------------------------------------------------------------------
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -d viewer ]] || [[ -z "$(find viewer -maxdepth 3 -name '*.ts' -o -name '*.tsx' 2>/dev/null | head -n 1)" ]]; then
  echo "OK — viewer/ has no TS/TSX yet, nothing to check."
  exit 0
fi

# Network call shapes we ban
PATTERNS='(fetch\(|axios\.(get|post|put|delete|patch|head)|axios\(|new\s+XMLHttpRequest|navigator\.sendBeacon|EventSource\()'

# Allowed targets: self-relative, /api/*, localhost, 127.0.0.1, blob:, data:
violations=$(grep -RInE "$PATTERNS" viewer --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" 2>/dev/null \
  | grep -vE "(['\"]/api/|['\"]/[a-zA-Z]|['\"]\.\./|localhost|127\.0\.0\.1|blob:|data:|/\* allow-remote \*/)" \
  || true)

if [[ -n "$violations" ]]; then
  echo "FAIL — remote network call detected in viewer/ (FND-02):"
  echo "----------------------------------------------------------------"
  echo "$violations"
  echo "----------------------------------------------------------------"
  echo ""
  echo "MRI / DICOM / NIfTI must stay in the browser."
  echo "If this call is truly necessary and PHI-free, append the marker:"
  echo "    /* allow-remote */"
  echo "on the same line, and add a justification line above."
  exit 1
fi

echo "OK — no remote network calls in viewer/"
