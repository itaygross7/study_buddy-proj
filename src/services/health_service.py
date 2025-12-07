"""Comprehensive health monitoring service for StudyBuddy AI."""

from __future__ import annotations

import os
import shutil
import smtplib
import socket
import subprocess
import tempfile
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
from typing import Dict, Any, Optional, List

from pymongo.database import Database
import pymongo
import pika
from tenacity import retry, stop_after_attempt, wait_fixed

from src.infrastructure.config import settings
from src.infrastructure.database import db as flask_db
from src.services.ai_client import AIClient
from sb_utils.logger_utils import logger


# ---------------------------------------------------------------------------
# Internal helpers / globals
# ---------------------------------------------------------------------------

def _get_db(db_conn: Optional[Database] = None) -> Database:
    return db_conn if db_conn is not None else flask_db


# Simple in-process alert cooldown to avoid spamming admin
_LAST_ALERT_SENT_AT: Optional[datetime] = None
ALERT_COOLDOWN_SECONDS = 900  # 15 minutes

REQUIRED_RABBITMQ_QUEUES: List[str] = [
    "summarize",
    "flashcards",
    "assess",
    "homework",
    "avner_chat",
]


# ---------------------------------------------------------------------------
# MongoDB health
# ---------------------------------------------------------------------------

def check_mongodb(db_conn: Database = None) -> dict:
    """Check MongoDB connectivity with a simple ping."""
    db = _get_db(db_conn)
    try:
        client: pymongo.MongoClient = db.client  # type: ignore[assignment]
        client.admin.command("ping")
        logger.info("MongoDB health check passed")
        return {"status": "healthy"}
    except Exception as e:  # noqa: BLE001
        logger.error(f"MongoDB health check failed: {e}", exc_info=True)
        return {"status": "unhealthy", "error": str(e)}


# ---------------------------------------------------------------------------
# RabbitMQ health (connection + queues + depth)
# ---------------------------------------------------------------------------

@retry(wait=wait_fixed(5), stop=stop_after_attempt(3))
def _rabbitmq_connection() -> pika.BlockingConnection:
    return pika.BlockingConnection(pika.URLParameters(settings.RABBITMQ_URI))


@retry(wait=wait_fixed(5), stop=stop_after_attempt(3))
def check_rabbitmq() -> dict:
    """
    Check RabbitMQ connection with retries, ensure required queues exist,
    and report basic queue depths.

    IMPORTANT:
    - NO passive=True → if queues are missing, they are created instead of causing
      404 NOT_FOUND errors.
    """
    connection = None
    details: Dict[str, Any] = {"queues": {}}
    status = "healthy"

    try:
        connection = _rabbitmq_connection()
        channel = connection.channel()

        for queue_name in REQUIRED_RABBITMQ_QUEUES:
            # Idempotent: creates the queue if missing, OK if it exists.
            q = channel.queue_declare(queue=queue_name, durable=True)
            message_count = q.method.message_count

            details["queues"][queue_name] = {
                "message_count": message_count,
            }

            # Simple heuristic: many stuck messages = degraded
            if message_count > 100:
                status = "degraded"

        logger.info("RabbitMQ health check passed")
        return {"status": status, "details": details}

    except Exception as e:  # noqa: BLE001
        logger.error(f"RabbitMQ health check failed: {e}", exc_info=True)
        raise
    finally:
        if connection and connection.is_open:
            connection.close()
            logger.debug("RabbitMQ health check connection closed.")


# ---------------------------------------------------------------------------
# AI models / AI client health
# ---------------------------------------------------------------------------

def check_ai_models() -> dict:
    """
    Basic AI health:
    - Can we construct AIClient?
    - Are primary/fallback/available models configured (if exposed)?
    """
    try:
        client = AIClient()
        models_info: Dict[str, Any] = {}

        for attr in ("primary_model", "fallback_model", "available_models"):
            if hasattr(client, attr):
                models_info[attr] = getattr(client, attr)

        logger.info("AI models health check passed")
        return {"status": "healthy", "models": models_info}
    except Exception as e:  # noqa: BLE001
        logger.error(f"AI models health check failed: {e}", exc_info=True)
        return {"status": "unhealthy", "error": str(e)}


# ---------------------------------------------------------------------------
# Filesystem / upload health (including a small PDF)
# ---------------------------------------------------------------------------

def check_file_upload() -> dict:
    """
    Check that the backend can:
    - Create a temporary directory.
    - Write & read a text file.
    - Write & read a small, valid-ish PDF.

    This doesn't run your full processing pipeline but ensures basic FS access,
    which is critical for uploads.
    """
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Text file
            txt_path = os.path.join(tmpdir, "health_check.txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("studybuddy health check\n")

            # 2. Small PDF
            pdf_path = os.path.join(tmpdir, "health_check.pdf")
            pdf_bytes = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT /F1 24 Tf 72 96 Td (StudyBuddy Health PDF) Tj ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000061 00000 n 
0000000114 00000 n 
0000000217 00000 n 
trailer
<< /Root 1 0 R /Size 5 >>
startxref
320
%%EOF
"""
            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)

            # Read back both files
            with open(txt_path, "r", encoding="utf-8") as f:
                _ = f.read()

            with open(pdf_path, "rb") as f:
                _ = f.read(128)

        logger.info("File upload health check passed (text + PDF)")
        return {
            "status": "healthy",
            "details": "Temp text and PDF files created and read successfully",
        }
    except Exception as e:  # noqa: BLE001
        logger.error(f"File upload health check failed: {e}", exc_info=True)
        return {"status": "unhealthy", "error": str(e)}


# ---------------------------------------------------------------------------
# Git connectivity health
# ---------------------------------------------------------------------------

def check_git_connectivity() -> dict:
    """
    Check that:
    - We are inside a git repo.
    - 'git status -sb' works (no catastrophic repo corruption).

    This mostly tells you that the app is running in the repo you think it is.
    """
    try:
        # Check if inside a git repo
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        status = subprocess.run(
            ["git", "status", "-sb"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        logger.info("Git connectivity check passed")
        return {"status": "healthy", "summary": status.stdout.strip()}
    except subprocess.CalledProcessError as e:
        logger.error(f"Git connectivity check failed: {e}", exc_info=True)
        return {"status": "unhealthy", "error": e.stderr or str(e)}
    except FileNotFoundError:
        # git not installed inside container – treat as degraded, not fatal
        logger.warning("Git not found inside container")
        return {"status": "degraded", "error": "git not installed in container"}
    except Exception as e:  # noqa: BLE001
        logger.error(f"Git connectivity check failed: {e}", exc_info=True)
        return {"status": "unhealthy", "error": str(e)}


# ---------------------------------------------------------------------------
# Disk space / basic OS-level health
# ---------------------------------------------------------------------------

def check_disk_space(path: str = "/") -> dict:
    try:
        usage = shutil.disk_usage(path)
        total_gb = round(usage.total / (1024**3), 2)
        free_gb = round(usage.free / (1024**3), 2)
        free_pct = round(usage.free / usage.total * 100, 2)

        status = "healthy"
        if free
