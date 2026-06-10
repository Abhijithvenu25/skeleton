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

## Quickstart

```bash
# 1. Configure env
cp .env.example .env

# 2. Bring up the stack (app waits for pg/redis to be healthy, then auto-migrates)
make up

# 3. Seed an admin user
make seed

# 4. Smoke test
curl http://localhost:8000/api/v1/healthz
curl http://localhost:8000/api/v1/readyz
```

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
| GET    | `/api/v1/customers`     | access JWT |
| POST   | `/api/v1/customers`     | access JWT |
| GET    | `/api/v1/customers/{id}`| access JWT |
| PATCH  | `/api/v1/customers/{id}`| access JWT |
| DELETE | `/api/v1/customers/{id}`| access JWT |

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
src/app/
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
