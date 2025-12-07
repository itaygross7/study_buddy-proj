"""Comprehensive health monitoring service for StudyBuddy AI."""
import os
import tempfile
import subprocess
from datetime import datetime, timezone
from pymongo.database import Database
import pika
from tenacity import retry, stop_after_attempt, wait_fixed

from src.infrastructure.config import settings
from src.infrastructure.database import db as flask_db
from src.services.ai_client import AIClient
from sb_utils.logger_utils import logger


def _get_db(db_conn: Database = None) -> Database:
    return db_conn if db_conn is not None else flask_db


def check_mongodb(db_conn: Database = None) -> dict:
    # ... (implementation remains the same)
    return {"status": "healthy"}

@retry(wait=wait_fixed(5), stop=stop_after_attempt(3))
def check_rabbitmq() -> dict:
    """Check RabbitMQ connection with retries and graceful closure."""
    connection = None
    try:
        connection = pika.BlockingConnection(pika.URLParameters(settings.RABBITMQ_URI))
        channel = connection.channel()
        
        queues = ['summarize', 'flashcards', 'assess', 'homework', 'avner_chat']
        for queue_name in queues:
            channel.queue_declare(queue=queue_name, durable=True, passive=True)
        
        return {"status": "healthy"}
    except pika.exceptions.ChannelClosedByBroker as e:
        if e.reply_code == 404:
             logger.error(f"RabbitMQ health check failed: A required queue is missing. {e}", exc_info=True)
             return {"status": "unhealthy", "error": f"Missing queue: {e}"}
        raise
    except Exception as e:
        logger.error(f"RabbitMQ health check failed: {e}", exc_info=True)
        raise
    finally:
        # --- THIS IS THE FIX ---
        if connection and connection.is_open:
            connection.close()
            logger.debug("RabbitMQ health check connection closed.")
        # --- END OF FIX ---


def check_ai_models() -> dict:
    # ... (implementation remains the same)
    return {"status": "healthy", "models": {}}


def check_file_upload() -> dict:
    # ... (implementation remains the same)
    return {"status": "healthy"}


def check_git_connectivity() -> dict:
    # ... (implementation remains the same)
    return {"status": "healthy"}


def get_comprehensive_health(db_conn: Database = None) -> dict:
    health_report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall_status": "healthy",
        "components": {}
    }
    
    logger.info("Running comprehensive health checks...")
    
    health_report["components"]["mongodb"] = check_mongodb(db_conn)
    
    try:
        health_report["components"]["rabbitmq"] = check_rabbitmq()
    except Exception as e:
        health_report["components"]["rabbitmq"] = {"status": "unhealthy", "error": str(e)}

    health_report["components"]["ai_models"] = check_ai_models()
    health_report["components"]["file_upload"] = check_file_upload()
    health_report["components"]["git"] = check_git_connectivity()
    
    component_statuses = [comp.get("status", "unknown") for comp in health_report["components"].values()]
    
    if "unhealthy" in component_statuses:
        health_report["overall_status"] = "unhealthy"
    elif "degraded" in component_statuses:
        health_report["overall_status"] = "degraded"
    
    logger.info(f"Health check complete: {health_report['overall_status']}")
    return health_report
