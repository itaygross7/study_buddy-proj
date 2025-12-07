from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from pymongo.database import Database

from src.infrastructure.database import db as flask_db
from src.domain.models.db_models import Task, TaskStatus
from sb_utils.logger_utils import logger


def _get_db(db_conn: Optional[Database] = None) -> Database:
    """
    Resolve the MongoDB connection.

    If a specific connection is passed (e.g., from tests), use that.
    Otherwise, fall back to the default Flask DB proxy.
    """
    return db_conn if db_conn is not None else flask_db


def create_task(db_conn: Optional[Database] = None) -> str:
    """
    Create a new task document and return its ID.

    The task starts in PENDING state. Additional metadata (course_id,
    task_type, etc.) can be attached later by an update function or
    written directly into the document by the caller.

    :param db_conn: Optional explicit DB connection (useful for tests).
    :return: The ID of the newly created task.
    """
    db = _get_db(db_conn)
    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    task = Task(
        _id=task_id,
        status=TaskStatus.PENDING,  # domain enum
        created_at=now,
        updated_at=now,
    )

    # Persist as dict. Task.to_dict() should normalize the enum to its value.
    db.tasks.insert_one(task.to_dict())

    logger.info(
        "Created new task",
        extra={
            "task_id": task_id,
            "status": TaskStatus.PENDING.value,
            "component": "task_service",
        },
    )
    return task_id


def get_task(task_id: str, db_conn: Optional[Database] = None) -> Optional[Task]:
    """
    Retrieve a task by ID.

    :param task_id: Task identifier (UUID string).
    :param db_conn: Optional explicit DB connection.
    :return: Task instance, or None if not found.
    """
    db = _get_db(db_conn)
    task_data = db.tasks.find_one({"_id": task_id})

    if not task_data:
        logger.debug(
            "Task not found in DB",
            extra={"task_id": task_id, "component": "task_service"},
        )
        return None

    # Task(**task_data) assumes the domain model knows how to handle:
    #   - status as a string (e.g. "PENDING", "COMPLETED", ...)
    #   - _id as the primary identifier
    task = Task(**task_data)
    return task


def update_task_status(
    task_id: str,
    status: TaskStatus,
    result_id: Optional[str] = None,
    error_message: Optional[str] = None,
    db_conn: Optional[Database] = None,
) -> None:
    """
    Update the status (and optionally result_id/error_message) of a task.

    This is used by workers to mark tasks as PROCESSING / COMPLETED / FAILED.

    :param task_id: Task identifier to update.
    :param status: New TaskStatus enum value.
    :param result_id: Optional ID pointing to the result document (e.g. summary/quiz).
    :param error_message: Optional user-facing error message (must be sanitized).
    :param db_conn: Optional explicit DB connection.
    """
    db = _get_db(db_conn)

    set_doc: dict = {
        "status": status.value,
        "updated_at": datetime.now(timezone.utc),
    }

    if result_id is not None:
        set_doc["result_id"] = result_id

    if error_message is not None:
        # IMPORTANT: Only pass a clean, user-friendly message here.
        # No stack traces / internal IDs / secrets.
        set_doc["error_message"] = error_message

    update_doc = {"$set": set_doc}

    result = db.tasks.update_one({"_id": task_id}, update_doc)

    if result.matched_count == 0:
        logger.warning(
            "Attempted to update non-existing task",
            extra={
                "task_id": task_id,
                "new_status": status.value,
                "component": "task_service",
            },
        )
        return

    logger.info(
        "Updated task status",
        extra={
            "task_id": task_id,
            "new_status": status.value,
            "has_result_id": result_id is not None,
            "has_error_message": error_message is not None,
            "component": "task_service",
        },
    )
