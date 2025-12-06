#!/usr/bin/env python3
"""
Health Monitor Script for StudyBuddy Application

This script monitors the health of the StudyBuddy application by periodically
checking the /health endpoint and sending email alerts when the app is unhealthy.

Usage:
    python scripts/health_monitor.py

Environment Variables Required:
    - HEALTH_CHECK_URL (optional): URL to check, defaults to http://localhost:5000/health
    - ADMIN_EMAIL: Email address to send alerts to
    - MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD: SMTP settings
    - HEALTH_CHECK_INTERVAL (optional): Check interval in seconds, defaults to 60
"""
import os
import sys
import time
import requests
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.config import settings
from sb_utils.logger_utils import logger
from src.services.email_service import send_email


class HealthMonitor:
    """Monitors application health and sends email alerts."""

    def __init__(self):
        self.health_url = os.getenv('HEALTH_CHECK_URL', 'http://localhost:5000/health')
        self.check_interval = int(os.getenv('HEALTH_CHECK_INTERVAL', '60'))
        self.max_consecutive_failures = int(os.getenv('MAX_CONSECUTIVE_FAILURES', '3'))
        self.consecutive_failures = 0
        self.last_alert_time = None
        self.alert_cooldown = int(os.getenv('ALERT_COOLDOWN_SECONDS', '3600'))  # 1 hour default
        self.is_unhealthy = False

    def check_health(self) -> tuple[bool, str]:
        """
        Check application health.
        
        Returns:
            tuple: (is_healthy: bool, message: str)
        """
        try:
            response = requests.get(self.health_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'healthy':
                    return True, "Application is healthy"
                else:
                    return False, f"Application reports unhealthy status: {data}"
            else:
                return False, f"Health check returned status code {response.status_code}"
                
        except requests.exceptions.Timeout:
            return False, "Health check timed out after 10 seconds"
        except requests.exceptions.ConnectionError:
            return False, "Could not connect to application (connection error)"
        except requests.exceptions.RequestException as e:
            return False, f"Health check request failed: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error during health check: {str(e)}"

    def should_send_alert(self) -> bool:
        """Check if enough time has passed since last alert."""
        if self.last_alert_time is None:
            return True
        
        time_since_last_alert = time.time() - self.last_alert_time
        return time_since_last_alert >= self.alert_cooldown

    def send_health_alert(self, message: str):
        """Send email alert about unhealthy application."""
        if not settings.ADMIN_EMAIL:
            logger.warning("ADMIN_EMAIL not configured, cannot send health alert")
            return

        if not self.should_send_alert():
            logger.info(f"Skipping alert (cooldown period active). Next alert in {self.alert_cooldown - (time.time() - self.last_alert_time):.0f}s")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        html_body = f"""
        <!DOCTYPE html>
        <html dir="ltr" lang="en">
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #FFF8E6; margin: 0; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #FAF3D7; border-radius: 16px; padding: 30px; border: 2px solid #DC2626; }}
                .header {{ text-align: center; margin-bottom: 20px; color: #DC2626; }}
                .content {{ color: #4B2E16; line-height: 1.8; }}
                .alert-box {{ background: #FEE2E2; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #DC2626; }}
                .info {{ background: #FFF8E6; padding: 10px; border-radius: 4px; margin: 5px 0; font-size: 14px; }}
                .footer {{ margin-top: 20px; text-align: center; color: #8B5E34; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>🚨 StudyBuddy Health Alert</h2>
                </div>
                <div class="content">
                    <div class="alert-box">
                        <p><strong>⚠️ Application Health Check Failed</strong></p>
                        <p>The StudyBuddy application is reporting an unhealthy status.</p>
                    </div>
                    <div class="info">
                        <p><strong>Timestamp:</strong> {timestamp}</p>
                        <p><strong>Health Check URL:</strong> {self.health_url}</p>
                        <p><strong>Consecutive Failures:</strong> {self.consecutive_failures}</p>
                        <p><strong>Error Details:</strong> {message}</p>
                    </div>
                    <p style="margin-top: 20px;"><strong>Recommended Actions:</strong></p>
                    <ul>
                        <li>Check application logs for errors</li>
                        <li>Verify all services are running (app, worker, MongoDB, RabbitMQ)</li>
                        <li>Check system resources (CPU, memory, disk space)</li>
                        <li>Restart services if necessary using: <code>docker-compose restart</code></li>
                    </ul>
                </div>
                <div class="footer">
                    <p>This is an automated alert from StudyBuddy Health Monitor</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        StudyBuddy Health Alert
        ========================

        The StudyBuddy application is reporting an unhealthy status.

        Timestamp: {timestamp}
        Health Check URL: {self.health_url}
        Consecutive Failures: {self.consecutive_failures}
        Error Details: {message}

        Recommended Actions:
        - Check application logs for errors
        - Verify all services are running
        - Check system resources
        - Restart services if necessary

        This is an automated alert from StudyBuddy Health Monitor
        """

        try:
            success = send_email(
                settings.ADMIN_EMAIL,
                f"[ALERT] StudyBuddy Application Unhealthy",
                html_body,
                text_body
            )
            if success:
                self.last_alert_time = time.time()
                logger.info(f"Health alert sent to {settings.ADMIN_EMAIL}")
            else:
                logger.error("Failed to send health alert email")
        except Exception as e:
            logger.error(f"Error sending health alert: {e}", exc_info=True)

    def send_recovery_notification(self):
        """Send email notification when application recovers."""
        if not settings.ADMIN_EMAIL:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        html_body = f"""
        <!DOCTYPE html>
        <html dir="ltr" lang="en">
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #FFF8E6; margin: 0; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #FAF3D7; border-radius: 16px; padding: 30px; border: 2px solid #10B981; }}
                .header {{ text-align: center; margin-bottom: 20px; color: #10B981; }}
                .content {{ color: #4B2E16; line-height: 1.8; }}
                .success-box {{ background: #D1FAE5; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #10B981; }}
                .info {{ background: #FFF8E6; padding: 10px; border-radius: 4px; margin: 5px 0; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>✅ StudyBuddy Health Recovered</h2>
                </div>
                <div class="content">
                    <div class="success-box">
                        <p><strong>✓ Application Has Recovered</strong></p>
                        <p>The StudyBuddy application is now reporting a healthy status.</p>
                    </div>
                    <div class="info">
                        <p><strong>Recovery Timestamp:</strong> {timestamp}</p>
                        <p><strong>Health Check URL:</strong> {self.health_url}</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        try:
            send_email(
                settings.ADMIN_EMAIL,
                f"[RECOVERED] StudyBuddy Application Healthy",
                html_body
            )
            logger.info(f"Recovery notification sent to {settings.ADMIN_EMAIL}")
        except Exception as e:
            logger.error(f"Error sending recovery notification: {e}", exc_info=True)

    def run_once(self):
        """Run a single health check."""
        is_healthy, message = self.check_health()
        
        if is_healthy:
            if self.is_unhealthy:
                # Application recovered
                logger.info("Application has recovered")
                self.send_recovery_notification()
                self.is_unhealthy = False
            
            self.consecutive_failures = 0
            logger.info("Health check passed")
        else:
            self.consecutive_failures += 1
            logger.warning(f"Health check failed ({self.consecutive_failures}/{self.max_consecutive_failures}): {message}")
            
            if self.consecutive_failures >= self.max_consecutive_failures:
                if not self.is_unhealthy:
                    # First time crossing threshold
                    logger.error(f"Application is unhealthy after {self.consecutive_failures} consecutive failures")
                    self.send_health_alert(message)
                    self.is_unhealthy = True
                elif self.should_send_alert():
                    # Still unhealthy and cooldown expired
                    logger.error(f"Application still unhealthy (failure count: {self.consecutive_failures})")
                    self.send_health_alert(message)

    def run_continuous(self):
        """Run continuous health monitoring."""
        logger.info(f"Starting health monitor for {self.health_url}")
        logger.info(f"Check interval: {self.check_interval}s, Max failures: {self.max_consecutive_failures}, Alert cooldown: {self.alert_cooldown}s")
        
        while True:
            try:
                self.run_once()
            except Exception as e:
                logger.error(f"Error in health monitor loop: {e}", exc_info=True)
            
            time.sleep(self.check_interval)


def main():
    """Main entry point."""
    # Validate configuration
    if not settings.ADMIN_EMAIL:
        logger.error("ADMIN_EMAIL is not configured. Health alerts cannot be sent.")
        logger.error("Please set ADMIN_EMAIL in your .env file")
        sys.exit(1)

    if not settings.MAIL_USERNAME or not settings.MAIL_PASSWORD:
        logger.error("Email is not configured. Health alerts cannot be sent.")
        logger.error("Please configure MAIL_USERNAME, MAIL_PASSWORD, and MAIL_SERVER in your .env file")
        sys.exit(1)

    monitor = HealthMonitor()
    
    # Check if running in one-shot mode
    if '--once' in sys.argv:
        logger.info("Running in one-shot mode")
        monitor.run_once()
    else:
        # Continuous monitoring
        try:
            monitor.run_continuous()
        except KeyboardInterrupt:
            logger.info("Health monitor stopped by user")
            sys.exit(0)


if __name__ == '__main__':
    main()
