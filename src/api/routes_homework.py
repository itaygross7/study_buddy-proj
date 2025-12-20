# src/api/routes_homework.py
from flask import Blueprint, request, jsonify, url_for, render_template
from flask_login import login_required, current_user
from pydantic import ValidationError

from src.domain.models.api_models import HomeworkRequest, TaskResponse
from src.services.task_service import create_task
from src.infrastructure.rabbitmq import publish_task
from sb_utils.logger_utils import logger

homework_bp = Blueprint("homework_bp", __name__)


@homework_bp.route("/", methods=["POST"])
@login_required
def trigger_homework_helper():
    """
    Triggers the homework helper task.

    Input:
      - HTMX form: problem_statement (+ optional course_id/context)
      - JSON: HomeworkRequest

    Output:
      - HTMX: renders task_status.html (polling component)
      - Non-HTMX: returns JSON TaskResponse
    """
    user_id = current_user.id
    is_htmx = request.headers.get("HX-Request") == "true"

    problem_statement: str | None = None
    course_id: str | None = None
    context_text: str | None = None

    # -------- Parse input --------
    if request.is_json:
        try:
            payload = request.get_json(silent=True) or {}
            req_data = HomeworkRequest(**payload)
            problem_statement = req_data.problem_statement
            course_id = getattr(req_data, "course_id", None)
            context_text = getattr(req_data, "context", None)
        except ValidationError as e:
            if is_htmx:
                return (
                    "<div class='p-4 rounded-2xl bg-red-50/50 border border-red-200 text-right'>"
                    "<div class='text-sm font-semibold text-red-800'>בקשה לא תקינה</div>"
                    "<div class='text-xs text-red-700 mt-1'>בדוק את השדות ונסה שוב.</div>"
                    "</div>",
                    400,
                )
            return jsonify({"error": e.errors()}), 400
        except Exception as e:
            logger.error(f"Failed to parse homework request (JSON): {e}", exc_info=True)
            if is_htmx:
                return (
                    "<div class='p-4 rounded-2xl bg-red-50/50 border border-red-200 text-right'>"
                    "<div class='text-sm font-semibold text-red-800'>שגיאה בקריאת הבקשה</div>"
                    "<div class='text-xs text-red-700 mt-1'>נסה שוב.</div>"
                    "</div>",
                    400,
                )
            return jsonify({"error": "Invalid request format"}), 400

    else:
        problem_statement = (request.form.get("problem_statement") or "").strip()
        course_id = (request.form.get("course_id") or "").strip() or None
        context_text = (request.form.get("context") or "").strip() or None

        if not problem_statement:
            if is_htmx:
                return (
                    "<div class='p-4 rounded-2xl bg-red-50/50 border border-red-200 text-right'>"
                    "<div class='text-sm font-semibold text-red-800'>חסר טקסט של שאלה</div>"
                    "<div class='text-xs text-red-700 mt-1'>הדבק/כתוב את השאלה ואז נסה שוב.</div>"
                    "</div>",
                    400,
                )
            return jsonify({"error": "problem_statement is required"}), 400

    # -------- Create task + publish --------
    try:
        task_id = create_task()

        task_body = {
            "task_id": task_id,
            "user_id": user_id,  # ✅ do not trust form user_id
            "problem_statement": problem_statement,
            "course_id": course_id,
            "context": context_text,
        }

        publish_task(queue_name="homework", task_body=task_body)
        logger.info(f"Published homework task {task_id} (user={user_id})")

        polling_url = url_for("task_bp.get_task_status_route", task_id=task_id, _external=not is_htmx)

        # ✅ HTMX: return polling component HTML
        if is_htmx:
            # Build minimal task dict that matches task_status.html expectations
            task_stub = {
                "id": task_id,
                "status": "PENDING",
                "task_type": "homework",
                "result_id": None,
                "next_tool_endpoint": None,
                "error_message": None,
            }
            return render_template("task_status.html", task=task_stub), 202

        # Non-HTMX: JSON
        response = TaskResponse(
            task_id=task_id,
            status="PENDING",
            polling_url=polling_url,
        )
        return jsonify(response.to_dict()), 202

    except Exception as e:
        logger.error(f"Failed to create homework task: {e}", exc_info=True)
        if is_htmx:
            return (
                "<div class='p-4 rounded-2xl bg-red-50/50 border border-red-200 text-right'>"
                "<div class='text-sm font-semibold text-red-800'>אוי, משהו השתבש.</div>"
                "<div class='text-xs text-red-700 mt-1'>נסה שוב בעוד רגע 🦫</div>"
                "</div>",
                500,
            )
        return jsonify({"error": "Failed to create task"}), 500
