import json
import pika

from src.infrastructure.config import settings
from sb_utils.logger_utils import logger


def publish_task(queue_name: str, task_body: dict) -> None:
    """
    Publish a task to RabbitMQ.

    - Declares the queue as durable.
    - Injects `queue_name` into the payload so the worker can route logic.
    """
    payload = dict(task_body)
    payload["queue_name"] = queue_name  # 👈 worker relies on this

    params = pika.URLParameters(settings.RABBITMQ_URI)
    connection = None
    try:
        connection = pika.BlockingConnection(params)
        channel = connection.channel()

        # Durable queue
        channel.queue_declare(queue=queue_name, durable=True)

        channel.basic_publish(
            exchange="",
            routing_key=queue_name,
            body=json.dumps(payload),
            properties=pika.BasicProperties(
                delivery_mode=2,  # persistent
            ),
        )

        logger.info(
            "Published task to queue '%s' with payload keys: %s",
            queue_name,
            list(payload.keys()),
        )

    except Exception as e:
        logger.error(
            "Failed to publish task to queue '%s': %s",
            queue_name,
            e,
            exc_info=True,
        )
        raise
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass
