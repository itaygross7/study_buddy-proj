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

    - This endpoint is designed primarily for HTMX.
    - It returns 'task_status.html', which renders a single task row.
    - The template is responsible for:
        * Status label + color
        * Avner avatar (loading / success / error / pending)
        * Optional "view" button for completed tools

    Security note:
    -------------
    The Task model MUST ensure that any fields exposed to the template
    are safe for the UI (no secrets, no internal IDs that shouldn't be
    visible to the student).
    """
    logger.debug(
        "Polling task status",
        extra={"task_id": task_id, "route": "get_task_status_route"},
    )

    try:
        task = get_task(task_id)
    except Exception:
        # Log full details internally, but do not leak them to the client.
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

    # NOTE:
    # If Task has an internal _id field, the Jinja template should use
    # `task._id` for IDs and URLs (e.g., hx-get). If you exposed a .id
    # property on the model, the template can use that instead.
    #
    # Partial: templates/task_status.html
    return render_template("task_status.html", task=task)
