"""
db_files.py
===========
File metadata store.

Schema
------
{
    "file_id"      : str  (UUID, primary key)
    "user_id"      : str
    "file_name"    : str  (original filename shown to user)
    "content_hash" : str  (MD5 of raw bytes — for dedup / integrity)
    "created_at"   : datetime
}

Notes
-----
- content_hash lets us skip re-embedding when the same user re-uploads
  the same binary.  We still create a NEW file record so the user can
  manage each upload independently.
- storage_path is intentionally NOT stored in the DB; it is always
  derived on-the-fly via storage_paths.paths(user_id, file_id).
  Storing it would create a second source of truth that can drift.
"""

from motor.motor_asyncio import AsyncIOMotorClient
import os
from datetime import datetime
import uuid

client = AsyncIOMotorClient(os.getenv("MONGO_URL"))
db = client.chat_db

files = db.get_collection("files")


# ── CREATE ────────────────────────────────────────────────────────────────────

async def create_file(user_id: str, file_name: str, content_hash: str) -> str:
    """
    Insert a new file record.  Returns the generated file_id.
    """
    file_doc = {
        "file_id":      str(uuid.uuid4()),
        "user_id":      user_id,
        "file_name":    file_name,
        "content_hash": content_hash,
        "created_at":   datetime.utcnow(),
    }
    await files.insert_one(file_doc)
    return file_doc["file_id"]


# ── READ ──────────────────────────────────────────────────────────────────────

async def get_file(file_id: str) -> dict | None:
    return await files.find_one({"file_id": file_id}, {"_id": 0})


async def get_user_files(user_id: str) -> list[dict]:
    cursor = files.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1)
    return await cursor.to_list(length=200)


async def find_duplicate(user_id: str, content_hash: str) -> dict | None:
    """
    Return an existing file record if this user already uploaded the same
    binary (same content_hash).  None otherwise.
    Used to reuse pre-computed embeddings without re-processing.
    """
    return await files.find_one(
        {"user_id": user_id, "content_hash": content_hash},
        {"_id": 0}
    )


# ── DELETE ────────────────────────────────────────────────────────────────────

async def delete_file(file_id: str) -> None:
    await files.delete_one({"file_id": file_id})