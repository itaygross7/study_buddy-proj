import json
from flask import Blueprint, request, jsonify, url_for
from pydantic import ValidationError

from src.domain.models.api_models import SummarizeRequest, TaskResponse
from src.services.task_service import create_task
from src.infrastructure.rabbitmq import publish_task
from sb_utils.logger_utils import logger

summary_bp = Blueprint('summary_bp', __name__)


@summary_bp.route('/', methods=['POST'])
def trigger_summary():
    """Triggers the summarization task."""
    try:
        req_data = SummarizeRequest(**request.json)
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400
    except Exception as e:
        logger.error(f"Failed to parse summary request: {e}", exc_info=True)
        return jsonify({"error": "Invalid request format"}), 400

    try:
        task_id = create_task()

        message_body = json.dumps({
            "task_id": task_id,
            "queue_name": "summarize",
            "document_id": req_data.document_id
        })

        publish_task(queue_name='summarize', body=message_body)
        logger.info(f"Published summarization task {task_id} for document {req_data.document_id}")

        response = TaskResponse(
            task_id=task_id,
            status="PENDING",
            polling_url=url_for('task_bp.get_task_status_route', task_id=task_id, _external=True)
        )

        return jsonify(response.to_dict()), 202
    except Exception as e:
        logger.error(f"Failed to create summary task: {e}", exc_info=True)
        return jsonify({"error": "Failed to create task"}), 500
