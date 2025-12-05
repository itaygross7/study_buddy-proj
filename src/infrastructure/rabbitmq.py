import pika
import json
from .config import settings
from sb_utils.logger_utils import logger

def publish_task(queue_name: str, task_body: dict):
    """
    Publishes a task to the specified RabbitMQ queue.

    Args:
        queue_name: The name of the queue to publish to.
        task_body: A dictionary representing the message body.
    """
    try:
        connection = pika.BlockingConnection(pika.URLParameters(settings.RABBITMQ_URI))
        channel = connection.channel()
        
        # Ensure the queue exists and is durable
        channel.queue_declare(queue=queue_name, durable=True)
        
        # Add queue_name to the body for the worker
        task_body['queue_name'] = queue_name
        
        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(task_body),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
            )
        )
        logger.info(f"Published task {task_body.get('task_id')} to queue '{queue_name}'")
        connection.close()
    except Exception as e:
        logger.error(f"Failed to publish task to RabbitMQ: {e}", exc_info=True)
        # Re-raise the exception so the caller knows the operation failed
        raise
