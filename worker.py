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
from src.services import summary_service, flashcards_service, assess_service, homework_service, glossary_service, avner_service
from src.services.file_service import FileService
from src.domain.models.db_models import TaskStatus, DocumentStatus
from src.domain.errors import DocumentNotFoundError
from sb_utils.logger_utils import logger
from src.utils.file_processing import process_uploaded_file
from src.utils.document_chunking import index_document_chunks

# --- Database Connection ---
try:
    mongo_client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
    db_conn = mongo_client.get_database()
    db_conn.command('ping')
    task_repo = MongoTaskRepository(db_conn)
    doc_repo = MongoDocumentRepository(db_conn)
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

    # This is the only task that doesn't need a document
    if queue_name == 'homework':
        result_id = homework_service.solve_homework_problem(data['problem_statement'])
        task_repo.update_status(task_id, TaskStatus.COMPLETED, result_id=result_id)
        logger.info(f"Successfully completed task {task_id}", extra={"task_id": task_id})
        return

    document_id = data.get('document_id')
    if not document_id:
        raise ValueError(f"Task {task_id} of type {queue_name} is missing a document_id.")

    doc = doc_repo.get_by_id(document_id)
    if not doc:
        raise DocumentNotFoundError(f"Document {document_id} not found for task {task_id}.")

    text_content = doc.content_text
    if doc.gridfs_id and doc.status != DocumentStatus.READY:
        logger.info(f"Worker is processing file from GridFS for doc {doc.id}")
        file_stream = file_service.get_file_stream(doc.gridfs_id)
        if not file_stream:
            raise FileNotFoundError(f"File with GridFS ID {doc.gridfs_id} not found.")
        
        text_content = process_uploaded_file(file_stream)
        
        try:
            index_document_chunks(db=db_conn, document_id=doc.id, filename=doc.filename, text=text_content, course_id=doc.course_id, user_id=doc.user_id)
        except Exception as e:
            logger.warning(f"Chunk indexing failed for doc {document_id}: {e}")

        doc.status = DocumentStatus.READY
        doc.content_text = text_content # Store the processed text
        doc_repo.update(doc)
        
        # We no longer delete the GridFS file, it's the source of truth
        # file_service.delete_file(doc.gridfs_id) 
    
    result_id = None
    if queue_name == 'summarize':
        result_id = summary_service.generate_summary(doc.id, text_content, db_conn)
        try:
            glossary_service.extract_terms_from_content(doc.id, text_content, doc.course_id, doc.user_id, doc.filename, db_conn)
        except Exception as e:
            logger.warning(f"Glossary extraction failed (non-critical): {e}")

    elif queue_name == 'flashcards':
        result_id = flashcards_service.generate_flashcards(doc.id, text_content, data['num_cards'], db_conn)

    elif queue_name == 'assess':
        result_id = assess_service.generate_assessment(doc.id, text_content, data['num_questions'], data['question_type'], db_conn)
    
    elif queue_name == 'avner_chat':
        answer = avner_service.answer_question(question=data['question'], context=text_content, language=data.get('language', 'he'), baby_mode=data.get('baby_mode', False), user_id=data.get('user_id', ''), db_conn=db_conn)
        result_doc = {"_id": str(uuid.uuid4()), "answer": answer}
        db_conn.avner_results.insert_one(result_doc)
        result_id = result_doc["_id"]
    else:
        raise ValueError(f"Unknown AI queue for worker: {queue_name}")

    if result_id:
        task_repo.update_status(task_id, TaskStatus.COMPLETED, result_id=result_id)
        logger.info(f"Successfully completed task {task_id}", extra={"task_id": task_id})
    else:
        task_repo.update_status(task_id, TaskStatus.FAILED, error_message="Task finished without a result.")

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

            queues = ['summarize', 'flashcards', 'assess', 'homework', 'avner_chat']
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
