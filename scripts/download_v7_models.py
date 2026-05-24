#!/usr/bin/env python3
"""Download v7.0 AI models from Hugging Face after HF_TOKEN is set.

Models: MedGemma 4B (~8 GB), TxGemma 9B (~18 GB), MedSigLIP (~2 GB).
Total ~28 GB. Requires HF_TOKEN in .env AND license acceptance per model:
  - https://huggingface.co/google/medgemma-4b-it       (gated)
  - https://huggingface.co/google/txgemma-9b-chat      (gated)
  - https://huggingface.co/google/medsiglip-448        (gated)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
MODELS_DIR = Path(os.path.expanduser("~/models"))

MODELS = [
    ("google/medgemma-4b-it", "medgemma-4b", 8.0),
    ("google/txgemma-9b-chat", "txgemma-9b", 18.0),
    ("google/medsiglip-448", "medsiglip", 2.0),
]


def _load_env() -> None:
    if not ENV_PATH.exists():
        return
    for raw in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def main() -> int:
    _load_env()
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        print("HF_TOKEN missing. Add to .env first.", file=sys.stderr)
        return 2

    try:
        from huggingface_hub import snapshot_download
        from huggingface_hub.utils import GatedRepoError, RepositoryNotFoundError
    except ImportError:
        print("huggingface_hub not installed in current Python.", file=sys.stderr)
        print(
            "Run with: .venv-v7/Scripts/python.exe scripts/download_v7_models.py",
            file=sys.stderr,
        )
        return 2

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    failures: list[tuple[str, str]] = []

    for repo_id, subdir, size_gb in MODELS:
        target = MODELS_DIR / subdir
        print(f"\n=== {repo_id} ({size_gb:.1f} GB) → {target} ===")
        try:
            snapshot_download(
                repo_id=repo_id,
                local_dir=str(target),
                token=token,
                local_dir_use_symlinks=False,
                resume_download=True,
            )
            print(f"  OK  {repo_id}")
        except GatedRepoError:
            msg = f"License not accepted. Visit https://huggingface.co/{repo_id} and click Accept."
            print(f"  FAIL  {msg}", file=sys.stderr)
            failures.append((repo_id, msg))
        except RepositoryNotFoundError as exc:
            msg = f"Repo missing or token lacks access: {exc}"
            print(f"  FAIL  {msg}", file=sys.stderr)
            failures.append((repo_id, msg))
        except Exception as exc:
            msg = f"{type(exc).__name__}: {exc}"
            print(f"  FAIL  {msg}", file=sys.stderr)
            failures.append((repo_id, msg))

    print("\n" + "=" * 60)
    print(f" Downloaded: {len(MODELS) - len(failures)}/{len(MODELS)}")
    if failures:
        for r, m in failures:
            print(f"  - {r}: {m}")
    print("=" * 60)
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
