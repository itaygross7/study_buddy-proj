import json
from flask import Blueprint, request, jsonify, url_for
from pydantic import ValidationError

from src.domain.models.api_models import FlashcardsRequest, TaskResponse
from src.services.task_service import create_task
from src.infrastructure.rabbitmq import publish_task
from sb_utils.logger_utils import logger

flashcards_bp = Blueprint('flashcards_bp', __name__)


@flashcards_bp.route('/', methods=['POST'])
def trigger_flashcards():
    """Triggers the flashcard generation task."""
    try:
        req_data = FlashcardsRequest(**(request.json or {}))
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400
    except Exception as e:
        logger.error(f"Failed to parse flashcards request: {e}", exc_info=True)
        return jsonify({"error": "Invalid request format"}), 400

    try:
        task_id = create_task()

        task_body = {
            "task_id": task_id,
            "document_id": req_data.document_id,
            "num_cards": req_data.num_cards,
        }
        # Optional query/focus if defined in model
        query = getattr(req_data, "query", None) or getattr(req_data, "focus", None)
        if query:
            task_body["query"] = query

        publish_task(queue_name='flashcards', task_body=task_body)
        logger.info(f"Published flashcards task {task_id} for document {req_data.document_id}")

        response = TaskResponse(
            task_id=task_id,
            status="PENDING",
            polling_url=url_for('task_bp.get_task_status_route', task_id=task_id, _external=True),
        )

        return jsonify(response.to_dict()), 202
    except Exception as e:
        logger.error(f"Failed to create flashcards task: {e}", exc_info=True)
        return jsonify({"error": "Failed to create task"}), 500
