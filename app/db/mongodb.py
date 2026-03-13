import shlex
from urllib.parse import parse_qs, quote_plus, urlencode, urlparse, urlunparse

import certifi
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ServerSelectionTimeoutError
from app.core.config import get_settings

settings = get_settings()


class Database:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None


database = Database()


def _extract_mongosh_arg(parts: list[str], key: str) -> str | None:
    lowered = [p.lower() for p in parts]
    key = key.lower()
    if key in lowered:
        idx = lowered.index(key)
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return None


def _normalize_mongodb_url(raw_value: str) -> str:
    value = (raw_value or "").strip()

    if value.startswith("mongodb://") or value.startswith("mongodb+srv://"):
        return value

    if value.startswith("mongosh"):
        try:
            parts = shlex.split(value)
        except Exception as e:
            raise ValueError(f"Invalid mongosh command in MONGODB_URL: {e}")

        host = _extract_mongosh_arg(parts, "--host")
        port = _extract_mongosh_arg(parts, "--port") or "27017"
        username = _extract_mongosh_arg(parts, "--username")
        password = _extract_mongosh_arg(parts, "--password")
        auth_db = (
            _extract_mongosh_arg(parts, "--authenticationdatabase")
            or "admin"
        )

        if not host:
            raise ValueError("mongosh command is missing --host")

        if username and password:
            return (
                f"mongodb://{quote_plus(username)}:{quote_plus(password)}"
                f"@{host}:{port}/?authSource={quote_plus(auth_db)}"
            )

        return f"mongodb://{host}:{port}"

    raise ValueError("MONGODB_URL must be a MongoDB URI or a mongosh command")


def _should_enable_tls(mongodb_url: str) -> bool:
    if mongodb_url.startswith("mongodb+srv://"):
        return True

    parsed = urlparse(mongodb_url)
    query = parse_qs(parsed.query)
    tls_flag = (query.get("tls") or query.get("ssl") or ["false"])[0].lower()
    return tls_flag in {"1", "true", "yes"}


def _safe_mongo_target(mongodb_url: str) -> str:
    parsed = urlparse(mongodb_url)
    return parsed.netloc or "unknown-host"


def _ensure_direct_connection(mongodb_url: str) -> str:
    parsed = urlparse(mongodb_url)
    if parsed.scheme != "mongodb":
        return mongodb_url

    query = parse_qs(parsed.query)
    existing = (query.get("directConnection") or [""])[0].lower()
    if existing in {"true", "1", "yes"}:
        return mongodb_url

    query["directConnection"] = ["true"]
    rebuilt_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=rebuilt_query))


async def connect_db():
    mongodb_url = _normalize_mongodb_url(settings.resolved_mongodb_url())
    print(f"Connecting to MongoDB: {_safe_mongo_target(mongodb_url)}")

    client_kwargs = {
        "serverSelectionTimeoutMS": 15000,
        "connectTimeoutMS": 15000,
        "socketTimeoutMS": 15000,
    }
    if _should_enable_tls(mongodb_url):
        client_kwargs["tlsCAFile"] = certifi.where()

    try:
        database.client = AsyncIOMotorClient(mongodb_url, **client_kwargs)
        database.db = database.client[settings.resolved_database_name()]

        # Ping to verify connection
        await database.client.admin.command("ping")
        print("MongoDB ping OK")
    except ServerSelectionTimeoutError as e:
        fallback_url = _ensure_direct_connection(mongodb_url)
        if fallback_url != mongodb_url:
            print("MongoDB discovery failed, retrying with directConnection=true")
            database.client = AsyncIOMotorClient(fallback_url, **client_kwargs)
            database.db = database.client[settings.resolved_database_name()]
            await database.client.admin.command("ping")
            print("MongoDB ping OK (direct connection)")
        else:
            print(f"MongoDB connection failed: {type(e).__name__}: {e}")
            raise
    except Exception as e:
        print(f"MongoDB connection failed: {type(e).__name__}: {e}")
        raise

    # Create indexes — don't crash if this fails
    try:
        await database.db.users.create_index("username", unique=True)
        await database.db.users.create_index("email", unique=True)
        await database.db.results.create_index([("user_id", 1), ("created_at", -1)])
        await database.db.results.create_index([("wpm", -1)])
        await database.db.results.create_index([("mode", 1), ("mode_value", 1), ("wpm", -1)])
        print("Indexes created OK")
    except Exception as e:
        print(f"Warning: Index creation failed (non-fatal): {e}")

    print(f"Connected to MongoDB: {settings.resolved_database_name()}")


async def disconnect_db():
    if database.client:
        database.client.close()
        print("Disconnected from MongoDB")


def get_db() -> AsyncIOMotorDatabase:
    return database.db
