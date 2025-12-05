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
    Handles file uploads OR text input, extracts/processes text, and saves it to MongoDB.
    """
    # Determine user_id: prioritize authenticated user, then form value, then default
    if current_user.is_authenticated:
        user_id = current_user.id
    else:
        user_id = request.form.get('user_id', '') or 'anonymous'

    # Get course_id from form or use default
    course_id = request.form.get('course_id', '') or 'default'
    
    # Check if text was provided directly
    text_input = request.form.get('text', '').strip()
    
    if text_input:
        # Handle direct text input
        try:
            doc_repo = MongoDocumentRepository(db)
            document = Document(
                _id=str(uuid.uuid4()),
                user_id=user_id,
                course_id=course_id,
                filename="text_input.txt",
                content_text=text_input
            )
            doc_repo.create(document)
            
            logger.info(f"Text content uploaded by user {user_id} to course {course_id}")
            return jsonify({"document_id": document.id, "filename": "text_input.txt"}), 201
            
        except Exception as e:
            logger.error(f"Error processing text input: {e}", exc_info=True)
            return jsonify({"error": "An internal error occurred while processing the text."}), 500
    
    # Handle file upload
    if 'file' not in request.files:
        return jsonify({"error": "No file or text provided"}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({"error": "No file selected"}), 400

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

        logger.info(f"File '{filename}' uploaded by user {user_id} to course {course_id}")
        return jsonify({"document_id": document.id, "filename": filename}), 201

    except InvalidFileTypeError as e:
        logger.warning(f"Invalid file type uploaded ('{filename}'): {e}")
        return jsonify({"error": str(e)}), 415
    except Exception as e:
        logger.error(f"Internal server error during upload of '{filename}': {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred while processing the file."}), 500
