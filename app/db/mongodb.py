import certifi
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import get_settings

settings = get_settings()


class Database:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None


database = Database()


async def connect_db():
    print(f"Connecting to MongoDB...")

    database.client = AsyncIOMotorClient(
        settings.mongodb_url,
        serverSelectionTimeoutMS=15000,
        connectTimeoutMS=15000,
        socketTimeoutMS=15000,
        tlsCAFile=certifi.where(),
    )
    database.db = database.client[settings.database_name]

    # Ping to verify connection
    await database.client.admin.command("ping")
    print("MongoDB ping OK")

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

    print(f"Connected to MongoDB: {settings.database_name}")


async def disconnect_db():
    if database.client:
        database.client.close()
        print("Disconnected from MongoDB")


def get_db() -> AsyncIOMotorDatabase:
    return database.db
