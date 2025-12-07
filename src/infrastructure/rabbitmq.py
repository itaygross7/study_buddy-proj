import pika
import json
from .config import settings
from sb_utils.logger_utils import logger

def publish_task(queue_name: str, task_body: dict):
    """
    Publishes a task to the specified RabbitMQ queue, ensuring the connection is closed.
    """
    connection = None  # Initialize connection to None
    try:
        connection = pika.BlockingConnection(pika.URLParameters(settings.RABBITMQ_URI))
        channel = connection.channel()
        
        channel.queue_declare(queue=queue_name, durable=True)
        
        task_body['queue_name'] = queue_name
        
        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(task_body),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        logger.info(f"Published task {task_body.get('task_id')} to queue '{queue_name}'")
    except Exception as e:
        logger.error(f"Failed to publish task to RabbitMQ: {e}", exc_info=True)
        raise
    finally:
        # --- THIS IS THE FIX ---
        # Ensure the connection is always closed gracefully.
        if connection and connection.is_open:
            connection.close()
            logger.debug("RabbitMQ publisher connection closed.")
        # --- END OF FIX ---
