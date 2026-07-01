# kalisia-backend

Production-ready FastAPI backend with JWT auth, PostgreSQL, and Redis.

## Stack

- FastAPI 0.115 (async) on Python 3.12
- SQLAlchemy 2.0 + asyncpg + Alembic
- PostgreSQL 16
- Redis 7 (refresh-token store + rate limiting)
- PyJWT (HS256 access + refresh)
- passlib bcrypt
- structlog (JSON logs)
- uv for dependency management
- ruff + mypy + pytest
- Multi-stage Docker image, docker-compose orchestration

## Quickstart (Docker)

```bash
# 1. Configure env
cp .env.example .env

# 2. Bring up the stack (app waits for pg/redis to be healthy, then auto-migrates)
make up

# 3. Smoke test
curl http://localhost:8000/api/v1/health/healthz
curl http://localhost:8000/api/v1/health/readyz
```

## Running locally without Docker

Use this path if you want to iterate on the API without the Docker overhead.
You'll need Python 3.12, a local PostgreSQL instance, and a local Redis instance
running on the defaults the app expects.

### 1. Prerequisites

- Python 3.12 (matches `.python-version`)
- PostgreSQL 16 reachable on `localhost:5432`
- Redis 7 reachable on `localhost:6379`
- [uv](https://docs.astral.sh/uv/) for dependency management

### 2. Create the database

```bash
createdb kalisia_develop
```

### 3. Configure env

```bash
cp .env.example .env
```

Then edit `.env` so the local values point at your local services, e.g.:

```dotenv
APP_ENV=local
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=kalisia_develop
POSTGRES_SSL=disable
REDIS_URL=redis://localhost:6379/0
```

Keep `POSTGRES_SSL=disable` for a plain local Postgres; use `require` only for
managed databases like Neon.

### 4. Install dependencies

```bash
uv sync --all-extras
```

This creates `.venv/` and installs the app + dev tooling.

### 5. Run migrations

```bash
uv run alembic upgrade head
```

### 6. Start the API

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

`--reload` watches `app/` and restarts on save.

### 8. Smoke test

```bash
curl http://localhost:8000/api/v1/health/healthz
curl http://localhost:8000/api/v1/health/readyz
```

Both should return `{"status":"ok"}`. `/readyz` will report `degraded` if the
DB or Redis check fails — check the connection settings in `.env` if so.

### 9. Open the docs

- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc:      http://localhost:8000/api/v1/redoc

### Troubleshooting

- **`pydantic ... is not fully defined` on `/docs`** — every module that uses
  `from __future__ import annotations` must keep its type-only imports at
  module top level (not inside `if TYPE_CHECKING:`) so Pydantic's `TypeAdapter`
  can resolve them at schema-generation time.
- **`asyncpg ... SSL error`** — set `POSTGRES_SSL=disable` for plain local
  Postgres; the `require` value is only for managed providers.
- **Port already in use** — change the port: `uvicorn app.main:app --port 8001`.

## Endpoints

| Method | Path | Auth |
| --- | --- | --- |
| GET    | `/api/v1/healthz` | none |
| GET    | `/api/v1/readyz`  | none |
| POST   | `/api/v1/auth/register` | none (rate-limited) |
| POST   | `/api/v1/auth/login`    | none (rate-limited) |
| POST   | `/api/v1/auth/refresh`  | refresh JWT |
| POST   | `/api/v1/auth/logout`   | access JWT |
| GET    | `/api/v1/auth/me`       | access JWT |

### CRM

| Method | Path | Auth |
| --- | --- | --- |
| GET    | `/api/v1/roles`                  | access JWT |
| POST   | `/api/v1/roles`                  | access JWT |
| GET    | `/api/v1/roles/{id}`             | access JWT |
| PATCH  | `/api/v1/roles/{id}`             | access JWT |
| DELETE | `/api/v1/roles/{id}`             | access JWT |
| GET    | `/api/v1/staff-profiles`         | access JWT |
| POST   | `/api/v1/staff-profiles/{user_id}` | access JWT |
| GET    | `/api/v1/staff-profiles/{user_id}` | access JWT |
| PATCH  | `/api/v1/staff-profiles/{user_id}` | access JWT |
| DELETE | `/api/v1/staff-profiles/{user_id}` | access JWT |
| GET    | `/api/v1/companies`              | access JWT |
| POST   | `/api/v1/companies`              | access JWT |
| GET    | `/api/v1/companies/{id}`         | access JWT |
| PATCH  | `/api/v1/companies/{id}`         | access JWT |
| DELETE | `/api/v1/companies/{id}`         | access JWT |
| GET    | `/api/v1/contacts`               | access JWT |
| POST   | `/api/v1/contacts`               | access JWT |
| GET    | `/api/v1/contacts/{id}`          | access JWT |
| PATCH  | `/api/v1/contacts/{id}`          | access JWT |
| DELETE | `/api/v1/contacts/{id}`          | access JWT |
| GET    | `/api/v1/projects`               | access JWT |
| POST   | `/api/v1/projects`               | access JWT |
| GET    | `/api/v1/projects/{id}`          | access JWT |
| PATCH  | `/api/v1/projects/{id}`          | access JWT |
| DELETE | `/api/v1/projects/{id}`          | access JWT |
| GET    | `/api/v1/enquiries`              | access JWT |
| POST   | `/api/v1/enquiries`              | access JWT |
| GET    | `/api/v1/enquiries/{id}`         | access JWT |
| PATCH  | `/api/v1/enquiries/{id}`         | access JWT |
| DELETE | `/api/v1/enquiries/{id}`         | access JWT |
| POST   | `/api/v1/enquiries/{id}/mark-lost` | access JWT |
| GET    | `/api/v1/site-visits`            | access JWT |
| POST   | `/api/v1/site-visits`            | access JWT |
| GET    | `/api/v1/site-visits/{id}`       | access JWT |
| PATCH  | `/api/v1/site-visits/{id}`       | access JWT |
| DELETE | `/api/v1/site-visits/{id}`       | access JWT |
| GET    | `/api/v1/quotations`             | access JWT |
| POST   | `/api/v1/quotations`             | access JWT |
| GET    | `/api/v1/quotations/{id}`        | access JWT |
| PATCH  | `/api/v1/quotations/{id}`        | access JWT |
| DELETE | `/api/v1/quotations/{id}`        | access JWT |
| POST   | `/api/v1/quotations/{id}/versions` | access JWT |
| GET    | `/api/v1/quotations/{id}/versions` | access JWT |
| GET    | `/api/v1/quotation-line-items`   | access JWT |
| GET    | `/api/v1/quotation-line-items/by-version/{version_id}` | access JWT |
| GET    | `/api/v1/quotation-line-items/{id}` | access JWT |
| DELETE | `/api/v1/quotation-line-items/{id}` | access JWT |
| GET    | `/api/v1/lost-enquiries`         | access JWT |
| POST   | `/api/v1/lost-enquiries`         | access JWT |
| GET    | `/api/v1/lost-enquiries/{id}`    | access JWT |
| PATCH  | `/api/v1/lost-enquiries/{id}`    | access JWT |
| DELETE | `/api/v1/lost-enquiries/{id}`    | access JWT |

Docs: `http://localhost:8000/api/v1/docs` (Swagger), `/api/v1/redoc`.

## Development

```bash
make install        # uv sync --all-extras
make lint           # ruff check + format --check
make format         # auto-fix
make typecheck      # mypy strict
make test           # full test suite
make test-unit      # unit tests only
make test-int       # integration tests (compose up first)
```

## Migrations

```bash
make migrate              # upgrade head
make revision m="add x"   # autogenerate revision
```

## Layout

```
app/
  api/         # HTTP routers + DI
  core/        # config, security, logging, errors, rate limit
  db/          # async engine + redis client
  models/      # SQLAlchemy ORM
  schemas/     # Pydantic API contracts
  services/    # business logic
  repositories/# data access
```

Layering: `api → services → repositories → models`. Cross-cutting in `core/`.

## Production notes

- `JWT_SECRET` must be replaced in any non-local env — the app refuses to start otherwise.
- `CORS_ALLOW_ORIGINS` should be set to the explicit frontend origin(s).
- The default CMD uses `gunicorn` with `UvicornWorker` (2 workers; tune in compose).
- Healthchecks: `/healthz` is liveness; `/readyz` checks DB + Redis.
- Rate limits per IP per minute, sliding window in Redis.
- Refresh tokens are stored in Redis by `jti` and revoked on logout / rotated on refresh.

## License

MIT
