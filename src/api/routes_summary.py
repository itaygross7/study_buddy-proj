from __future__ import annotations

from flask import Blueprint, request, jsonify, url_for, render_template
from flask_login import login_required, current_user

from src.infrastructure.database import db
from src.infrastructure.repositories import MongoTaskRepository
from src.infrastructure.rabbitmq import publish_task
from sb_utils.logger_utils import logger

summary_bp = Blueprint("summary_bp", __name__)


@summary_bp.route("/trigger", methods=["POST"])
@login_required
def trigger_summary():
    user_id = current_user.id
    course_id = request.form.get("course_id")
    query = request.form.get("query", "general summary")

    if not course_id:
        # אם זה HTMX – נחזיר partial יפה במקום JSON
        if request.headers.get("HX-Request") == "true":
            return (
                render_template(
                    "task_status.html",
                    task={"status": "FAILED", "error_message": "course_id is required"},
                ),
                400,
            )
        return jsonify({"error": "course_id is required"}), 400

    try:
        task_repo = MongoTaskRepository(db)
        task = task_repo.create(
            user_id=user_id,
            course_id=course_id,
            task_type="summary",
        )

        publish_task(
            queue_name="summarize",
            task_body={
                "task_id": task.id,
                "course_id": course_id,
                "query": query,
            },
        )

        # ✅ אם זה HTMX – מחזירים את ה־partial שמתחיל polling
        if request.headers.get("HX-Request") == "true":
            return render_template("task_status.html", task=task), 202

        # API רגיל (לא HTMX) – מחזירים JSON
        return jsonify(
            {
                "status": "processing_summary",
                "task_id": task.id,
                "polling_url": url_for("task_bp.get_task_status_route", task_id=task.id),
            }
        ), 202

    except Exception:
        logger.exception("Error in trigger_summary", extra={"user_id": user_id, "course_id": course_id})
        if request.headers.get("HX-Request") == "true":
            return (
                render_template(
                    "task_status.html",
                    task={"status": "FAILED", "error_message": "שגיאה פנימית. נסה שוב."},
                ),
                500,
            )
        return jsonify({"error": "An internal server error occurred."}), 500
