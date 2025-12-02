import json
import pika
import time
from tenacity import retry, stop_after_attempt, wait_fixed
from pymongo import MongoClient

from src.infrastructure.config import settings
from src.infrastructure.repositories import MongoTaskRepository, MongoDocumentRepository
from src.services import summary_service, flashcards_service, assess_service, homework_service
from src.domain.models.db_models import TaskStatus
from src.domain.errors import DocumentNotFoundError
from sb_utils.logger_utils import logger

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

    if queue_name == 'summarize':
        doc = doc_repo.get_by_id(data['document_id'])
        if not doc:
            raise DocumentNotFoundError(f"Document {data['document_id']} not found.")
        result_id = summary_service.generate_summary(doc.id, doc.content_text, db_conn)

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

            queues = ['summarize', 'flashcards', 'assess', 'homework']
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
