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

# FIXED VERSION — compatible with your existing Document model
@upload_bp.route("/files", methods=["POST"])
@login_required
def upload_files_route():
    user_id = current_user.id
    course_id = request.form.get("course_id", "default")

    files = request.files.getlist("files")
    if not files:
        single_file = request.files.get("file")
        if single_file:
            files = [single_file]

    if not files:
        return jsonify({"error": "לא התקבלו קבצים להעלאה"}), 400

    file_service = get_file_service()
    doc_repo = MongoDocumentRepository(db)
    task_repo = MongoTaskRepository(db)

    created_docs = []
    task_ids = []

    try:
        for f in files:
            if not f or not f.filename:
                continue

            filename = secure_filename(f.filename)

            # Compute size safely
            file_size = getattr(f, "content_length", None)
            if file_size is None:
                try:
                    pos = f.stream.tell()
                    f.stream.seek(0, os.SEEK_END)
                    file_size = f.stream.tell()
                    f.stream.seek(pos, os.SEEK_SET)
                except Exception:
                    file_size = 0

            # Save file
            gridfs_id = file_service.save_file(f, user_id, course_id)

            # Create Document WITHOUT file_size (your model doesn't support it)
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

            # PATCH: Add file_size to DB
            db.documents.update_one(
                {"_id": document.id},
                {"$set": {"file_size": int(file_size or 0)}}
            )

            # Create processing task
            task = task_repo.create(
                user_id=user_id,
                document_id=document.id,
                task_type="file_processing",
            )

            publish_task(
                queue_name="file_processing",
                task_body={"task_id": task.id, "document_id": document.id},
            )

            created_docs.append(document.id)
            task_ids.append(str(task.id))

        if not created_docs:
            return jsonify({"error": "לא נמצאו קבצים תקינים להעלאה"}), 400

        return jsonify({
            "status": "processing_file",
            "files_uploaded": len(created_docs),
            "task_ids": task_ids
        }), 202

    except Exception as e:
        logger.error(f"File upload failed for user {user_id}: {e}", exc_info=True)
        return jsonify({"error": "אירעה שגיאה פנימית. נסה שוב מאוחר יותר."}), 500
