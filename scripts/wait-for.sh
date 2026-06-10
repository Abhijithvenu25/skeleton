#!/bin/bash
# Wait for postgres + redis to become healthy before running alembic / dev commands.

set -euo pipefail

echo "Waiting for PostgreSQL..."
until pg_isready -h "${POSTGRES_HOST:-postgres}" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER:-app}"; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 1
done
echo "PostgreSQL is up"

echo "Waiting for Redis..."
until redis-cli -h "${REDIS_HOST:-redis}" -p "${REDIS_PORT:-6379}" ping | grep -q PONG; do
    echo "Redis is unavailable - sleeping"
    sleep 1
done
echo "Redis is up"

"$@"