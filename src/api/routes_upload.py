import uuid
from flask import Blueprint, request, jsonify
from flask_login import current_user

from werkzeug.utils import secure_filename

from src.infrastructure.database import db
from src.infrastructure.repositories import MongoDocumentRepository
from src.domain.models.db_models import Document
from src.utils.file_processing import process_uploaded_file
from src.domain.errors import InvalidFileTypeError
from sb_utils.logger_utils import logger

upload_bp = Blueprint('upload_bp', __name__)


@upload_bp.route('/', methods=['POST'])
def upload_file_route():
    """
    Handles file uploads, extracts text, and saves it to MongoDB.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({"error": "No file selected"}), 400

    # Get user_id and course_id from request or authenticated user
    user_id = request.form.get('user_id', '')
    course_id = request.form.get('course_id', '')

    # If user is authenticated, use their ID
    if current_user.is_authenticated:
        user_id = current_user.id

    # If no user_id or course_id provided, use defaults for testing
    if not user_id:
        user_id = 'anonymous'
    if not course_id:
        course_id = 'default'

    filename = secure_filename(file.filename)
    try:
        text_content = process_uploaded_file(file)

        doc_repo = MongoDocumentRepository(db)
        document = Document(
            _id=str(uuid.uuid4()),
            user_id=user_id,
            course_id=course_id,
            filename=filename,
            content_text=text_content
        )
        doc_repo.create(document)

        return jsonify({"document_id": document.id, "filename": filename}), 201

    except InvalidFileTypeError as e:
        logger.warning(f"Invalid file type uploaded ('{filename}'): {e}")
        return jsonify({"error": str(e)}), 415
    except Exception as e:
        logger.error(f"Internal server error during upload of '{filename}': {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred while processing the file."}), 500
