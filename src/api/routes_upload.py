import uuid
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

from src.infrastructure.database import db
from src.infrastructure.repositories import MongoDocumentRepository
from src.domain.models.db_models import Document
from src.utils.file_processing import process_uploaded_file
from src.domain.errors import InvalidFileTypeError
from sb_utils.logger_utils import logger

upload_bp = Blueprint('upload_bp', __name__)
doc_repo = MongoDocumentRepository(db)

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

    filename = secure_filename(file.filename)
    try:
        text_content = process_uploaded_file(file)
        
        document = Document(
            _id=str(uuid.uuid4()),
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
