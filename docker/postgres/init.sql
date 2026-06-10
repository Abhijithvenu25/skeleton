-- Initial database bootstrap. Loaded by the postgres image on first run.
-- The app uses SQLAlchemy with `citext` for case-insensitive emails and `pgcrypto`
-- is left available for future use.

CREATE EXTENSION IF NOT EXISTS "citext";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
