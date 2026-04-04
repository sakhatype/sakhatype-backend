import asyncpg
from app.core.config import get_settings

settings = get_settings()


class Database:
    pool: asyncpg.Pool | None = None


database = Database()


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(30) NOT NULL UNIQUE,
    email           VARCHAR(255) UNIQUE,
    password_hash   TEXT NOT NULL,
    level           INTEGER NOT NULL DEFAULT 1,
    xp              INTEGER NOT NULL DEFAULT 0,
    total_tests     INTEGER NOT NULL DEFAULT 0,
    best_wpm        DOUBLE PRECISION NOT NULL DEFAULT 0,
    avg_wpm         DOUBLE PRECISION NOT NULL DEFAULT 0,
    avg_accuracy    DOUBLE PRECISION NOT NULL DEFAULT 0,
    achievements    TEXT[] NOT NULL DEFAULT '{}',
    friends         TEXT[] NOT NULL DEFAULT '{}',
    friend_requests_sent     TEXT[] NOT NULL DEFAULT '{}',
    friend_requests_received TEXT[] NOT NULL DEFAULT '{}',
    avatar_url      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS results (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER REFERENCES users(id) ON DELETE SET NULL,
    wpm             DOUBLE PRECISION NOT NULL,
    raw_wpm         DOUBLE PRECISION NOT NULL DEFAULT 0,
    accuracy        DOUBLE PRECISION NOT NULL,
    mode            VARCHAR(20) NOT NULL,
    mode_value      INTEGER NOT NULL,
    language        VARCHAR(20) NOT NULL DEFAULT 'sakha',
    difficulty      VARCHAR(20) NOT NULL DEFAULT 'normal',
    chars_correct   INTEGER NOT NULL DEFAULT 0,
    chars_incorrect INTEGER NOT NULL DEFAULT 0,
    chars_extra     INTEGER NOT NULL DEFAULT 0,
    chars_missed    INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_results_user_created
    ON results (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_results_wpm
    ON results (wpm DESC);
CREATE INDEX IF NOT EXISTS idx_results_mode
    ON results (mode, mode_value, wpm DESC);
CREATE INDEX IF NOT EXISTS idx_results_mode_difficulty_wpm
    ON results (mode, mode_value, difficulty, wpm DESC);
"""


async def connect_db():
    dsn = settings.resolved_postgres_dsn()
    print(f"Connecting to PostgreSQL: {dsn.split('@')[-1] if '@' in dsn else dsn}")

    try:
        database.pool = await asyncpg.create_pool(
            dsn,
            min_size=2,
            max_size=10,
            timeout=15,
            command_timeout=15,
        )
        print("PostgreSQL pool created")

        async with database.pool.acquire() as conn:
            await conn.execute(SCHEMA_SQL)
            await conn.execute(
                "ALTER TABLE users ALTER COLUMN email DROP NOT NULL"
            )
        print("Schema ensured OK")

    except Exception as e:
        print(f"PostgreSQL connection failed: {type(e).__name__}: {e}")
        raise

    print(f"Connected to PostgreSQL: {settings.resolved_database_name()}")


async def disconnect_db():
    if database.pool:
        await database.pool.close()
        print("Disconnected from PostgreSQL")


def get_pool() -> asyncpg.Pool:
    return database.pool
