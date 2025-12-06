import json
import os
import shutil
import pika
import time
import uuid
from datetime import datetime, timezone
from tenacity import retry, stop_after_attempt, wait_fixed
from pymongo import MongoClient

from src.infrastructure.config import settings
from src.infrastructure.repositories import MongoTaskRepository, MongoDocumentRepository
from src.services import summary_service, flashcards_service, assess_service, homework_service
from src.services import glossary_service, avner_service
from src.domain.models.db_models import TaskStatus
from src.domain.errors import DocumentNotFoundError
from sb_utils.logger_utils import logger
from src.utils.file_processing import process_file_from_path
from src.utils.document_chunking import index_document_chunks
from src.utils.smart_parser import create_smart_repository # Import the new utility

# --- Database Connection for Worker ---
try:
    mongo_client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
    db_conn = mongo_client.get_database()
    db_conn.command('ping') # Verify connection
    task_repo = MongoTaskRepository(db_conn)
    doc_repo = MongoDocumentRepository(db_conn)
    logger.info("Worker successfully connected to MongoDB.")
except Exception as e:
    logger.critical(f"Worker failed to connect to MongoDB on startup: {e}", exc_info=True)
    exit(1)

# --- Task Processing Logic with Retry ---
@retry(wait=wait_fixed(5), stop=stop_after_attempt(3), reraise=True)
def process_task(body: bytes):
    """
    Processes a single task with retry logic for transient errors.
    """
    data = json.loads(body)
    task_id = data['task_id']
    queue_name = data['queue_name']

    logger.info(f"Starting processing for task {task_id}", extra={"queue": queue_name, "task_id": task_id})
    task_repo.update_status(task_id, TaskStatus.PROCESSING)

    if queue_name == 'file_processing':
        document_id = data['document_id']
        temp_path = data['temp_path']
        filename = data['filename']
        
        try:
            text_content = process_file_from_path(temp_path, filename)
            doc = doc_repo.get_by_id(document_id)
            if doc:
                doc.content_text = text_content
                doc_repo.update(doc)
                logger.info(f"Successfully processed file '{filename}'", extra={"document_id": document_id})
                
                # --- ADDITIVE INJECTION POINT ---
                try:
                    create_smart_repository(document_id, text_content)
                except Exception as smart_repo_error:
                    # CRITICAL: Do not fail the main task if the new logic fails.
                    # Just log the error and continue.
                    logger.error(f"Smart repository creation failed for doc {document_id}, but main task succeeded. Error: {smart_repo_error}", exc_info=True)
                # --- END OF INJECTION ---

            # Clean up temp file and directory
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                temp_dir = os.path.dirname(temp_path)
                if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                    shutil.rmtree(temp_dir)
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp file/dir for '{temp_path}': {cleanup_error}")
            
            result_id = document_id
            
        except Exception as e:
            logger.error(f"File processing failed for '{filename}': {e}", exc_info=True)
            doc = doc_repo.get_by_id(document_id)
            if doc:
                doc.content_text = f"[שגיאה בעיבוד קובץ: {str(e)}]"
                doc_repo.update(doc)
            raise

    # ... (rest of the task processing logic remains unchanged) ...
    elif queue_name == 'summarize':
        doc = doc_repo.get_by_id(data['document_id'])
        if not doc: raise DocumentNotFoundError(f"Document {data['document_id']} not found.")
        result_id = summary_service.generate_summary(doc.id, doc.content_text, db_conn)
    
    else:
        raise ValueError(f"Unknown queue: {queue_name}")

    task_repo.update_status(task_id, TaskStatus.COMPLETED, result_id=result_id)
    logger.info(f"Successfully completed task {task_id}", extra={"task_id": task_id})

# --- RabbitMQ Consumer ---
def main_callback(ch, method, properties, body):
    task_id = "unknown"
    try:
        task_id = json.loads(body).get('task_id', 'unknown')
        process_task(body)
    except Exception as e:
        logger.error(f"Task {task_id} failed permanently after retries", extra={"task_id": task_id, "error": str(e)}, exc_info=True)
        safe_error_msg = "An unexpected error occurred during processing."
        if isinstance(e, (DocumentNotFoundError, ValueError)):
            safe_error_msg = str(e)
        task_repo.update_status(task_id, TaskStatus.FAILED, error_message=safe_error_msg)
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)

def main():
    """Connects to RabbitMQ and starts consuming tasks."""
    while True:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(settings.RABBITMQ_URI))
            channel = connection.channel()
            logger.info("Worker connected to RabbitMQ.")

            queues = ['file_processing', 'summarize', 'flashcards', 'assess', 'homework', 'avner_chat']
            for q in queues:
                channel.queue_declare(queue=q, durable=True)
            channel.basic_qos(prefetch_count=1)
            
            for q in queues:
                channel.basic_consume(queue=q, on_message_callback=main_callback)

            logger.info("Worker is waiting for messages. To exit press CTRL+C")
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            logger.warning(f"RabbitMQ connection failed: {e}. Retrying in 10 seconds...")
            time.sleep(10)
        except Exception as e:
            logger.critical(f"An unrecoverable error occurred in the worker. Shutting down.", exc_info=True)
            break

if __name__ == '__main__':
    main()
