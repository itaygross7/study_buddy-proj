from typing import Any, Dict, Optional
from bson import ObjectId
from pymongo import MongoClient, ASCENDING
import logging

logger = logging.getLogger(__name__)


class MongoClientWrapper:
    """
    Thin wrapper around MongoClient to centralize indexes and safe patterns.
    """

    def __init__(self, uri: str = "mongodb://localhost:27017", db_name: str = "studybuddy") -> None:
        self._client = MongoClient(uri, serverSelectionTimeoutMS=2000)
        self.db = self._client[db_name]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        # Example indexes — add as needed for queries (no unique on user content)
        try:
            self.db.jobs.create_index([("created_at", ASCENDING)])
        except Exception:
            logger.warning("Failed to create indexes on MongoDB", exc_info=True)

    def insert_job(self, collection: str, job: Dict[str, Any]) -> str:
        """
        Insert a job document and return its ID as string.
        """
        res = self.db[collection].insert_one(job)
        return str(res.inserted_id)

    def find_job(self, collection: str, job_id: Any) -> Optional[Dict[str, Any]]:
        """
        Find a job document by its ID (string or ObjectId).
        """
        oid = ObjectId(job_id) if not isinstance(job_id, ObjectId) else job_id
        res = self.db[collection].find_one({"_id": oid})
        return res
