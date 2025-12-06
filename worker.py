import json
import os
import shutil
from tenacity import retry, stop_after_attempt, wait_fixed
from pymongo import MongoClient
import pika
import time

from src.infrastructure.config import settings
from src.infrastructure.repositories import MongoTaskRepository, MongoDocumentRepository
from src.services import summary_service, flashcards_service, assess_service
from src.services.file_service import FileService # Import the class, not the factory
from src.domain.models.db_models import TaskStatus
from src.domain.errors import DocumentNotFoundError
from sb_utils.logger_utils import logger
from src.utils.file_processing import process_uploaded_file
from src.utils.smart_parser import create_smart_repository

# --- Database Connection ---
try:
    mongo_client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
    db_conn = mongo_client.get_database()
    db_conn.command('ping')
    task_repo = MongoTaskRepository(db_conn)
    doc_repo = MongoDocumentRepository(db_conn)
    # CORRECTED: Create a FileService instance with the real DB connection
    file_service = FileService(db_conn)
    logger.info("Worker successfully connected to MongoDB and services initialized.")
except Exception as e:
    logger.critical(f"Worker failed to connect to MongoDB on startup: {e}", exc_info=True)
    exit(1)

# --- Task Processing Logic ---
@retry(wait=wait_fixed(5), stop=stop_after_attempt(3), reraise=True)
def process_task(body: bytes):
    data = json.loads(body)
    task_id = data['task_id']
    queue_name = data['queue_name']

    logger.info(f"Starting processing for task {task_id}", extra={"queue": queue_name, "task_id": task_id})
    task_repo.update_status(task_id, TaskStatus.PROCESSING)

    document_id = data['document_id']
    doc = doc_repo.get_by_id(document_id)
    if not doc:
        raise DocumentNotFoundError(f"Document {document_id} not found for task {task_id}.")

    text_content = doc.content_text
    if doc.gridfs_id:
        logger.info(f"Worker is processing file from GridFS for doc {doc.id}")
        file_stream = file_service.get_file_stream(doc.gridfs_id)
        if not file_stream:
            raise FileNotFoundError(f"File with GridFS ID {doc.gridfs_id} not found.")
        
        text_content = process_uploaded_file(file_stream)
        doc.content_text = "" # Clear placeholder
        doc_repo.update(doc)
        
        try:
            create_smart_repository(document_id, text_content)
        except Exception as e:
            logger.warning(f"Smart repository creation failed for doc {document_id}, but task will continue. Error: {e}")

    if queue_name == 'summarize':
        result_id = summary_service.generate_summary(doc.id, text_content, db_conn)
    elif queue_name == 'flashcards':
        result_id = flashcards_service.generate_flashcards(doc.id, text_content, data['num_cards'], db_conn)
    elif queue_name == 'assess':
        result_id = assess_service.generate_assessment(doc.id, text_content, data['num_questions'], data['question_type'], db_conn)
    else:
        raise ValueError(f"Unknown AI queue for worker: {queue_name}")

    task_repo.update_status(task_id, TaskStatus.COMPLETED, result_id=result_id)
    logger.info(f"Successfully completed task {task_id}", extra={"task_id": task_id})

# ... (The rest of the worker file remains the same) ...
def main_callback(ch, method, properties, body):
    # ...
    process_task(body)
    # ...

def main():
    # ...
    pass

if __name__ == '__main__':
    main()
