from typing import Any, Dict, Optional
from pymongo import MongoClient, ASCENDING
import logging

logger = logging.getLogger(__name__)

class MongoClientWrapper:
    def __init__(self, uri: str = "mongodb://localhost:27017", db_name: str = "studybuddy"):
        self._client = MongoClient(uri, serverSelectionTimeoutMS=2000)
        self.db = self._client[db_name]
        self._ensure_indexes()

    def _ensure_indexes(self):
        # Example indexes — add as needed for queries (no unique on user content)
        try:
            self.db.jobs.create_index([("created_at", ASCENDING)])
        except Exception:
            logger.warning("Failed to create indexes on MongoDB", exc_info=True)

    def insert_job(self, collection: str, job: Dict[str, Any]) -> str:
        # Safe insert; ensure no direct user content used in queries
        res = self.db[collection].insert_one(job)
        return str(res.inserted_id)

    def find_job(self, collection: str, job_id: Any) -> Optional[Dict]:
        res = self.db[collection].find_one({"_id": job_id})
        return res

