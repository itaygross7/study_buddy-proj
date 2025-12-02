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
        req_data = FlashcardsRequest(**request.json)
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    task_id = create_task()

    message_body = json.dumps({
        "task_id": task_id,
        "queue_name": "flashcards",
        "document_id": req_data.document_id,
        "num_cards": req_data.num_cards
    })

    publish_task(queue_name='flashcards', body=message_body)
    logger.info(f"Published flashcards task {task_id} for document {req_data.document_id}")

    response = TaskResponse(
        task_id=task_id,
        status="PENDING",
        polling_url=url_for('task_bp.get_task_status_route', task_id=task_id, _external=True)
    )

    return jsonify(response.to_dict()), 202
