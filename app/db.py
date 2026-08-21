"""MongoDB connection handling and index setup."""

from flask import current_app
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.errors import PyMongoError


def init_mongo(app):
    """Attach a shared MongoClient to the app. Connection is lazy, so this
    never blocks on startup even if Mongo is not up yet."""
    app.extensions["mongo_client"] = MongoClient(
        app.config["MONGO_URI"],
        serverSelectionTimeoutMS=app.config["MONGO_TIMEOUT_MS"],
        tz_aware=True,
    )
    app.extensions["mongo_indexed"] = False


def get_db():
    db = current_app.extensions["mongo_client"][current_app.config["MONGO_DB"]]
    if not current_app.extensions.get("mongo_indexed"):
        try:
            ensure_indexes(db)
            current_app.extensions["mongo_indexed"] = True
        except PyMongoError:
            # Mongo not ready yet; try again on the next request.
            pass
    return db


def ensure_indexes(db):
    db.users.create_index([("role", ASCENDING), ("name", ASCENDING)])
    db.users.create_index(
        [("email", ASCENDING)],
        unique=True,
        partialFilterExpression={"email": {"$type": "string"}},
    )
    db.rewards.create_index([("active", DESCENDING), ("cost", ASCENDING)])
    db.transactions.create_index([("kid_id", ASCENDING), ("created_at", DESCENDING)])
    db.transactions.create_index([("created_at", DESCENDING)])
    db.redemptions.create_index([("status", ASCENDING), ("created_at", DESCENDING)])
    db.redemptions.create_index([("kid_id", ASCENDING), ("created_at", DESCENDING)])
    db.quests.create_index([("active", DESCENDING), ("title", ASCENDING)])
    db.quest_claims.create_index([("status", ASCENDING), ("created_at", DESCENDING)])
    # One claim per kid, per quest, per period (day/week/ever).
    db.quest_claims.create_index(
        [("quest_id", ASCENDING), ("kid_id", ASCENDING), ("period", ASCENDING)],
        unique=True,
    )
