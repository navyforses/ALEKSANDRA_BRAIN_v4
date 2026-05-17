"""
perception_worker.py — Phase 2.5B HTTP wrapper around perception_tick.

Exposes `POST /perception-tick` so the n8n `perception_6h` workflow (in
workflows/perception_6h.json) can fire the perception pipeline on a 6-hour
cron via the Railway-hosted worker URL stored in `$env.PERCEPTION_WORKER_URL`.

Single endpoint, single function call. Wrapping is intentionally thin: the
heavy lifting lives in `scripts.perception_tick.run`, which already writes a
`runs` row + posts a Telegram summary. This wrapper adds two things:

  1. HTTP transport (stdlib http.server — no new deps, ~80 LOC). FastAPI
     would be the obvious choice but adds ~30 MB and a version-pinning
     headache for a one-endpoint service. Stdlib is the right Pareto here.
  2. Defence-in-depth budget gate — calls `check_daily_budget()` before
     invoking the pipeline so a runaway day cannot kick off a new tick
     (HC-2 + HC-4 per the Phase 2.5 plan).

Other endpoints intentionally absent:
  - /healthz — Railway's built-in healthcheck just probes TCP; no JSON
    endpoint needed.
  - /metrics — Phase 4 if at all; runs table is already the audit ledger.

Run locally (smoke test before Railway deploy):
    .venv/Scripts/python.exe -X utf8 -m scripts.perception_worker
    # then in another shell:
    curl -X POST http://127.0.0.1:8000/perception-tick \
         -H "Content-Type: application/json" \
         -d '{"small": true, "no_telegram": true}'

Deploy on Railway:
  - Service entry command: python -m scripts.perception_worker
  - Port: bound by $PORT env var (Railway convention); falls back to 8000.
  - Env vars required (Railway → Variables): ANTHROPIC_API_KEY,
    SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_DB_URL,
    NEO4J_URI/USERNAME/PASSWORD, QDRANT_URL, NCBI_EMAIL,
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, DAILY_BUDGET_USD (optional).
"""

from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from scripts.cognition.budget import BudgetExceeded, check_daily_budget
from scripts.ledger import load_env

LOG = logging.getLogger("perception_worker")
DEFAULT_PORT = 8000


def _json_response(
    handler: BaseHTTPRequestHandler, status: int, body: dict[str, Any]
) -> None:
    payload = json.dumps(body, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


class _Handler(BaseHTTPRequestHandler):
    # Quiet the default request logger — we already log structured events.
    def log_message(self, fmt: str, *args: Any) -> None:
        LOG.info("%s - %s", self.address_string(), fmt % args)

    def do_GET(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler API)
        if self.path == "/" or self.path == "/healthz":
            _json_response(self, 200, {"status": "ok", "service": "perception_worker"})
            return
        _json_response(self, 404, {"error": "not_found", "path": self.path})

    def do_POST(self) -> None:  # noqa: N802
        # Four POST endpoints. The first three sit behind a budget gate
        # because they trigger LLM-using pipelines. The fourth
        # (/daily-spend-report) is LLM-free and runs even when the budget
        # is exhausted — visibility into spend is most valuable when
        # spend is high.
        if self.path not in (
            "/perception-tick",
            "/chunking-tick",
            "/extraction-tick",
            "/daily-spend-report",
        ):
            _json_response(self, 404, {"error": "not_found", "path": self.path})
            return

        body = self._parse_body()
        if body is None:
            return  # already responded with 400

        if self.path == "/daily-spend-report":
            # No budget gate. Pure SQL aggregation + Telegram send.
            self._handle_daily_spend_report(body)
            return

        # Defence-in-depth budget gate (HC-2/HC-4) BEFORE any pipeline.
        try:
            today_spend, over = check_daily_budget(threshold_usd=12.0)
        except Exception as e:
            LOG.exception("budget check failed open")
            today_spend, over = 0.0, False
            _ = e
        if over:
            _json_response(
                self,
                429,
                {
                    "error": "budget_exceeded",
                    "today_spend_usd": today_spend,
                    "cap_usd": 12.0,
                },
            )
            return

        if self.path == "/perception-tick":
            self._handle_perception(body)
        elif self.path == "/chunking-tick":
            self._handle_chunking(body)
        elif self.path == "/extraction-tick":
            self._handle_extraction(body)

    def _parse_body(self) -> dict[str, Any] | None:
        body: dict[str, Any] = {}
        length = int(self.headers.get("Content-Length") or 0)
        if length > 0:
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
                if not isinstance(body, dict):
                    raise ValueError("body must be a JSON object")
            except (json.JSONDecodeError, ValueError) as e:
                _json_response(self, 400, {"error": "bad_json", "detail": str(e)})
                return None
        return body

    def _handle_perception(self, body: dict[str, Any]) -> None:
        small = bool(body.get("small", False))
        no_telegram = bool(body.get("no_telegram", False))
        try:
            from scripts import perception_tick  # noqa: PLC0415
        except Exception as e:
            LOG.exception("perception_tick import failed")
            _json_response(
                self,
                500,
                {"error": "import_failed", "detail": f"{type(e).__name__}: {e}"},
            )
            return
        if no_telegram:
            perception_tick._telegram = lambda _msg: None  # type: ignore[attr-defined]
        try:
            result = perception_tick.run(small=small)
        except BudgetExceeded as e:
            _json_response(
                self,
                429,
                {
                    "error": "budget_exceeded",
                    "today_spend_usd": e.today_spend_usd,
                    "cap_usd": e.threshold_usd,
                },
            )
            return
        except Exception as e:
            LOG.exception("perception_tick.run raised")
            _json_response(
                self,
                500,
                {
                    "error": "perception_failed",
                    "detail": f"{type(e).__name__}: {e}",
                    "trace": traceback.format_exc(limit=5),
                },
            )
            return
        _json_response(self, 200, result)

    def _handle_chunking(self, body: dict[str, Any]) -> None:
        limit = int(body.get("limit", 0)) or 0
        only_papers = bool(body.get("only_papers", False))
        score = bool(body.get("score", True))
        try:
            from scripts.chunking.process_ledger import run as chunk_run  # noqa: PLC0415

            result = chunk_run(limit=limit, only_papers=only_papers, score=score)
        except BudgetExceeded as e:
            _json_response(
                self,
                429,
                {
                    "error": "budget_exceeded",
                    "today_spend_usd": e.today_spend_usd,
                    "cap_usd": e.threshold_usd,
                },
            )
            return
        except Exception as e:
            LOG.exception("process_ledger.run raised")
            _json_response(
                self,
                500,
                {
                    "error": "chunking_failed",
                    "detail": f"{type(e).__name__}: {e}",
                    "trace": traceback.format_exc(limit=5),
                },
            )
            return
        _json_response(self, 200, result)

    def _handle_daily_spend_report(self, body: dict[str, Any]) -> None:
        """Phase 4 OBS-03. Aggregate prior 24h spend, send Telegram, audit."""
        dry_run = bool(body.get("dry_run", False))
        try:
            from scripts.observer.daily_spend_report import run as spend_run  # noqa: PLC0415

            result = spend_run(dry_run=dry_run)
        except Exception as e:
            LOG.exception("daily_spend_report.run raised")
            _json_response(
                self,
                500,
                {
                    "error": "daily_spend_report_failed",
                    "detail": f"{type(e).__name__}: {e}",
                    "trace": traceback.format_exc(limit=5),
                },
            )
            return
        _json_response(self, 200, result)

    def _handle_extraction(self, body: dict[str, Any]) -> None:
        import asyncio  # noqa: PLC0415

        force = bool(body.get("force", False))
        limit = body.get("limit")
        if limit is not None:
            limit = int(limit)
        try:
            from scripts.extraction.batch_ingest import run_batch  # noqa: PLC0415

            result = asyncio.run(run_batch(force=force, limit=limit))
        except BudgetExceeded as e:
            _json_response(
                self,
                429,
                {
                    "error": "budget_exceeded",
                    "today_spend_usd": e.today_spend_usd,
                    "cap_usd": e.threshold_usd,
                },
            )
            return
        except Exception as e:
            LOG.exception("batch_ingest.run_batch raised")
            _json_response(
                self,
                500,
                {
                    "error": "extraction_failed",
                    "detail": f"{type(e).__name__}: {e}",
                    "trace": traceback.format_exc(limit=5),
                },
            )
            return
        _json_response(self, 200, result)


def serve(host: str = "0.0.0.0", port: int | None = None) -> None:
    load_env()
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    bind_port = port if port is not None else int(os.environ.get("PORT", DEFAULT_PORT))
    server = ThreadingHTTPServer((host, bind_port), _Handler)
    LOG.info("perception_worker listening on http://%s:%d", host, bind_port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOG.info("shutting down")
    finally:
        server.server_close()


if __name__ == "__main__":
    sys.exit(serve())
