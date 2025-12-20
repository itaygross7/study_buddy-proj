# src/api/routes_summary.py
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
    """
    Trigger an AI summary task for an entire course.

    Expected form fields:
    - course_id: required
    - query: optional (defaults to 'general summary').

    HTMX behavior:
    - If HX-Request: returns HTML partial (task_status.html) so UI can start polling.
    - Otherwise returns JSON.
    """
    user_id = current_user.id
    course_id = (request.form.get("course_id") or "").strip()
    query = (request.form.get("query") or "general summary").strip()

    if not course_id:
        # HTMX should NOT get JSON dumped into the page
        if request.headers.get("HX-Request") == "true":
            return (
                "<div class='p-4 rounded-2xl bg-red-50/50 border border-red-200 text-right'>"
                "<div class='text-sm font-semibold text-red-800'>חסר course_id</div>"
                "<div class='text-xs text-red-700 mt-1'>בחר קורס ונסה שוב.</div>"
                "</div>",
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

        # ✅ HTMX: return the polling component immediately (HTML)
        if request.headers.get("HX-Request") == "true":
            # ensure we render the freshest copy if repo returns a model
            try:
                task_fresh = task_repo.get_by_id(task.id)
                task = task_fresh or task
            except Exception:
                pass
            return render_template("task_status.html", task=task), 202

        # Non-HTMX: return JSON
        return jsonify(
            {
                "status": "processing_summary",
                "task_id": task.id,
                "polling_url": url_for("task_bp.get_task_status_route", task_id=task.id),
            }
        ), 202

    except Exception as e:
        logger.error(f"Error in trigger_summary for user {user_id}: {e}", exc_info=True)

        if request.headers.get("HX-Request") == "true":
            return (
                "<div class='p-4 rounded-2xl bg-red-50/50 border border-red-200 text-right'>"
                "<div class='text-sm font-semibold text-red-800'>אוי, משהו השתבש.</div>"
                "<div class='text-xs text-red-700 mt-1'>נסה שוב בעוד רגע 🦫</div>"
                "</div>",
                500,
            )

        return jsonify({"error": "An internal server error occurred."}), 500
