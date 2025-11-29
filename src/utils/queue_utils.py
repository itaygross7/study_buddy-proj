from celery import Celery
from src.infrastructure.config import settings

# Note: Celery is configured but the main worker.py uses RabbitMQ directly with pika
# This celery_app can be used for future migration to Celery-based workers
celery_app = Celery(
    "studybuddy",
    broker=settings.RABBITMQ_URI,
    backend="rpc://"  # Use RPC for results
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
