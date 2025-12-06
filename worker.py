import json
import os
import shutil
from tenacity import retry, stop_after_attempt, wait_fixed
from pymongo import MongoClient
import pika
import time

from src.infrastructure.config import settings
from src.infrastructure.repositories import MongoTaskRepository, MongoDocumentRepository
from src.services import summary_service, flashcards_service, assess_service, homework_service
from src.services.file_service import FileService
from src.domain.models.db_models import TaskStatus, DocumentStatus
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
    file_service = FileService(db_conn) # Initialize with the real DB connection
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

    document_id = data.get('document_id')
    if not document_id:
        # Handle tasks like homework_helper that don't have a document
        if queue_name == 'homework':
            result_id = homework_service.solve_homework_problem(data['problem_statement'])
            task_repo.update_status(task_id, TaskStatus.COMPLETED, result_id=result_id)
            logger.info(f"Successfully completed task {task_id}", extra={"task_id": task_id})
            return
        else:
            raise ValueError(f"Task {task_id} is missing a document_id.")

    doc = doc_repo.get_by_id(document_id)
    if not doc:
        raise DocumentNotFoundError(f"Document {document_id} not found for task {task_id}.")

    text_content = doc.content_text

    # --- THIS IS THE CORE FIX ---
    # If the document has a GridFS ID, it means it's a file that needs processing.
    if doc.gridfs_id and doc.status == DocumentStatus.UPLOADED:
        logger.info(f"Worker is processing file from GridFS for doc {doc.id}")
        file_stream = file_service.get_file_stream(doc.gridfs_id)
        if not file_stream:
            raise FileNotFoundError(f"File with GridFS ID {doc.gridfs_id} not found.")
        
        # 1. Process the file to get text (this handles PDF, DOCX, PNG, etc.)
        text_content = process_uploaded_file(file_stream)
        
        # 2. Create the smart repository (pickle the chunks)
        try:
            create_smart_repository(document_id, text_content)
        except Exception as e:
            logger.warning(f"Smart repository creation failed for doc {document_id}, but task will continue. Error: {e}")

        # 3. Update the document status to READY and clear placeholder text
        doc.status = DocumentStatus.READY
        doc.content_text = "" # The chunks are the source of truth now
        doc_repo.update(doc)
        
        # 4. Delete the original large file from GridFS to save space
        file_service.delete_file(doc.gridfs_id)
        logger.info(f"Original GridFS file {doc.gridfs_id} deleted after successful processing.")
    # --- END OF CORE FIX ---

    # Now, perform the AI Generation step using the final document content.
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

# --- RabbitMQ Consumer ---
def main_callback(ch, method, properties, body):
    task_id = "unknown"
    try:
        task_id = json.loads(body).get('task_id', 'unknown')
        process_task(body)
    except Exception as e:
        logger.error(f"Task {task_id} failed permanently after retries", extra={"task_id": task_id, "error": str(e)}, exc_info=True)
        safe_error_msg = "An unexpected error occurred during processing."
        if isinstance(e, (DocumentNotFoundError, ValueError, FileNotFoundError)):
            safe_error_msg = str(e)
        task_repo.update_status(task_id, TaskStatus.FAILED, error_message=safe_error_msg)
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)

def main():
    while True:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(settings.RABBITMQ_URI))
            channel = connection.channel()
            logger.info("Worker connected to RabbitMQ.")

            # The worker listens to the AI queues. It no longer needs a separate file_processing queue.
            queues = ['summarize', 'flashcards', 'assess', 'homework']
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
