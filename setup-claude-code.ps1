# ═══════════════════════════════════════════════════════════
# ALEKSANDRA_BRAIN — Claude Code productivity setup (Windows)
# Run once, from repo root, in PowerShell:
#   ./setup-claude-code.ps1
#
# Installs 5 tools (CLAUDE.md is already in repo root):
#   1. Claude Mem        — npx installer (memory across sessions)
#   2. GSD               — npx installer (spec-driven workflow skill)
#   3. Spec Kit          — uv tool install (GitHub official, /speckit.* commands)
#   4. Caveman           — irm | iex installer (token-economy skill)
#   5. Code Review Graph — pip + platform install (persistent codebase MCP)
#
# Verified 2026-05-13 against actual GitHub repos:
#   - thedotmack/claude-mem v13.2.0
#   - gsd-build/get-shit-done v1.41.2
#   - github/spec-kit
#   - JuliusBrussee/caveman v1.8.2
#   - tirth8205/code-review-graph v2.3.3
# ═══════════════════════════════════════════════════════════

$ErrorActionPreference = "Stop"
Write-Host "`n=== ALEKSANDRA_BRAIN — Claude Code setup ===" -ForegroundColor Cyan

# UTF-8 for Python tools on Windows (avoids cp1252 encoding errors)
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

# ─── 0. Prerequisites check ──────────────────────────────
Write-Host "`n[0/6] Checking prerequisites..." -ForegroundColor Yellow
$tools = @{ "node" = "Node.js (>=18)"; "npm" = "npm"; "npx" = "npx"; "pip" = "pip"; "uv" = "uv (Astral)"; "git" = "Git" }
$missing = @()
foreach ($cmd in $tools.Keys) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        $missing += $tools[$cmd]
    }
}
if ($missing.Count -gt 0) {
    Write-Host "Missing tools: $($missing -join ', ')" -ForegroundColor Red
    Write-Host "Install hints:" -ForegroundColor Yellow
    Write-Host "  Node.js  : winget install OpenJS.NodeJS.LTS" -ForegroundColor Yellow
    Write-Host "  uv       : powershell -c `"irm https://astral.sh/uv/install.ps1 | iex`"" -ForegroundColor Yellow
    Write-Host "  Python   : winget install Python.Python.3.12" -ForegroundColor Yellow
    Write-Host "  Git      : winget install Git.Git" -ForegroundColor Yellow
    exit 1
}
Write-Host "  Node, npm, npx, pip, uv, git all present" -ForegroundColor Green

# ─── 1. Claude Mem (sessions memory) ─────────────────────
Write-Host "`n[1/6] Installing Claude Mem (memory across sessions)..." -ForegroundColor Yellow
try {
    npx -y claude-mem@latest install
    Write-Host "  Claude Mem installed" -ForegroundColor Green
} catch {
    Write-Host "  Claude Mem failed: $_" -ForegroundColor Yellow
    Write-Host "  Manual: npx claude-mem install" -ForegroundColor Yellow
}

# ─── 2. GSD (Get Shit Done — spec-driven workflow) ───────
Write-Host "`n[2/6] Installing GSD skill..." -ForegroundColor Yellow
try {
    npx -y get-shit-done-cc@latest
    Write-Host "  GSD installed" -ForegroundColor Green
} catch {
    Write-Host "  GSD failed: $_" -ForegroundColor Yellow
    Write-Host "  Manual: npx get-shit-done-cc@latest" -ForegroundColor Yellow
}

# ─── 3. Spec Kit (GitHub official) ───────────────────────
Write-Host "`n[3/6] Installing GitHub Spec Kit..." -ForegroundColor Yellow
try {
    uv tool install specify-cli --from git+https://github.com/github/spec-kit.git
    Write-Host "  Spec Kit installed (use: specify init <project>)" -ForegroundColor Green
} catch {
    Write-Host "  Spec Kit failed: $_" -ForegroundColor Yellow
    Write-Host "  Manual: uv tool install specify-cli --from git+https://github.com/github/spec-kit.git" -ForegroundColor Yellow
}

# ─── 4. Caveman (token economy) ──────────────────────────
Write-Host "`n[4/6] Installing Caveman skill..." -ForegroundColor Yellow
try {
    irm https://raw.githubusercontent.com/JuliusBrussee/caveman/main/install.ps1 | iex
    Write-Host "  Caveman installed" -ForegroundColor Green
} catch {
    Write-Host "  Caveman failed: $_" -ForegroundColor Yellow
    Write-Host "  Manual: irm https://raw.githubusercontent.com/JuliusBrussee/caveman/main/install.ps1 | iex" -ForegroundColor Yellow
}

# ─── 5. Code Review Graph MCP ────────────────────────────
Write-Host "`n[5/6] Installing Code Review Graph (MCP server)..." -ForegroundColor Yellow
try {
    pip install --upgrade code-review-graph
    # Ensure Python Scripts dir is on PATH for current session
    $pyScripts = (& py -3 -c "import sysconfig; print(sysconfig.get_path('scripts'))").Trim()
    if ($env:Path -notlike "*$pyScripts*") { $env:Path += ";$pyScripts" }
    code-review-graph install --platform claude-code
    code-review-graph build
    Write-Host "  Code Review Graph installed and initial graph built" -ForegroundColor Green
} catch {
    Write-Host "  Code Review Graph failed: $_" -ForegroundColor Yellow
    Write-Host "  Manual: pip install code-review-graph; code-review-graph install --platform claude-code; code-review-graph build" -ForegroundColor Yellow
}

# ─── 6. Summary ──────────────────────────────────────────
Write-Host "`n[6/6] Summary" -ForegroundColor Yellow
Write-Host @"

Setup attempted. What is active now:
  - CLAUDE.md           -> already in repo root (Claude Code reads automatically)
  - Claude Mem          -> ~/.claude-mem/ (memory worker: 'npx claude-mem start')
  - GSD                 -> ~/.claude/skills/gsd-*/
  - Spec Kit            -> 'specify' CLI; commands: /speckit.specify, /speckit.plan, /speckit.tasks, /speckit.implement
  - Caveman             -> ~/.claude-plugin or skills dir (auto-activates)
  - Code Review Graph   -> MCP via uvx, scoped to project via .mcp.json

Verify:
  - Restart Claude Code (close + reopen) so new skills + MCP register
  - In Claude Code:  /skills           -> should list gsd, caveman
  - In Claude Code:  /mcp              -> should list code-review-graph

Next:
  - Use /speckit.specify or /gsd to scaffold the first feature
  - Move to PHASE_0_HANDOUT.md for Supabase + n8n + CrewAI setup

If any step warned, run that single command manually and re-check.
"@ -ForegroundColor Green
