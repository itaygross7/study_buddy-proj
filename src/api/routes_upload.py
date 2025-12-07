import uuid
import os
import tempfile
from flask import Blueprint, request, jsonify, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from src.infrastructure.database import db
from src.infrastructure.repositories import MongoDocumentRepository, MongoTaskRepository
from src.infrastructure.rabbitmq import publish_task
from src.domain.models.db_models import Document, Task, DocumentStatus
from src.services.file_service import get_file_service
from sb_utils.logger_utils import logger

upload_bp = Blueprint('upload_bp', __name__)

@upload_bp.route('/files', methods=['POST'])
@login_required
def upload_files_route():
    """
    (CORRECTED) This route ONLY handles saving the file and creating a
    'file_processing' task. It does not trigger any AI.
    """
    user_id = current_user.id
    course_id = request.form.get('course_id', 'default')
    file = request.files.get('file')

    if not file or not file.filename:
        return jsonify({"error": "No file selected"}), 400

    try:
        file_service = get_file_service()
        filename = secure_filename(file.filename)
        gridfs_id = file_service.save_file(file, user_id, course_id)

        doc_repo = MongoDocumentRepository(db)
        document = Document(
            _id=str(uuid.uuid4()),
            user_id=user_id,
            course_id=course_id,
            filename=filename,
            content_text="[File uploaded, pending processing...]",
            status=DocumentStatus.UPLOADED,
            gridfs_id=str(gridfs_id)
        )
        doc_repo.create(document)

        task_repo = MongoTaskRepository(db)
        task = task_repo.create(user_id=user_id, document_id=document.id, task_type='file_processing')

        publish_task(
            queue_name='file_processing',
            task_body={"task_id": task.id, "document_id": document.id}
        )
        
        logger.info(f"File '{filename}' queued for processing. Task ID: {task.id}")
        
        # Return the polling URL for the FILE PROCESSING task.
        return jsonify({
            "status": "processing_file",
            "polling_url": url_for('task_bp.get_task_status_route', task_id=task.id)
        }), 202

    except Exception as e:
        logger.error(f"File upload failed for user {user_id}: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred."}), 500
