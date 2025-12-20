import json
import time

import pika
from tenacity import retry, stop_after_attempt, wait_fixed
from pymongo import MongoClient

from src.infrastructure.config import settings
from src.infrastructure.repositories import MongoTaskRepository
from src.domain.models.db_models import TaskStatus
from src.domain.errors import DocumentNotFoundError
from sb_utils.logger_utils import logger

# Worker task handlers - unified backend architecture
from src.workers.task_handlers import (
    handle_file_processing_task,
    handle_summarize_task,
    handle_flashcards_task,
    handle_assess_task,
    handle_homework_task,
    handle_avner_chat_task,
)

# --- Database Connection ---
try:
    mongo_client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
    db_conn = mongo_client.get_database()
    db_conn.command("ping")

    task_repo = MongoTaskRepository(db_conn)

    logger.info("Worker successfully connected to MongoDB and services initialized.")
except Exception as e:
    logger.critical(f"Worker failed to connect to MongoDB on startup: {e}", exc_info=True)
    exit(1)


# --- Task Processing Logic ---
@retry(wait=wait_fixed(5), stop=stop_after_attempt(3), reraise=True)
def process_task(body: bytes):
    data = json.loads(body)
    task_id = data["task_id"]
    queue_name = data["queue_name"]

    logger.info(
        f"Starting processing for task {task_id}",
        extra={"queue": queue_name, "task_id": task_id},
    )

    # Mark as processing
    task_repo.update_status(task_id, TaskStatus.PROCESSING)

    try:
        # MODE 1: File processing
        if queue_name == "file_processing":
            result_id = handle_file_processing_task(data, db_conn)

        # MODE 2: AI generation with document
        elif queue_name == "summarize":
            result_id = handle_summarize_task(data, db_conn)

        elif queue_name == "flashcards":
            result_id = handle_flashcards_task(data, db_conn)

        elif queue_name == "assess":
            result_id = handle_assess_task(data, db_conn)

        # MODE 3: No-document needed
        elif queue_name == "homework":
            result_id = handle_homework_task(data, db_conn)

        # MODE 4: Protected Avner chat
        elif queue_name == "avner_chat":
            result_id = handle_avner_chat_task(data, db_conn)

        else:
            raise ValueError(f"Unknown queue for worker: {queue_name}")

        task_repo.update_status(task_id, TaskStatus.COMPLETED, result_id=result_id)
        logger.info(
            f"Successfully completed task {task_id}",
            extra={"queue": queue_name, "task_id": task_id},
        )

    except Exception:
        # Let tenacity handle retries; failure is handled in main_callback
        raise


# --- RabbitMQ callback ---
def main_callback(ch, method, properties, body):
    task_id = "unknown"
    try:
        task_id = json.loads(body).get("task_id", "unknown")
        process_task(body)

    except Exception as e:
        logger.error(
            f"Task {task_id} failed permanently after retries",
            extra={"task_id": task_id, "error": str(e)},
            exc_info=True,
        )

        safe_error_msg = "An unexpected error occurred during processing."
        if isinstance(e, (DocumentNotFoundError, ValueError, FileNotFoundError)):
            safe_error_msg = str(e)

        task_repo.update_status(task_id, TaskStatus.FAILED, error_message=safe_error_msg)

    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)


# --- Main Worker Loop ---
def main():
    while True:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(settings.RABBITMQ_URI))
            channel = connection.channel()
            logger.info("Worker connected to RabbitMQ.")

            queues = [
                "file_processing",
                "summarize",
                "flashcards",
                "assess",
                "homework",
                "avner_chat",
            ]

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
        except Exception:
            logger.critical(
                "An unrecoverable error occurred in the worker. Shutting down.",
                exc_info=True,
            )
            break


if __name__ == "__main__":
    main()