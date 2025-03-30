from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

_client = None

def get_db():
    global _client
    if not _client:
        _client = MongoClient(
            os.getenv("MONGO_URI"),
            connectTimeoutMS=5000,
            socketTimeoutMS=30000,
            retryWrites=True
        )
    return _client[os.getenv("MONGODB_DBNAME")]