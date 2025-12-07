import json
from flask import Blueprint, request, jsonify, url_for
from pydantic import ValidationError

from src.domain.models.api_models import HomeworkRequest, TaskResponse
from src.services.task_service import create_task
from src.infrastructure.rabbitmq import publish_task
from sb_utils.logger_utils import logger

homework_bp = Blueprint('homework_bp', __name__)


@homework_bp.route('/', methods=['POST'])
def trigger_homework_helper():
    """Triggers the homework helper task."""
    problem_statement: str | None = None
    course_id: str | None = None
    context_text: str | None = None

    # ---- 1. Support both JSON API and HTMX form posts ----
    if request.is_json:
        try:
            payload = request.get_json(silent=True) or {}
            req_data = HomeworkRequest(**payload)
            problem_statement = req_data.problem_statement
            # If your HomeworkRequest model has these fields, they will be filled.
            # If not, they remain None and that's fine.
            course_id = getattr(req_data, "course_id", None)
            context_text = getattr(req_data, "context", None)
        except ValidationError as e:
            return jsonify({"error": e.errors()}), 400
        except Exception as e:
            logger.error(f"Failed to parse homework request (JSON): {e}", exc_info=True)
            return jsonify({"error": "Invalid request format"}), 400
    else:
        # HTMX / form-encoded path (matches your template)
        problem_statement = (request.form.get("problem_statement") or "").strip()
        course_id = request.form.get("course_id")
        context_text = request.form.get("context")

        if not problem_statement:
            return jsonify({"error": "problem_statement is required"}), 400

    # ---- 2. Create task + publish to queue ----
    try:
        task_id = create_task()

        message_body = json.dumps({
            "task_id": task_id,
            "queue_name": "homework",
            "problem_statement": problem_statement,
            # Optional extras for the worker:
            "course_id": course_id,
            "context": context_text,
        })

        publish_task(queue_name='homework', body=message_body)
        logger.info(f"Published homework task {task_id}")

        response = TaskResponse(
            task_id=task_id,
            status="PENDING",
            polling_url=url_for('task_bp.get_task_status_route', task_id=task_id, _external=True),
        )

        return jsonify(response.to_dict()), 202
    except Exception as e:
        logger.error(f"Failed to create homework task: {e}", exc_info=True)
        return jsonify({"error": "Failed to create task"}), 500
