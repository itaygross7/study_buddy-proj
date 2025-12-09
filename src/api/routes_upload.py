import uuid
import os
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from src.infrastructure.database import db
from src.infrastructure.repositories import MongoDocumentRepository, MongoTaskRepository
from src.infrastructure.rabbitmq import publish_task
from src.services.file_service import get_file_service
from sb_utils.logger_utils import logger
from src.domain.models.db_models import Document, Task, DocumentStatus, TaskStatus

upload_bp = Blueprint("upload_bp", __name__)


@upload_bp.route("/files", methods=["POST"])
@login_required
def upload_files_route():
    """Upload one or more files, save to GridFS, create Document + Task."""
    user_id = current_user.id
    course_id = request.form.get("course_id")

    if not course_id:
        return jsonify({"error": "course_id is required"}), 400

    # Multi-file or single-file compatibility
    files = request.files.getlist("files")
    if not files:
        f = request.files.get("file")
        if f:
            files = [f]

    if not files:
        return jsonify({"error": "לא התקבלו קבצים"}), 400

    file_service = get_file_service()
    doc_repo = MongoDocumentRepository(db)
    task_repo = MongoTaskRepository(db)

    created_docs = []
    tasks_created = []

    try:
        for f in files:
            if not f or not f.filename:
                continue

            filename = secure_filename(f.filename)

            # --- FILE SIZE ---
            try:
                pos = f.stream.tell()
                f.stream.seek(0, os.SEEK_END)
                file_size = f.stream.tell()
                f.stream.seek(pos, os.SEEK_SET)
            except Exception:
                file_size = 0

            # --- SAVE TO GRIDFS ---
            gridfs_id = file_service.save_file(f, user_id, course_id)
            # (אם בשלב מאוחר תרצה, תוסיף gridfs_id למודל Document ותשמור אותו גם שם)

            # --- CREATE DOCUMENT MODEL ---
            document = Document(
                id=str(uuid.uuid4()),
                user_id=user_id,
                course_id=course_id,
                filename=filename,
                original_filename=filename,
                content_text="[Processing file…]",
                content_type="file",
                file_size=file_size,
                status=DocumentStatus.UPLOADED,  # משתמשים ב-DocumentStatus
            )

            # --- SAVE DOCUMENT ---
            doc_repo.create(document)

            # --- CREATE TASK ---
            task = Task(
                id=str(uuid.uuid4()),
                user_id=user_id,
                course_id=course_id,
                task_type="file_processing",
                status=TaskStatus.PENDING,
                result_id=None,
            )
            task_repo.create(task)

            # --- SEND TO QUEUE ---
            publish_task(
                queue_name="file_processing",
                task_body={"task_id": task.id, "document_id": document.id}
            )

            created_docs.append(document.id)
            tasks_created.append(task.id)

        return jsonify({
            "status": "processing",
            "files_uploaded": len(created_docs),
            "documents": created_docs,
            "task_ids": tasks_created
        }), 202

    except Exception as e:
        logger.error(f"Upload failed for user {user_id}: {e}", exc_info=True)
        return jsonify({"error": "שגיאה פנימית בשרת"}), 500
