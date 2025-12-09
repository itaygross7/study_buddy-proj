from __future__ import annotations

from typing import Union, Tuple

from flask import Blueprint, jsonify, render_template, Response

from src.services.task_service import get_task
from sb_utils.logger_utils import logger

task_bp = Blueprint("task_bp", __name__, url_prefix="/tasks")


@task_bp.route("/<string:task_id>", methods=["GET"])
def get_task_status_route(task_id: str) -> Union[Response, Tuple[Response, int]]:
    """
    Poll the status of a background task and return an HTML partial.

    Designed primarily for HTMX.
    """
    logger.debug(
        "Polling task status",
        extra={"task_id": task_id, "route": "get_task_status_route"},
    )

    try:
        task = get_task(task_id)
    except Exception:
        logger.exception(
            "Failed to fetch task from task_service",
            extra={"task_id": task_id, "route": "get_task_status_route"},
        )
        return jsonify({"error": "Internal server error"}), 500

    if task is None:
        logger.warning(
            "Task not found when polling",
            extra={"task_id": task_id, "route": "get_task_status_route"},
        )
        return jsonify({"error": "Task not found"}), 404

    return render_template("task_status.html", task=task)
