#!/usr/bin/env bash
# Launch TheVirtualBrain container with the correct port mapping.
#
# IMPORTANT: TVB web UI listens on port 8080 inside the container, NOT
# 8888 as the foundation doc says. Host port 8888 -> container 8080.
# TVB takes ~30 seconds to fully start; the web UI is at
# http://localhost:8888/ once it's up.
#
# Usage:
#   ./scripts/run_tvb.sh        # start (background)
#   ./scripts/run_tvb.sh stop   # stop and remove
#   ./scripts/run_tvb.sh logs   # tail container logs

set -euo pipefail

NAME="tvb"
HOST_PORT="${TVB_HOST_PORT:-8888}"
IMAGE="thevirtualbrain/tvb-run:latest"

case "${1:-start}" in
  start)
    if docker ps -a --format '{{.Names}}' | grep -q "^${NAME}$"; then
      echo "Container ${NAME} already exists. Use './scripts/run_tvb.sh stop' first."
      exit 1
    fi
    docker run -d --name "${NAME}" -p "${HOST_PORT}:8080" "${IMAGE}"
    echo "Started ${NAME}. Wait ~30 seconds, then open http://localhost:${HOST_PORT}/"
    ;;
  stop)
    docker stop "${NAME}" >/dev/null 2>&1 || true
    docker rm "${NAME}" >/dev/null 2>&1 || true
    echo "Stopped and removed ${NAME}."
    ;;
  logs)
    docker logs -f "${NAME}"
    ;;
  *)
    echo "Usage: $0 [start|stop|logs]"
    exit 1
    ;;
esac
