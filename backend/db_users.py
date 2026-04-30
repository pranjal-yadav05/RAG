from motor.motor_asyncio import AsyncIOMotorClient
import os

client = AsyncIOMotorClient(os.getenv("MONGO_URL"))
db = client.chat_db

users = db.get_collection("users")