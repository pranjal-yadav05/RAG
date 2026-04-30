"""
db.py — session store
=====================

Schema
------
{
    "session_id" : str  (UUID)
    "user_id"    : str
    "file_id"    : str  (FK → files.file_id)
    "title"      : str  (optional; can be set later by client)
    "messages"   : [
        {
            "role"       : "user" | "assistant",
            "content"    : str,
            "highlights" : [...],   # assistant only
            "images"     : [...],   # assistant only
            "created_at" : datetime
        }
    ]
    "created_at" : datetime
    "updated_at" : datetime
}
"""

from motor.motor_asyncio import AsyncIOMotorClient
import os
from datetime import datetime
import uuid

client = AsyncIOMotorClient(os.getenv("MONGO_URL"))
db = client.chat_db

sessions = db.get_collection("sessions")


# ── CREATE ────────────────────────────────────────────────────────────────────

async def create_session(user_id: str, file_id: str, title: str = "New Chat") -> str:
    session = {
        "session_id": str(uuid.uuid4()),
        "user_id":    user_id,
        "file_id":    file_id,
        "title":      title,
        "messages":   [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await sessions.insert_one(session)
    return session["session_id"]


# ── READ ──────────────────────────────────────────────────────────────────────

async def get_session(session_id: str) -> dict | None:
    return await sessions.find_one({"session_id": session_id})


async def get_sessions(user_id: str) -> list[dict]:
    """All sessions for a user, newest first, without Mongo _id."""
    cursor = sessions.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("updated_at", -1)
    return await cursor.to_list(length=200)


async def get_sessions_for_file(file_id: str) -> list[dict]:
    """Useful for listing sessions grouped by file."""
    cursor = sessions.find({"file_id": file_id}, {"_id": 0}).sort("updated_at", -1)
    return await cursor.to_list(length=200)


# ── WRITE ─────────────────────────────────────────────────────────────────────

async def add_message(session_id: str, message: dict) -> None:
    message.setdefault("created_at", datetime.utcnow())
    await sessions.update_one(
        {"session_id": session_id},
        {
            "$push": {"messages": message},
            "$set":  {"updated_at": datetime.utcnow()},
        }
    )


async def rename_session(session_id: str, title: str) -> None:
    await sessions.update_one(
        {"session_id": session_id},
        {"$set": {"title": title, "updated_at": datetime.utcnow()}}
    )


# ── DELETE ────────────────────────────────────────────────────────────────────

async def delete_session(session_id: str) -> None:
    await sessions.delete_one({"session_id": session_id})


async def delete_sessions_for_file(file_id: str) -> None:
    """Called automatically when a file is deleted."""
    await sessions.delete_many({"file_id": file_id})