from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import get_settings

settings = get_settings()


class Database:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None


database = Database()


async def connect_db():
    database.client = AsyncIOMotorClient(settings.mongodb_url)
    database.db = database.client[settings.database_name]

    # Create indexes
    await database.db.users.create_index("username", unique=True)
    await database.db.users.create_index("email", unique=True)
    await database.db.results.create_index([("user_id", 1), ("created_at", -1)])
    await database.db.results.create_index([("wpm", -1)])
    await database.db.results.create_index([("mode", 1), ("mode_value", 1), ("wpm", -1)])

    print("Connected to MongoDB")


async def disconnect_db():
    if database.client:
        database.client.close()
        print("Disconnected from MongoDB")


def get_db() -> AsyncIOMotorDatabase:
    return database.db
