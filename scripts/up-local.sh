#!/bin/bash
# Bring the stack up with local-only env vars. Avoids docker compose auto-loading
# a project-root .env (which previously leaked remote creds into local Postgres).
#
# Usage:
#   ./scripts/up-local.sh up        # start
#   ./scripts/up-local.sh down      # stop
#   ./scripts/up-local.sh logs -f   # tail logs
#   ./scripts/up-local.sh ps         # list services
# Any docker compose args are forwarded.

set -euo pipefail

# Local Postgres — must match app/core/config.py defaults and .env.local.
export POSTGRES_USER="${POSTGRES_USER:-postgres}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres}"
export POSTGRES_DB="${POSTGRES_DB:-kalisia}"
export POSTGRES_HOST="${POSTGRES_HOST:-postgres}"   # service name inside compose network
export POSTGRES_PORT="${POSTGRES_PORT:-5432}"

# Local Redis.
export REDIS_URL="${REDIS_URL:-redis://redis:6379/0}"

# App env. The Python app reads .env.local for the rest.
export APP_ENV="${APP_ENV:-local}"

cd "$(dirname "$0")/.."

exec docker compose "$@"