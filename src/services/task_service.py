import uuid
from datetime import datetime, timezone
from pymongo.database import Database
from src.infrastructure.database import db as flask_db
from src.domain.models.db_models import Task, TaskStatus
from sb_utils.logger_utils import logger


def _get_db(db_conn: Database = None) -> Database:
    """Returns the provided db_conn or the default Flask db proxy."""
    return db_conn if db_conn is not None else flask_db


def create_task(db_conn: Database = None) -> str:
    """Creates a new task in the database and returns its ID."""
    db = _get_db(db_conn)
    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    task = Task(
        _id=task_id,
        status=TaskStatus.PENDING,
        created_at=now,
        updated_at=now
    )
    db.tasks.insert_one(task.to_dict())
    logger.info(f"Created new task with ID: {task_id}")
    return task_id


def get_task(task_id: str, db_conn: Database = None) -> Task | None:
    """Retrieves a task from the database."""
    db = _get_db(db_conn)
    task_data = db.tasks.find_one({"_id": task_id})
    return Task(**task_data) if task_data else None


def update_task_status(task_id: str, status: TaskStatus, result_id: str = None,
                       error_message: str = None, db_conn: Database = None):
    """Updates the status and result of a task."""
    db = _get_db(db_conn)
    update_doc = {
        "$set": {
            "status": status.value,
            "updated_at": datetime.now(timezone.utc)
        }
    }
    if result_id:
        update_doc["$set"]["result_id"] = result_id
    if error_message:
        update_doc["$set"]["error_message"] = error_message

    db.tasks.update_one({"_id": task_id}, update_doc)
    logger.info(f"Updated task {task_id} to status: {status.value}")
