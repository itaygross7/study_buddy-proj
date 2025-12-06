"""Email service for notifications and verification."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from src.infrastructure.config import settings
from sb_utils.logger_utils import logger


def send_email(to_email: str, subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
    """Send an email using SMTP."""
    if not settings.MAIL_USERNAME or not settings.MAIL_PASSWORD:
        logger.warning("Email not configured - MAIL_USERNAME or MAIL_PASSWORD missing")
        logger.warning(f"Attempted to send email to {to_email} with subject: {subject}")
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = settings.MAIL_DEFAULT_SENDER or settings.MAIL_USERNAME
        msg['To'] = to_email

        # Attach text and HTML parts
        if text_body:
            msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        # Connect and send
        with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT) as server:
            if settings.MAIL_USE_TLS:
                server.starttls()
            server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            server.sendmail(msg['From'], to_email, msg.as_string())

        logger.info(f"Email sent successfully to {to_email} - Subject: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}", exc_info=True)
        logger.error(f"Email config - Server: {settings.MAIL_SERVER}:{settings.MAIL_PORT}, TLS: {settings.MAIL_USE_TLS}")
        return False


def send_verification_email(to_email: str, verification_token: str, base_url: str = None) -> bool:
    """Send email verification link."""
    # Use configured BASE_URL if available, otherwise use provided base_url
    url_base = settings.BASE_URL if hasattr(settings, 'BASE_URL') and settings.BASE_URL else base_url
    verify_url = f"{url_base}/auth/verify/{verification_token}"

    html_body = f"""
    <!DOCTYPE html>
    <html dir="rtl" lang="he">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #FFF8E6; margin: 0; padding: 20px; }}
            .container {{ max-width: 500px; margin: 0 auto; background: #FAF3D7; border-radius: 16px; padding: 30px; border: 2px solid #F7D774; }}
            .header {{ text-align: center; margin-bottom: 20px; }}
            .logo {{ font-size: 24px; font-weight: bold; color: #4B2E16; }}
            .content {{ color: #4B2E16; line-height: 1.8; }}
            .button {{ display: inline-block; background: #F2C94C; color: #4B2E16; padding: 12px 30px; border-radius: 12px; text-decoration: none; font-weight: bold; margin: 20px 0; }}
            .footer {{ margin-top: 20px; text-align: center; color: #8B5E34; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">🦫 StudyBuddy</div>
            </div>
            <div class="content">
                <p>שלום!</p>
                <p>תודה שנרשמת ל-StudyBuddy. כדי להשלים את ההרשמה, אנא אמת את כתובת האימייל שלך:</p>
                <p style="text-align: center;">
                    <a href="{verify_url}" class="button">אמת את האימייל</a>
                </p>
                <p>או העתק את הקישור הזה לדפדפן:</p>
                <p style="word-break: break-all; color: #8B5E34;">{verify_url}</p>
            </div>
            <div class="footer">
                <p>לומדים יחד עם אבנר 🦫</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    שלום!

    תודה שנרשמת ל-StudyBuddy.
    כדי להשלים את ההרשמה, אנא אמת את כתובת האימייל שלך בקישור הבא:

    {verify_url}

    לומדים יחד עם אבנר!
    """

    return send_email(to_email, "אמת את האימייל שלך - StudyBuddy", html_body, text_body)


def send_new_user_notification(user_email: str, user_name: str) -> bool:
    """Send notification to admin about new user signup."""
    if not settings.ADMIN_EMAIL:
        return False

    html_body = f"""
    <!DOCTYPE html>
    <html dir="rtl" lang="he">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #FFF8E6; margin: 0; padding: 20px; }}
            .container {{ max-width: 500px; margin: 0 auto; background: #FAF3D7; border-radius: 16px; padding: 30px; border: 2px solid #F7D774; }}
            .header {{ text-align: center; margin-bottom: 20px; }}
            .logo {{ font-size: 24px; font-weight: bold; color: #4B2E16; }}
            .content {{ color: #4B2E16; line-height: 1.8; }}
            .info {{ background: #FFF8E6; padding: 15px; border-radius: 8px; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">🦫 StudyBuddy - הודעת מערכת</div>
            </div>
            <div class="content">
                <p><strong>משתמש חדש נרשם למערכת!</strong></p>
                <div class="info">
                    <p><strong>שם:</strong> {user_name or 'לא צוין'}</p>
                    <p><strong>אימייל:</strong> {user_email}</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    return send_email(settings.ADMIN_EMAIL, f"משתמש חדש נרשם: {user_email}", html_body)


def send_error_notification(error_type: str, error_message: str, details: str = "") -> bool:
    """Send error notification to admin."""
    if not settings.ADMIN_EMAIL:
        logger.warning(f"ADMIN_EMAIL not configured - cannot send error notification for {error_type}")
        return False

    html_body = f"""
    <!DOCTYPE html>
    <html dir="ltr" lang="en">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #FFF8E6; margin: 0; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: #FAF3D7; border-radius: 16px; padding: 30px; border: 2px solid #D97706; }}
            .header {{ text-align: center; margin-bottom: 20px; color: #D97706; }}
            .content {{ color: #4B2E16; line-height: 1.8; }}
            .error-box {{ background: #FEF3CD; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #D97706; }}
            pre {{ background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>⚠️ StudyBuddy Error Alert</h2>
            </div>
            <div class="content">
                <div class="error-box">
                    <p><strong>Error Type:</strong> {error_type}</p>
                    <p><strong>Message:</strong> {error_message}</p>
                </div>
                {f'<pre>{details}</pre>' if details else ''}
            </div>
        </div>
    </body>
    </html>
    """

    result = send_email(settings.ADMIN_EMAIL, f"[StudyBuddy Alert] {error_type}", html_body)
    if not result:
        logger.error(f"Failed to send error notification to {settings.ADMIN_EMAIL} for {error_type}")
    return result
