"""
Automated health monitoring and service recovery daemon.
"""
import time
import schedule
import subprocess
import tempfile
import os
from datetime import datetime, timezone
from pathlib import Path

from src.services.health_service import get_comprehensive_health
from src.services.email_service import send_email
from src.infrastructure.config import settings
from src.infrastructure.database import db
from sb_utils.logger_utils import logger

# Configuration
HEALTH_CHECK_INTERVAL_MINUTES = 5
DAILY_REPORT_TIME = "08:00"
MAX_CONSECUTIVE_FAILURES = 3
RESTART_COOLDOWN_MINUTES = 10

# State tracking
consecutive_failures = {
    "mongodb": 0,
    "rabbitmq": 0,
    "ai_models": 0,
    "file_upload": 0,
    "git": 0
}
last_restart_time = None
last_email_sent = {}


def create_test_file() -> str:
    test_content = "StudyBuddy Health Check Test"
    test_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', prefix='health_test_', delete=False, encoding='utf-8')
    test_file.write(test_content)
    test_file.close()
    return test_file.name


def test_real_file_upload() -> dict:
    test_file_path = None
    document_id = None
    try:
        from app import create_app
        app = create_app()
        with app.app_context():
            test_file_path = create_test_file()
            logger.info(f"Created test file: {test_file_path}")
            from src.utils.file_processing import process_file_from_path
            extracted_text = process_file_from_path(test_file_path, "health_test.txt")
            if not extracted_text:
                return {"status": "failed", "error": "Text extraction failed"}
            
            from src.domain.models.db_models import Document
            import uuid
            document_id = str(uuid.uuid4())
            test_doc = Document(_id=document_id, user_id="health_check_system", course_id="health_check", filename="health_test.txt", content_text=extracted_text)
            db.documents.insert_one(test_doc.to_dict())
            logger.info(f"Created test document: {document_id}")
            
            stored_doc = db.documents.find_one({"_id": document_id})
            if not stored_doc:
                return {"status": "failed", "error": "Document not found after insertion"}
            
            return {"status": "success"}
    except Exception as e:
        logger.error(f"File upload test failed: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}
    finally:
        if test_file_path and os.path.exists(test_file_path):
            os.remove(test_file_path)
            logger.info(f"Cleaned up test file: {test_file_path}")
        if document_id:
            try:
                db.documents.delete_one({"_id": document_id})
                logger.info(f"Cleaned up test document: {document_id}")
            except Exception as e:
                logger.error(f"Failed to clean up test document {document_id}: {e}")


def restart_docker_service(service_name: str) -> bool:
    try:
        logger.warning(f"Attempting to restart service: {service_name}")
        result = subprocess.run(['docker', 'restart', f'studybuddy_{service_name}'], capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            logger.info(f"Successfully restarted service: {service_name}")
            time.sleep(10)
            return True
        else:
            logger.error(f"Failed to restart {service_name}: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error restarting {service_name}: {e}", exc_info=True)
        return False


def should_restart_services() -> bool:
    global last_restart_time
    if last_restart_time is None:
        return True
    return (datetime.now(timezone.utc) - last_restart_time).total_seconds() > (RESTART_COOLDOWN_MINUTES * 60)


def send_critical_alert(component: str, error_details: str):
    # ... (implementation remains the same)
    pass

def send_daily_health_report():
    # ... (implementation remains the same)
    pass


def perform_health_check_and_recovery():
    logger.info("=== Starting periodic health check ===")
    try:
        from app import create_app
        app = create_app()
        with app.app_context():
            health_report = get_comprehensive_health(db)
            upload_test = test_real_file_upload()
            
            for component, status_data in health_report["components"].items():
                if status_data.get("status") == "unhealthy":
                    consecutive_failures[component] += 1
                    logger.warning(f"Component {component} unhealthy ({consecutive_failures[component]}/{MAX_CONSECUTIVE_FAILURES})")
                    if consecutive_failures[component] >= MAX_CONSECUTIVE_FAILURES and should_restart_services():
                        # ... (restart logic remains the same)
                        pass
                else:
                    if consecutive_failures[component] > 0:
                        logger.info(f"Component {component} recovered")
                    consecutive_failures[component] = 0
            
            if upload_test.get("status") == "failed":
                logger.error(f"File upload test failed: {upload_test.get('error')}")
            
            logger.info(f"Health check complete: {health_report['overall_status']}")
    except Exception as e:
        logger.error(f"Health check routine failed: {e}", exc_info=True)


def start_monitoring_daemon():
    logger.info("Starting StudyBuddy Health Monitoring Daemon")
    schedule.every(HEALTH_CHECK_INTERVAL_MINUTES).minutes.do(perform_health_check_and_recovery)
    schedule.every().day.at(DAILY_REPORT_TIME).do(send_daily_health_report)
    perform_health_check_and_recovery()
    logger.info("Monitoring daemon started successfully")
    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == '__main__':
    start_monitoring_daemon()
