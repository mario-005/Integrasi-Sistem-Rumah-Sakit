import os
from pymongo import MongoClient

MONGO_URL = os.getenv(
    "PHARMACY_MONGODB_URL",
    "mongodb://mongodb-pharmacy:27017/pharmacy_db"
)

client = MongoClient(MONGO_URL)
db = client.get_database("pharmacy_db")


def get_db():
    return db
