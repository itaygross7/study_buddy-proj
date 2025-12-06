import uuid
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from src.infrastructure.database import db
from src.infrastructure.repositories import MongoDocumentRepository
from src.domain.models.db_models import Document, DocumentStatus
from src.services.file_service import get_file_service # IMPORT THE FACTORY
from sb_utils.logger_utils import logger

upload_bp = Blueprint('upload_bp', __name__)

@upload_bp.route('/', methods=['POST'])
@login_required
def upload_route():
    """
    Handles both direct text input and file uploads.
    """
    user_id = current_user.id
    course_id = request.form.get('course_id', 'default')
    text_input = request.form.get('text', '').strip()
    file = request.files.get('file')

    doc_repo = MongoDocumentRepository(db)

    try:
        if text_input:
            file_service = get_file_service() # Get service instance safely
            document = Document(
                _id=str(uuid.uuid4()),
                user_id=user_id,
                course_id=course_id,
                filename="הדבקת טקסט.txt",
                content_text="", # No full text stored here
                status=DocumentStatus.READY,
                gridfs_id=None
            )
            gridfs_id = file_service.fs.put(text_input.encode('utf-8'), filename=document.filename, metadata={"owner_id": user_id, "course_id": course_id})
            document.gridfs_id = str(gridfs_id)
            doc_repo.create(document)
            return jsonify({"document_id": document.id, "filename": document.filename, "status": "completed"}), 201

        elif file and file.filename:
            file_service = get_file_service() # Get service instance safely
            filename = secure_filename(file.filename)
            gridfs_id = file_service.save_file(file, user_id, course_id)

            document = Document(
                _id=str(uuid.uuid4()),
                user_id=user_id,
                course_id=course_id,
                filename=filename,
                content_text="[File uploaded, pending processing]",
                status=DocumentStatus.UPLOADED,
                gridfs_id=str(gridfs_id)
            )
            doc_repo.create(document)
            # This response is now handled by the tool-specific trigger routes
            return jsonify({"document_id": document.id, "filename": filename, "status": "uploaded"}), 201
        
        else:
            return jsonify({"error": "No input provided"}), 400

    except Exception as e:
        logger.error(f"Error in upload_route for user {user_id}: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred."}), 500
