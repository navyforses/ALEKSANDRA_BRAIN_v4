#!/usr/bin/env python3
"""ALEKSANDRA_BRAIN v7.0 Foundation Prerequisites Verifier.

Source plan: v7_architecture/00_FOUNDATION_PREREQUISITES.md
Run with the v7 venv: .venv-v7/Scripts/python.exe scripts/verify_v7_foundation.py

Exit 0 only when 25/25 PASS. Failures are printed with the exact fix command.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
VIEWER_PKG = ROOT / "viewer" / "package.json"
VENV_V7 = ROOT / ".venv-v7"
MODELS_DIR = Path(os.path.expanduser("~/models"))


def _load_env() -> None:
    """Parse .env without requiring python-dotenv (the venv may not be active)."""
    if not ENV_PATH.exists():
        return
    for raw in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _which(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _bin_version(cmd: list[str], min_major: int) -> bool:
    try:
        out = subprocess.check_output(
            cmd, text=True, stderr=subprocess.STDOUT, timeout=10
        )
        digits = "".join(c if c.isdigit() else " " for c in out).split()
        return bool(digits) and int(digits[0]) >= min_major
    except Exception:
        return False


def _docker_daemon_alive() -> bool:
    try:
        r = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return r.returncode == 0 and bool(r.stdout.strip())
    except Exception:
        return False


def _venv_python() -> Path:
    return (
        VENV_V7 / "Scripts" / "python.exe"
        if os.name == "nt"
        else VENV_V7 / "bin" / "python"
    )


def _venv_has(module: str) -> bool:
    py = _venv_python()
    if not py.exists():
        return False
    try:
        r = subprocess.run(
            [str(py), "-c", f"import {module}"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return r.returncode == 0
    except Exception:
        return False


def _docker_image_present(name: str) -> bool:
    try:
        r = subprocess.run(
            ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}", name],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return r.returncode == 0 and name.split(":")[0] in r.stdout
    except Exception:
        return False


def _viewer_has(pkg: str) -> bool:
    if not VIEWER_PKG.exists():
        return False
    try:
        data = json.loads(VIEWER_PKG.read_text(encoding="utf-8"))
        return pkg in (data.get("dependencies") or {}) or pkg in (
            data.get("devDependencies") or {}
        )
    except Exception:
        return False


def _env_nonempty(var: str) -> bool:
    return bool(os.environ.get(var, "").strip())


def _model_present(folder: str, min_mb: int = 100) -> bool:
    d = MODELS_DIR / folder
    if not d.is_dir():
        return False
    total = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
    return total >= min_mb * 1024 * 1024


# ---------------------------------------------------------------------------
# The 25 checks
# ---------------------------------------------------------------------------
CHECKS: list[tuple[str, Callable[[], bool], str]] = [
    # --- Toolchain (8) ---
    (
        "python_3_12_plus",
        lambda: sys.version_info >= (3, 12),
        "Install Python >= 3.12 from python.org",
    ),
    (
        "node_20_plus",
        lambda: _bin_version(["node", "--version"], 20),
        "Install Node.js >= 20 from nodejs.org",
    ),
    (
        "docker_daemon_running",
        _docker_daemon_alive,
        "Start Docker Desktop (Engine running)",
    ),
    (
        "uv_installed",
        lambda: _which("uv"),
        "Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh",
    ),
    ("git_installed", lambda: _which("git"), "Install git from git-scm.com"),
    ("gh_installed", lambda: _which("gh"), "Install gh from cli.github.com"),
    (
        "hf_cli_installed",
        lambda: (VENV_V7 / "Scripts" / "hf.exe").exists() or _which("hf"),
        "hf comes with huggingface-hub in requirements-v7.txt",
    ),
    (
        "venv_v7_exists",
        lambda: _venv_python().exists(),
        "uv venv .venv-v7 --python 3.12",
    ),
    # --- Python imports (8) ---
    (
        "pymc_importable",
        lambda: _venv_has("pymc"),
        "uv pip install --python .venv-v7/Scripts/python.exe pymc",
    ),
    (
        "numpyro_importable",
        lambda: _venv_has("numpyro"),
        "uv pip install --python .venv-v7/Scripts/python.exe numpyro",
    ),
    (
        "jax_importable",
        lambda: _venv_has("jax"),
        "uv pip install --python .venv-v7/Scripts/python.exe 'jax[cpu]'",
    ),
    (
        "arviz_importable",
        lambda: _venv_has("arviz"),
        "uv pip install --python .venv-v7/Scripts/python.exe arviz",
    ),
    (
        "dowhy_importable",
        lambda: _venv_has("dowhy"),
        "uv pip install --python .venv-v7/Scripts/python.exe dowhy",
    ),
    (
        "econml_importable",
        lambda: _venv_has("econml"),
        "uv pip install --python .venv-v7/Scripts/python.exe econml",
    ),
    (
        "transformers_importable",
        lambda: _venv_has("transformers"),
        "uv pip install --python .venv-v7/Scripts/python.exe transformers",
    ),
    (
        "anthropic_importable",
        lambda: _venv_has("anthropic"),
        "uv pip install --python .venv-v7/Scripts/python.exe anthropic",
    ),
    # --- Secrets / env (4) ---
    (
        "anthropic_key_set",
        lambda: _env_nonempty("ANTHROPIC_API_KEY"),
        "Add ANTHROPIC_API_KEY=sk-ant-... to .env",
    ),
    (
        "gemini_key_set",
        lambda: _env_nonempty("GEMINI_API_KEY"),
        "Get key at https://aistudio.google.com and add GEMINI_API_KEY=AIzaSy... to .env",
    ),
    (
        "hf_token_set",
        lambda: _env_nonempty("HF_TOKEN"),
        "Get token at https://huggingface.co/settings/tokens and add HF_TOKEN=hf_... to .env",
    ),
    (
        "supabase_url_set",
        lambda: _env_nonempty("SUPABASE_URL"),
        "Carry SUPABASE_URL forward from v6.0 .env",
    ),
    # --- Models / Docker / Frontend (5) ---
    (
        "tvb_image_pulled",
        lambda: _docker_image_present("thevirtualbrain/tvb-run"),
        "docker pull thevirtualbrain/tvb-run:latest",
    ),
    (
        "medgemma_4b_downloaded",
        lambda: _model_present("medgemma-4b", 1000),
        "hf download google/medgemma-4b-it --local-dir ~/models/medgemma-4b",
    ),
    (
        "txgemma_9b_downloaded",
        lambda: _model_present("txgemma-9b", 1000),
        "hf download google/txgemma-9b-chat --local-dir ~/models/txgemma-9b",
    ),
    (
        "medsiglip_downloaded",
        lambda: _model_present("medsiglip", 500),
        "hf download google/medsiglip-448 --local-dir ~/models/medsiglip",
    ),
    (
        "plotly_in_viewer",
        lambda: _viewer_has("plotly.js-dist-min"),
        "cd viewer && npm install plotly.js-dist-min react-plotly.js vis-network vis-data @xyflow/react",
    ),
]


def main() -> int:
    _load_env()

    print("=" * 70)
    print(" ALEKSANDRA_BRAIN v7.0 Foundation Verifier")
    print(f" Root: {ROOT}")
    print("=" * 70)

    passed: list[str] = []
    failed: list[tuple[str, str]] = []

    for name, fn, fix in CHECKS:
        try:
            ok = bool(fn())
        except Exception as exc:
            ok = False
            fix = f"{fix} (raised {type(exc).__name__}: {exc})"
        marker = "PASS" if ok else "FAIL"
        print(f"  [{marker}] {name}")
        (passed if ok else failed).append(name if ok else (name, fix))

    print("-" * 70)
    total = len(CHECKS)
    print(f" Result: {len(passed)}/{total} PASS")
    if failed:
        print("\n Failures and fixes:")
        for name, fix in failed:
            print(f"   - {name}")
            print(f"       fix: {fix}")
    print("=" * 70)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
