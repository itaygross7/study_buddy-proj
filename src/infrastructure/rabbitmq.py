import pika
from .config import settings

def get_rabbitmq_connection():
    """
    Establishes a connection to RabbitMQ.
    """
    params = pika.URLParameters(settings.RABBITMQ_URI)
    connection = pika.BlockingConnection(params)
    return connection

def publish_task(queue_name: str, body: str):
    """
    Publishes a task to the specified RabbitMQ queue.
    """
    connection = get_rabbitmq_connection()
    channel = connection.channel()
    
    # Ensure the queue exists
    channel.queue_declare(queue=queue_name, durable=True)
    
    channel.basic_publish(
        exchange='',
        routing_key=queue_name,
        body=body,
        properties=pika.BasicProperties(
            delivery_mode=2,  # make message persistent
        ))
    
    connection.close()
