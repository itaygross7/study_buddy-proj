from pymongo import MongoClient
from ..config.settings import settings

class Database:
    """
    Singleton class to manage the database connection.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance.client = MongoClient(settings.MONGO_URI)
            cls._instance.db = cls._instance.client[settings.MONGO_DB_NAME]
        return cls._instance

    def get_db(self):
        return self.db

db_instance = Database()
