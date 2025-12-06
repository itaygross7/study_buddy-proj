import uuid
from flask import Blueprint, request, jsonify, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from src.infrastructure.database import db
from src.infrastructure.repositories import MongoDocumentRepository, MongoTaskRepository
from src.infrastructure.rabbitmq import publish_task
from src.domain.models.db_models import Document, Task
from src.services.file_service import get_file_service # IMPORT THE FACTORY
from sb_utils.logger_utils import logger

summary_bp = Blueprint('summary_bp', __name__)

@summary_bp.route('/trigger', methods=['POST'])
@login_required
def trigger_summary():
    user_id = current_user.id
    course_id = request.form.get('course_id', 'default')
    text_input = request.form.get('text', '').strip()
    file = request.files.get('file')
    document_id = request.form.get('document_id')

    task_repo = MongoTaskRepository(db)
    doc_repo = MongoDocumentRepository(db)
    task_body = {}

    try:
        if document_id:
            doc = doc_repo.get_by_id(document_id)
            if not doc or doc.user_id != user_id: return jsonify({"error": "Document not found"}), 404
            task_body['document_id'] = document_id

        elif text_input:
            document = Document(_id=str(uuid.uuid4()), user_id=user_id, course_id=course_id, filename="הדבקת טקסט.txt", content_text=text_input, gridfs_id=None)
            doc_repo.create(document)
            task_body['document_id'] = document.id

        elif file and file.filename:
            file_service = get_file_service() # GET THE INSTANCE HERE
            filename = secure_filename(file.filename)
            gridfs_id = file_service.save_file(file, user_id, course_id)

            document = Document(_id=str(uuid.uuid4()), user_id=user_id, course_id=course_id, filename=filename, content_text="[File content stored in GridFS]", gridfs_id=str(gridfs_id))
            doc_repo.create(document)
            task_body['document_id'] = document.id
        
        else:
            return jsonify({"error": "No input provided"}), 400

        task = task_repo.create(user_id=user_id, document_id=task_body['document_id'], task_type='summary')
        task_body['task_id'] = task.id

        publish_task(queue_name='summarize', task_body=task_body)

        return jsonify({
            "status": "processing",
            "polling_url": url_for('task_bp.get_task_status_route', task_id=task.id)
        }), 202

    except Exception as e:
        logger.error(f"Error in trigger_summary for user {user_id}: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred."}), 500
