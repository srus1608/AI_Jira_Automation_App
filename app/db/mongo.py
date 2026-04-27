from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from app.config import MONGO_URI, DATABASE_NAME, COLLECTION_TICKETS, logger

_client: MongoClient | None = None
_db: Database | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
        )
        logger.info("MongoDB client created (uri=%s)", MONGO_URI)
    return _client


def get_database() -> Database:
    global _db
    if _db is None:
        _db = get_client()[DATABASE_NAME]
        logger.info("Using database: %s", DATABASE_NAME)
    return _db


def get_tickets_collection() -> Collection:
    return get_database()[COLLECTION_TICKETS]


def close_connection() -> None:
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB connection closed")
