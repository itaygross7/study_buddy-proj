from celery import Celery
from ..config.settings import settings

celery_app = Celery(
    "studybuddy",
    broker=settings.REDIS_URI,
    backend=settings.REDIS_URI
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
