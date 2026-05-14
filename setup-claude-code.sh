#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
# ALEKSANDRA_BRAIN — Claude Code productivity setup (macOS/Linux)
# Run once, from repo root:
#   chmod +x setup-claude-code.sh && ./setup-claude-code.sh
# ═══════════════════════════════════════════════════════════
set -e

echo ""
echo "=== ALEKSANDRA_BRAIN — Claude Code setup ==="

# ─── 0. Prerequisites ────────────────────────────────────
echo ""
echo "[0/6] Checking prerequisites..."
for cmd in node npm python3 pip3 git; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "  ❌ Missing: $cmd"
    exit 1
  fi
done
echo "  ✅ Node, npm, python3, pip3, git all present"

# ─── 1. Claude Mem ───────────────────────────────────────
echo ""
echo "[1/6] Installing Claude Mem..."
npm install -g claude-mem || echo "  ⚠️  npm install failed, try with sudo"
claude-mem init || true
echo "  ✅ Claude Mem"

# ─── 2. Caveman (Full mode) ──────────────────────────────
echo ""
echo "[2/6] Installing Caveman..."
mkdir -p .claude/skills
if [ -d ".claude/skills/caveman" ]; then
  (cd .claude/skills/caveman && git pull)
else
  git clone https://github.com/JuliusBrussee/caveman.git .claude/skills/caveman
fi
echo "  ✅ Caveman (Full mode)"

# ─── 3. GSD ──────────────────────────────────────────────
echo ""
echo "[3/6] Installing GSD..."
if [ -d ".claude/skills/get-shit-done" ]; then
  (cd .claude/skills/get-shit-done && git pull)
else
  git clone https://github.com/gsd-build/get-shit-done.git .claude/skills/get-shit-done
fi
echo "  ✅ GSD"

# ─── 4. Graphify ─────────────────────────────────────────
echo ""
echo "[4/6] Installing Graphify..."
pip3 install --upgrade graphify-ai || true
graphify index . || true
echo "  ✅ Graphify"

# ─── 5. Code Review Graph ────────────────────────────────
echo ""
echo "[5/6] Installing Code Review Graph..."
pip3 install --upgrade code-review-graph || true
code-review-graph build . || true
echo "  ✅ Code Review Graph"

# ─── 6. Summary ──────────────────────────────────────────
echo ""
echo "[6/6] Done."
echo ""
echo "✅ Open this folder in Claude Code and move to PHASE_0_HANDOUT.md §1.1"
