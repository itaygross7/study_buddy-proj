import json
import os
import pika
import time
from tenacity import retry, stop_after_attempt, wait_fixed
from pymongo import MongoClient

from src.infrastructure.config import settings
from src.infrastructure.repositories import MongoTaskRepository, MongoDocumentRepository
from src.services import summary_service, flashcards_service, assess_service, homework_service
from src.services import glossary_service
from src.domain.models.db_models import TaskStatus
from src.domain.errors import DocumentNotFoundError
from sb_utils.logger_utils import logger
from src.utils.file_processing import process_file_from_path

# --- Database Connection for Worker ---
# This is established once when the worker starts.
try:
    mongo_client = MongoClient(settings.MONGO_URI)
    db_conn = mongo_client.get_database()
    task_repo = MongoTaskRepository(db_conn)
    doc_repo = MongoDocumentRepository(db_conn)
    logger.info("Worker successfully connected to MongoDB.")
except Exception as e:
    logger.critical(f"Worker failed to connect to MongoDB on startup: {e}", exc_info=True)
    exit(1)  # Exit if we can't connect to the DB

# --- Task Processing Logic with Retry ---


@retry(wait=wait_fixed(5), stop=stop_after_attempt(3))
def process_task(body: bytes):
    """
    Processes a single task with retry logic for transient errors.
    """
    data = json.loads(body)
    task_id = data['task_id']
    queue_name = data['queue_name']

    logger.info(f"[Worker] Starting processing for task {task_id} from queue '{queue_name}'")
    task_repo.update_status(task_id, TaskStatus.PROCESSING)

    if queue_name == 'file_processing':
        # NEW: Handle file processing asynchronously
        document_id = data['document_id']
        temp_path = data['temp_path']
        filename = data['filename']
        
        try:
            # Process the file to extract text
            text_content = process_file_from_path(temp_path, filename)
            
            # Update document with extracted text
            doc = doc_repo.get_by_id(document_id)
            if doc:
                doc.content_text = text_content
                doc_repo.update(doc)
                logger.info(f"[Worker] Successfully processed file '{filename}' for document {document_id}")
            
            # Clean up temp file and directory
            import shutil
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                temp_dir = os.path.dirname(temp_path)
                if os.path.exists(temp_dir) and os.path.isdir(temp_dir):
                    # Use shutil.rmtree for robust cleanup
                    try:
                        shutil.rmtree(temp_dir)
                    except OSError:
                        # If rmtree fails, try removing if empty
                        if not os.listdir(temp_dir):
                            os.rmdir(temp_dir)
            except Exception as cleanup_error:
                logger.warning(f"[Worker] Failed to cleanup temp file: {cleanup_error}")
            
            result_id = document_id
            
        except Exception as e:
            logger.error(f"[Worker] File processing failed for '{filename}': {e}", exc_info=True)
            # Update document with error message
            doc = doc_repo.get_by_id(document_id)
            if doc:
                doc.content_text = f"[Error processing file: {str(e)}]"
                doc_repo.update(doc)
            raise
    
    elif queue_name == 'summarize':
        doc = doc_repo.get_by_id(data['document_id'])
        if not doc:
            raise DocumentNotFoundError(f"Document {data['document_id']} not found.")
        result_id = summary_service.generate_summary(doc.id, doc.content_text, db_conn)
        
        # Background task: Extract glossary terms from the document
        try:
            user_id = data.get('user_id', '')
            course_id = data.get('course_id', '')
            if user_id and course_id:
                logger.info(f"[Worker] Extracting glossary terms for document {doc.id}")
                glossary_service.extract_terms_from_content(
                    doc.id, doc.content_text, course_id, user_id, 
                    doc.filename, db_conn
                )
        except Exception as e:
            logger.warning(f"[Worker] Glossary extraction failed (non-critical): {e}")


    elif queue_name == 'flashcards':
        doc = doc_repo.get_by_id(data['document_id'])
        if not doc:
            raise DocumentNotFoundError(f"Document {data['document_id']} not found.")
        result_id = flashcards_service.generate_flashcards(doc.id, doc.content_text, data['num_cards'], db_conn)

    elif queue_name == 'assess':
        doc = doc_repo.get_by_id(data['document_id'])
        if not doc:
            raise DocumentNotFoundError(f"Document {data['document_id']} not found.")
        result_id = assess_service.generate_assessment(
            doc.id, doc.content_text, data['num_questions'], data['question_type'], db_conn)

    elif queue_name == 'homework':
        result_id = homework_service.solve_homework_problem(data['problem_statement'])

    else:
        raise ValueError(f"Unknown queue: {queue_name}")

    task_repo.update_status(task_id, TaskStatus.COMPLETED, result_id=result_id)
    logger.info(f"[Worker] Successfully completed task {task_id}")

# --- RabbitMQ Consumer ---


def main_callback(ch, method, properties, body):
    """
    Main callback that wraps task processing in a final try/except block.
    """
    task_id = json.loads(body).get('task_id', 'unknown')
    try:
        process_task(body)
    except Exception as e:
        logger.error(f"[Worker] Task {task_id} failed permanently after retries: {e}", exc_info=True)
        # Sanitize error message before saving
        safe_error_msg = "An unexpected error occurred during processing."
        if isinstance(e, DocumentNotFoundError):
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

            queues = ['file_processing', 'summarize', 'flashcards', 'assess', 'homework']
            for q in queues:
                channel.queue_declare(queue=q, durable=True)
                channel.basic_qos(prefetch_count=1)
                channel.basic_consume(queue=q, on_message_callback=main_callback)

            logger.info("Worker is waiting for messages. To exit press CTRL+C")
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"RabbitMQ connection failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            logger.critical(f"An unrecoverable error occurred in the worker: {e}", exc_info=True)
            break


if __name__ == '__main__':
    main()
