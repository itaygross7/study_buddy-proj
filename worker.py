import json
import os
import shutil
import pika
import time
import uuid
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
            
            # Clean up temp file and directory
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    logger.debug(f"Removed temp file: {temp_path}")
                temp_dir = os.path.dirname(temp_path)
                if os.path.exists(temp_dir) and os.path.isdir(temp_dir) and not os.listdir(temp_dir):
                    shutil.rmtree(temp_dir)
                    logger.debug(f"Removed empty temp directory: {temp_dir}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp file/dir for '{temp_path}': {cleanup_error}")
            
            result_id = document_id # The document ID is the result ID for file processing
            
        except Exception as e:
            logger.error(f"File processing failed for '{filename}': {e}", exc_info=True)
            doc = doc_repo.get_by_id(document_id)
            if doc:
                doc.content_text = f"[שגיאה בעיבוד קובץ: {str(e)}]" # Hebrew error message
                doc_repo.update(doc)
            raise # Re-raise for tenacity

    elif queue_name == 'summarize':
        doc = doc_repo.get_by_id(data['document_id'])
        if not doc: raise DocumentNotFoundError(f"Document {data['document_id']} not found.")
        result_id = summary_service.generate_summary(doc.id, doc.content_text, db_conn)
        
        # Background task: Extract glossary terms from the document
        try:
            user_id = data.get('user_id', '')
            course_id = data.get('course_id', '')
            if user_id and course_id:
                logger.info(f"Extracting glossary terms for document {doc.id}")
                glossary_service.extract_terms_from_content(
                    doc.id, doc.content_text, course_id, user_id, 
                    doc.filename, db_conn
                )
        except Exception as e:
            logger.warning(f"Glossary extraction failed (non-critical): {e}")

    elif queue_name == 'flashcards':
        doc = doc_repo.get_by_id(data['document_id'])
        if not doc: raise DocumentNotFoundError(f"Document {data['document_id']} not found.")
        result_id = flashcards_service.generate_flashcards(doc.id, doc.content_text, data['num_cards'], db_conn)

    elif queue_name == 'assess':
        doc = doc_repo.get_by_id(data['document_id'])
        if not doc: raise DocumentNotFoundError(f"Document {data['document_id']} not found.")
        result_id = assess_service.generate_assessment(
            doc.id, doc.content_text, data['num_questions'], data['question_type'], db_conn)

    elif queue_name == 'homework':
        result_id = homework_service.solve_homework_problem(data['problem_statement'])
    
    elif queue_name == 'avner_chat':
        # Avner chat task - answer questions with context
        question = data['question']
        context = data.get('context', '')
        language = data.get('language', 'he')
        baby_mode = data.get('baby_mode', False)
        user_id = data.get('user_id', '')
        
        answer = avner_service.answer_question(
            question=question,
            context=context,
            language=language,
            baby_mode=baby_mode,
            user_id=user_id,
            db_conn=db_conn
        )
        
        # Store the answer in a simple result document
        from datetime import datetime, timezone
        result_doc = {
            "_id": str(uuid.uuid4()),
            "type": "avner_chat",
            "question": question,
            "answer": answer,
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc)
        }
        db_conn.avner_results.insert_one(result_doc)
        result_id = result_doc["_id"]

    else:
        raise ValueError(f"Unknown queue: {queue_name}")

    task_repo.update_status(task_id, TaskStatus.COMPLETED, result_id=result_id)
    logger.info(f"Successfully completed task {task_id}", extra={"task_id": task_id})

# --- RabbitMQ Consumer ---
def main_callback(ch, method, properties, body):
    """
    Main callback that wraps task processing in a final try/except block.
    """
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
            break # Exit the loop and the script

if __name__ == '__main__':
    main()
