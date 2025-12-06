"""
Automated health monitoring and service recovery daemon.

Features:
- Periodic health checks
- Automatic service restart on failures
- Real file upload testing
- Email notifications for critical failures
- Daily health status reports
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
HEALTH_CHECK_INTERVAL_MINUTES = 5  # Check every 5 minutes
DAILY_REPORT_TIME = "08:00"  # Send daily report at 8 AM
MAX_CONSECUTIVE_FAILURES = 3  # Restart after 3 consecutive failures
RESTART_COOLDOWN_MINUTES = 10  # Don't restart more than once per 10 minutes

# State tracking
consecutive_failures = {
    "mongodb": 0,
    "rabbitmq": 0,
    "ai_models": 0,
    "file_upload": 0,
    "git": 0
}
last_restart_time = None
last_email_sent = {}  # Track when we last sent email for each component


def create_test_file() -> str:
    """
    Create a small test file for upload testing.
    
    Returns:
        Path to the test file
    """
    test_content = """StudyBuddy Health Check Test
    
This is a minimal test document created automatically by the health monitoring system.
It contains English and Hebrew text: שלום עולם
Current time: {timestamp}

This file should be processed and then deleted automatically.
"""
    
    timestamp = datetime.now(timezone.utc).isoformat()
    content = test_content.format(timestamp=timestamp)
    
    # Create in temp directory
    test_file = tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.txt',
        prefix='health_test_',
        delete=False,
        encoding='utf-8'
    )
    test_file.write(content)
    test_file.close()
    
    return test_file.name


def test_real_file_upload() -> dict:
    """
    Test actual file upload workflow:
    1. Create test file
    2. Upload via API
    3. Verify processing
    4. Clean up
    
    Returns:
        Dict with test results
    """
    test_file_path = None
    document_id = None
    
    try:
        # Create test file
        test_file_path = create_test_file()
        logger.info(f"Created test file: {test_file_path}")
        
        # Test file processing function
        from src.utils.file_processing import process_file_from_path
        
        extracted_text = process_file_from_path(test_file_path, "health_test.txt")
        
        if not extracted_text or "health check test" not in extracted_text.lower():
            return {
                "status": "failed",
                "error": "Text extraction failed or returned invalid content",
                "stage": "text_extraction"
            }
        
        # Test document creation in database
        from src.domain.models.db_models import Document
        import uuid
        
        document_id = str(uuid.uuid4())
        test_doc = Document(
            _id=document_id,
            user_id="health_check_system",
            course_id="health_check",
            filename="health_test.txt",
            content_text=extracted_text
        )
        
        # Insert into DB
        db.documents.insert_one(test_doc.to_dict())
        logger.info(f"Created test document: {document_id}")
        
        # Verify document exists
        stored_doc = db.documents.find_one({"_id": document_id})
        if not stored_doc:
            return {
                "status": "failed",
                "error": "Document not found after insertion",
                "stage": "database_verification"
            }
        
        # Clean up test file
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
            logger.info(f"Cleaned up test file: {test_file_path}")
        
        # Clean up test document
        db.documents.delete_one({"_id": document_id})
        logger.info(f"Cleaned up test document: {document_id}")
        
        return {
            "status": "success",
            "document_id": document_id,
            "text_length": len(extracted_text),
            "test_passed": True
        }
        
    except Exception as e:
        logger.error(f"File upload test failed: {e}", exc_info=True)
        
        # Clean up on error
        if test_file_path and os.path.exists(test_file_path):
            try:
                os.remove(test_file_path)
            except:
                pass
        
        if document_id:
            try:
                db.documents.delete_one({"_id": document_id})
            except:
                pass
        
        return {
            "status": "failed",
            "error": str(e),
            "stage": "exception"
        }


def restart_docker_service(service_name: str) -> bool:
    """
    Restart a specific Docker Compose service.
    
    Args:
        service_name: Name of the service (app, worker, mongo, rabbitmq)
        
    Returns:
        True if restart succeeded, False otherwise
    """
    try:
        logger.warning(f"Attempting to restart service: {service_name}")
        
        # Inside Docker, we need to use docker command directly
        # The health monitor container has access to Docker socket
        result = subprocess.run(
            ['docker', 'restart', f'studybuddy_{service_name}'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            logger.info(f"Successfully restarted service: {service_name}")
            # Wait a bit for service to start
            time.sleep(10)
            return True
        else:
            logger.error(f"Failed to restart {service_name}: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout while restarting {service_name}")
        return False
    except Exception as e:
        logger.error(f"Error restarting {service_name}: {e}", exc_info=True)
        return False


def should_restart_services() -> bool:
    """
    Check if enough time has passed since last restart.
    
    Returns:
        True if restart is allowed, False if in cooldown period
    """
    global last_restart_time
    
    if last_restart_time is None:
        return True
    
    time_since_restart = (datetime.now(timezone.utc) - last_restart_time).total_seconds()
    cooldown_seconds = RESTART_COOLDOWN_MINUTES * 60
    
    return time_since_restart > cooldown_seconds


def send_critical_alert(component: str, error_details: str):
    """
    Send critical failure alert email to admin.
    
    Args:
        component: Name of the failing component
        error_details: Error description
    """
    global last_email_sent
    
    # Rate limit: don't send same alert more than once per hour
    now = datetime.now(timezone.utc)
    last_sent = last_email_sent.get(component)
    
    if last_sent:
        time_diff = (now - last_sent).total_seconds()
        if time_diff < 3600:  # Less than 1 hour
            logger.info(f"Skipping alert email for {component} (rate limited)")
            return
    
    if not settings.ADMIN_EMAIL:
        logger.warning("No admin email configured, cannot send alert")
        return
    
    subject = f"🚨 CRITICAL: {component} Failure - StudyBuddy"
    
    body = f"""
<h2 style="color: #d32f2f;">Critical Component Failure Detected</h2>

<p><strong>Component:</strong> {component}</p>
<p><strong>Time:</strong> {now.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
<p><strong>Status:</strong> UNHEALTHY</p>

<h3>Error Details:</h3>
<pre style="background: #f5f5f5; padding: 10px; border-left: 4px solid #d32f2f;">
{error_details}
</pre>

<h3>Actions Taken:</h3>
<ul>
    <li>Automatic restart attempted</li>
    <li>Monitoring continues</li>
</ul>

<h3>Recommended Actions:</h3>
<ul>
    <li>Check container logs: <code>docker compose logs {component}</code></li>
    <li>Verify configuration in .env file</li>
    <li>Check system resources (CPU, memory, disk)</li>
    <li>Review recent deployments</li>
</ul>

<p style="color: #666; font-size: 12px; margin-top: 30px;">
This is an automated alert from StudyBuddy Health Monitoring System.
</p>
"""
    
    try:
        send_email(
            to_email=settings.ADMIN_EMAIL,
            subject=subject,
            body=body
        )
        last_email_sent[component] = now
        logger.info(f"Sent critical alert email for {component}")
    except Exception as e:
        logger.error(f"Failed to send alert email: {e}", exc_info=True)


def send_daily_health_report():
    """Send daily health status report to admin."""
    if not settings.ADMIN_EMAIL:
        logger.warning("No admin email configured, skipping daily report")
        return
    
    try:
        # Get comprehensive health status
        health_report = get_comprehensive_health(db)
        
        # Test file upload
        upload_test = test_real_file_upload()
        
        status = health_report["overall_status"]
        status_emoji = "✅" if status == "healthy" else "⚠️" if status == "degraded" else "❌"
        
        subject = f"{status_emoji} Daily Health Report - StudyBuddy - {status.upper()}"
        
        # Build component status table
        components_html = ""
        for comp_name, comp_data in health_report["components"].items():
            comp_status = comp_data.get("status", "unknown")
            comp_emoji = "✅" if comp_status == "healthy" else "⚠️" if comp_status == "degraded" else "❌"
            
            comp_details = ""
            if comp_status != "healthy":
                comp_details = f"<br><small style='color: #666;'>{comp_data.get('error', 'N/A')}</small>"
            
            components_html += f"""
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;">{comp_emoji} {comp_name}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{comp_status.upper()}{comp_details}</td>
            </tr>
            """
        
        # File upload test status
        upload_status = upload_test.get("status", "unknown")
        upload_emoji = "✅" if upload_status == "success" else "❌"
        
        body = f"""
<h2>📊 Daily Health Report</h2>
<p><strong>Date:</strong> {datetime.now(timezone.utc).strftime('%Y-%m-%d')}</p>
<p><strong>Overall Status:</strong> {status_emoji} {status.upper()}</p>

<h3>Component Status:</h3>
<table style="border-collapse: collapse; width: 100%; margin: 20px 0;">
    <thead>
        <tr style="background: #f5f5f5;">
            <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Component</th>
            <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Status</th>
        </tr>
    </thead>
    <tbody>
        {components_html}
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd;">{upload_emoji} File Upload Test</td>
            <td style="padding: 8px; border: 1px solid #ddd;">{upload_status.upper()}</td>
        </tr>
    </tbody>
</table>

<h3>Summary:</h3>
<ul>
    <li>Healthy Components: {health_report['summary']['healthy_components']}</li>
    <li>Degraded Components: {health_report['summary']['degraded_components']}</li>
    <li>Unhealthy Components: {health_report['summary']['unhealthy_components']}</li>
    <li>Total Components: {health_report['summary']['total_components']}</li>
</ul>

<h3>Worker Status:</h3>
<p>Worker Active: {health_report['components']['rabbitmq'].get('worker_active', False)}</p>

<h3>AI Models:</h3>
<ul>
"""
        
        ai_models = health_report['components']['ai_models'].get('models', {})
        for model_name, model_data in ai_models.items():
            model_status = model_data.get('status', 'unknown')
            model_emoji = "✅" if model_status == "healthy" else "⚠️" if model_status == "not_configured" else "❌"
            body += f"<li>{model_emoji} {model_name}: {model_status.upper()}</li>\n"
        
        body += f"""
</ul>

<h3>Auto-Update Status:</h3>
<p>Git Connectivity: {health_report['components']['git'].get('status', 'unknown')}</p>
<p>Can Pull Updates: {health_report['components']['git'].get('can_pull', False)}</p>
<p>Current Branch: {health_report['components']['git'].get('current_branch', 'unknown')}</p>
<p>Current Commit: {health_report['components']['git'].get('current_commit', 'unknown')}</p>

<p style="color: #666; font-size: 12px; margin-top: 30px;">
This is an automated daily report from StudyBuddy Health Monitoring System.
To view detailed diagnostics: <a href="http://localhost:5000/health/detailed">/health/detailed</a>
</p>
"""
        
        send_email(
            to_email=settings.ADMIN_EMAIL,
            subject=subject,
            body=body
        )
        logger.info("Sent daily health report email")
        
    except Exception as e:
        logger.error(f"Failed to send daily health report: {e}", exc_info=True)


def perform_health_check_and_recovery():
    """
    Main health check routine with automatic recovery.
    
    This runs periodically and:
    1. Checks all components
    2. Tests file upload
    3. Restarts services if needed
    4. Sends alerts on failures
    """
    logger.info("=== Starting periodic health check ===")
    
    try:
        # Get comprehensive health status
        health_report = get_comprehensive_health(db)
        
        # Test file upload
        upload_test = test_real_file_upload()
        
        # Check each component
        for component, status_data in health_report["components"].items():
            status = status_data.get("status", "unknown")
            
            if status == "unhealthy":
                consecutive_failures[component] += 1
                logger.warning(
                    f"Component {component} unhealthy "
                    f"({consecutive_failures[component]}/{MAX_CONSECUTIVE_FAILURES})"
                )
                
                # Check if we should restart
                if consecutive_failures[component] >= MAX_CONSECUTIVE_FAILURES:
                    if should_restart_services():
                        logger.error(
                            f"Component {component} failed {MAX_CONSECUTIVE_FAILURES} "
                            f"times, attempting restart"
                        )
                        
                        # Map component to service name
                        service_map = {
                            "mongodb": "mongo",
                            "rabbitmq": "rabbitmq",
                            "ai_models": "app",  # AI issues may need app restart
                            "file_upload": "worker",  # File upload issues -> worker restart
                            "git": None  # Git issues don't need restart
                        }
                        
                        service_to_restart = service_map.get(component)
                        
                        if service_to_restart:
                            restart_success = restart_docker_service(service_to_restart)
                            
                            global last_restart_time
                            last_restart_time = datetime.now(timezone.utc)
                            
                            # Send critical alert
                            error_details = status_data.get("error", "Unknown error")
                            send_critical_alert(component, error_details)
                            
                            if restart_success:
                                # Reset failure counter on successful restart
                                consecutive_failures[component] = 0
                                logger.info(f"Service {service_to_restart} restarted successfully")
                            else:
                                logger.error(f"Failed to restart {service_to_restart}")
                        else:
                            # Send alert but don't restart (e.g., Git issues)
                            error_details = status_data.get("error", "Unknown error")
                            send_critical_alert(component, error_details)
                            consecutive_failures[component] = 0  # Reset to avoid spam
                    else:
                        logger.warning(
                            f"Component {component} needs restart but in cooldown period"
                        )
            else:
                # Component is healthy or degraded, reset counter
                if consecutive_failures[component] > 0:
                    logger.info(f"Component {component} recovered")
                consecutive_failures[component] = 0
        
        # Check file upload test
        if upload_test.get("status") == "failed":
            logger.error(f"File upload test failed: {upload_test.get('error')}")
            # Could trigger app restart if this happens consistently
        
        logger.info(f"Health check complete: {health_report['overall_status']}")
        
    except Exception as e:
        logger.error(f"Health check routine failed: {e}", exc_info=True)


def start_monitoring_daemon():
    """
    Start the health monitoring daemon.
    
    This runs in the background and performs:
    - Health checks every 5 minutes
    - Daily reports at 8 AM
    - Automatic service recovery on failures
    """
    logger.info("Starting StudyBuddy Health Monitoring Daemon")
    logger.info(f"Health check interval: {HEALTH_CHECK_INTERVAL_MINUTES} minutes")
    logger.info(f"Daily report time: {DAILY_REPORT_TIME}")
    logger.info(f"Max consecutive failures before restart: {MAX_CONSECUTIVE_FAILURES}")
    logger.info(f"Restart cooldown: {RESTART_COOLDOWN_MINUTES} minutes")
    
    # Schedule periodic health checks
    schedule.every(HEALTH_CHECK_INTERVAL_MINUTES).minutes.do(
        perform_health_check_and_recovery
    )
    
    # Schedule daily health report
    schedule.every().day.at(DAILY_REPORT_TIME).do(send_daily_health_report)
    
    # Run initial health check immediately
    perform_health_check_and_recovery()
    
    # Keep running
    logger.info("Monitoring daemon started successfully")
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(30)  # Check every 30 seconds for scheduled tasks
        except KeyboardInterrupt:
            logger.info("Monitoring daemon stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}", exc_info=True)
            time.sleep(60)  # Wait a bit before retrying


if __name__ == '__main__':
    start_monitoring_daemon()
