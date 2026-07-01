# Migration Notes — Dev → AWS / Oracle

This is the dev-time setup. Production is moving to **AWS** (or Oracle)
under a different cloud account. The only thing that changes between
environments is the **value of `REDIS_URL`** — the application code
stays the same.

## What's environment-agnostic

- `app/db/redis.py` — uses `redis.asyncio.from_url(REDIS_URL)`. Speaks
  `redis://` (plain) and `rediss://` (TLS) on the same line. Works
  against any provider that exposes the Redis protocol.
- `app/core/exceptions.py` — the `RedisError` exception handler returns
  503 on any Redis failure, regardless of provider.
- `app/services/auth.py` — refresh-token `jti` storage and the
  rate-limiter are just `redis.set(...)` / `redis.get(...)` calls. No
  provider-specific features are used (no Streams, no Pub/Sub, no
  Modules, no Functions).
- `app/core/rate_limit.py` — `SlidingWindowLimiter` uses the standard
  `ZADD` + `ZREMRANGEBYSCORE` + `ZCARD` pattern. Compatible with Redis
  6.0+ on every major provider.

## What's environment-specific

Just this one env var:

```
REDIS_URL=<provider-specific-connection-string>
```

| Environment | REDIS_URL value | Notes |
|---|---|---|
| Local dev (docker compose) | `redis://redis:6379/0` | Docker-network hostname; only works inside `docker compose` |
| Render (dev, current) | `rediss://default:<password>@apn1-utter-falcon-12345.upstash.io:6379` | Upstash; free tier; 10k cmds/day |
| Render (prod, future) | TBD — likely `rediss://...` via Upstash Pro or Render-native Redis |  |
| AWS (prod) | `rediss://...clustercfg.<region>.cache.amazonaws.com:6379` (ElastiCache) or `rediss://...upstash.io:6379` (Upstash on AWS) | TLS required by ElastiCache; use the *primary* endpoint, not a replica |
| Oracle (prod) | `rediss://...` via Oracle Cache (Redis-compatible) or Upstash on Oracle Cloud | Oracle's Cache service exposes the Redis protocol on port 6379/6380 |

## AWS migration checklist

1. Provision ElastiCache for Redis (or Upstash on AWS, or AWS MemoryDB).
2. Take the *primary endpoint* with TLS — looks like
   `clustercfg.xxxxx.<region>.cache.amazonaws.com:6379`. Generate
   a Redis AUTH token if the cluster isn't a no-auth dev cluster.
3. URL-format it: `rediss://:<auth-token>@clustercfg.xxxxx.<region>.cache.amazonaws.com:6379`.
   (Note the colon before the token — that's "user is empty, password
   is the auth token", which is the convention for ElastiCache.)
4. In the AWS-side hosting (ECS, App Runner, EC2, etc.):
   - Set `REDIS_URL` to the URL above.
   - Set `APP_ENV=prod`.
   - The rest of the env (`POSTGRES_*`, `JWT_SECRET`, `CORS_ALLOW_ORIGINS`)
     carries over unchanged.
5. Deploy. The startup `ping_redis()` will confirm reachability; if
   the URL is wrong, the app refuses to boot with a clear error
   instead of returning 503s on every request.

## Oracle migration checklist

1. Provision Oracle Cache (Redis-compatible) on OCI.
2. Take the primary endpoint with TLS. URL-format it the same way.
3. Set `REDIS_URL` + `APP_ENV=prod` in the OCI-side environment.
4. Deploy. Same `ping_redis()` validation applies.

## What to verify after every migration

After setting `REDIS_URL` and redeploying:

```bash
# 1. App should boot cleanly (no redis_unreachable in logs)
grep -E 'redis_ok|redis_unreachable|app_starting' /var/log/app.log

# Expected: redis_ok + app_starting, no redis_unreachable.

# 2. Health check
curl -s https://<your-app>/api/v1/health/healthz
# Expected: {"status":"ok"}

# 3. Auth flow works end-to-end
curl -s -X POST https://<your-app>/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"sanity@x.com","password":"hunter2hunter"}'
# Expected: 201 with a `token.access_token` field

# 4. Rate limit fires (sanity check, 6th request in 60s should 429)
for i in 1 2 3 4 5 6; do
  curl -s -o /dev/null -w "register $i: %{http_code}\n" -X POST \
    https://<your-app>/api/v1/auth/register \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"rl-$i-$(date +%s%N)@x.com\",\"password\":\"hunter2hunter\"}"
done
# Expected: 1-5 are 201, 6 is 429
```

If any of those fail, the failure mode is the same as the dev case:
check `REDIS_URL` is correct, the security group / firewall allows
port 6379/6380 from the app's network, and the cluster is in a
healthy state.

## Things that will *not* break

- `JWT_SECRET` rotation — independent of Redis, just env var swap
- The `staff_profiles` → `user_roles` migration (`0004_user_roles`)
  — already applied; runs idempotently on next deploy
- `validate_production()` checks — same rules, same env-var names,
  same failure modes
- All CRM endpoints (companies, contacts, projects, enquiries,
  site_visits, quotations, lost_enquiries) — they don't touch Redis
  directly, only via auth and rate-limit

## Things to flag for follow-up

- `REFRESH_TOKEN_TTL_DAYS=7` is the dev value. For prod, lower to
  `1` or `2`. A stolen refresh token has a shorter blast radius.
  This is independent of the Redis move.
- The `validate_production` warning `redis_url_looks_docker_internal`
  only fires for the literal hostname `redis`. If a future provider
  uses a different dev-time hostname pattern, extend the check.
  This is unlikely — most providers use real-looking hostnames
  from day one.

## Reference: providers and their URL formats

| Provider | URL scheme | TLS default | Auth in URL? |
|---|---|---|---|
| Upstash | `rediss://default:<token>@<host>.upstash.io:6379` | required | token in user (default) |
| Render Redis | `rediss://red-xxxxxxxxxxxxx:6379` | required | token in path |
| ElastiCache (AWS) | `rediss://:<auth-token>@clustercfg.xxxxx.<region>.cache.amazonaws.com:6379` | required | token as password, user empty |
| ElastiCache w/ IAM | (no URL auth; use SigV4 separately) | required | n/a |
| MemoryDB (AWS) | `rediss://...clustercfg....memorydb.<region>.amazonaws.com:6379` | required | token as password |
| Oracle Cache | `rediss://...` (TLS), check OCI console for exact format | configurable | token in URL |
| Redis Cloud | `rediss://:<password>@<host>:<port>` | required | token as password |
| Local Redis (no TLS) | `redis://redis:6379/0` (docker) or `redis://localhost:6379/0` (binary) | none | none |

All of these are valid inputs to `redis.asyncio.from_url(REDIS_URL)`. The
Python client parses the scheme and switches to TLS automatically when
the scheme is `rediss://`. No code change needed.
