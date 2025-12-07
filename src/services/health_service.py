"""Comprehensive health monitoring service for StudyBuddy AI."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from pymongo.database import Database
import pymongo
import pika
from tenacity import retry, stop_after_attempt, wait_fixed

from src.infrastructure.config import settings
from src.infrastructure.database import db as flask_db
from src.services.ai_client import AIClient
from sb_utils.logger_utils import logger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_db(db_conn: Optional[Database] = None) -> Database:
    return db_conn if db_conn is not None else flask_db


# ---------------------------------------------------------------------------
# MongoDB health
# ---------------------------------------------------------------------------

def check_mongodb(db_conn: Optional[Database] = None) -> Dict[str, Any]:
    """Check MongoDB connectivity with a simple ping."""
    db = _get_db(db_conn)
    try:
        client: pymongo.MongoClient = db.client  # type: ignore[assignment]
        client.admin.command("ping")
        logger.info("MongoDB health check passed")
        return {"status": "healthy"}
    except Exception as e:  # noqa: BLE001
        logger.error("MongoDB health check failed: %s", e, exc_info=True)
        return {"status": "unhealthy", "error": str(e)}


# ---------------------------------------------------------------------------
# RabbitMQ health
# ---------------------------------------------------------------------------

@retry(wait=wait_fixed(5), stop=stop_after_attempt(3))
def check_rabbitmq() -> Dict[str, Any]:
    """
    Check RabbitMQ:
    - Connects successfully
    - Ensures all required queues exist
    - Returns simple queue depth info
    """
    connection: Optional[pika.BlockingConnection] = None
    details: Dict[str, Any] = {"queues": {}}
    status = "healthy"

    queues = [
        "file_processing",
        "summarize",
        "flashcards",
        "assess",
        "homework",
        "avner_chat",
    ]

    try:
        connection = pika.BlockingConnection(pika.URLParameters(settings.RABBITMQ_URI))
        channel = connection.channel()

        for queue_name in queues:
            # Idempotent: creates queue if needed, OK if it already exists
            q = channel.queue_declare(queue=queue_name, durable=True)
            message_count = q.method.message_count

            details["queues"][queue_name] = {"message_count": message_count}

            if message_count > 100:
                status = "degraded"

        logger.info("RabbitMQ health check passed")
        return {"status": status, "details": details}

    except Exception as e:  # noqa: BLE001
        logger.error("RabbitMQ health check failed: %s", e, exc_info=True)
        # Let tenacity handle retries by re-raising
        raise
    finally:
        if connection and connection.is_open:
            connection.close()
            logger.debug("RabbitMQ health check connection closed.")


# ---------------------------------------------------------------------------
# AI models health
# ---------------------------------------------------------------------------

def check_ai_models() -> Dict[str, Any]:
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
        logger.error("AI models health check failed: %s", e, exc_info=True)
        return {"status": "unhealthy", "error": str(e)}


# ---------------------------------------------------------------------------
# Filesystem / upload health (simple + PDF)
# ---------------------------------------------------------------------------

def check_file_upload() -> Dict[str, Any]:
    """
    Check that we can:
    - Create a temporary directory.
    - Write & read a text file.
    - Write & read a tiny PDF file.

    This is a lightweight check, separate from the deep test in health_monitor.
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

            # Read both files back
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
        logger.error("File upload health check failed: %s", e, exc_info=True)
        return {"status": "unhealthy", "error": str(e)}


# ---------------------------------------------------------------------------
# Git connectivity
# ---------------------------------------------------------------------------

def check_git_connectivity() -> Dict[str, Any]:
    """
    Check that we're in a git repo and 'git status -sb' works.
    """
    try:
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
        logger.error("Git connectivity check failed: %s", e, exc_info=True)
        return {"status": "unhealthy", "error": e.stderr or str(e)}
    except FileNotFoundError:
        logger.warning("Git not installed in container; treating as degraded")
        return {"status": "degraded", "error": "git not installed in container"}
    except Exception as e:  # noqa: BLE001
        logger.error("Git connectivity check failed: %s", e, exc_info=True)
        return {"status": "unhealthy", "error": str(e)}


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def get_comprehensive_health(db_conn: Database = None) -> Dict[str, Any]:
    """
    Run all health checks and return a structured report:

    {
        "timestamp": "...",
        "overall_status": "healthy" | "degraded" | "unhealthy",
        "components": {
            "mongodb": {...},
            "rabbitmq": {...},
            "ai_models": {...},
            "file_upload": {...},
            "git": {...},
        }
    }
    """
    health_report: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall_status": "healthy",
        "components": {},
    }

    logger.info("Running comprehensive health checks...")

    health_report["components"]["mongodb"] = check_mongodb(db_conn)

    try:
        health_report["components"]["rabbitmq"] = check_rabbitmq()
    except Exception as e:  # noqa: BLE001
        health_report["components"]["rabbitmq"] = {
            "status": "unhealthy",
            "error": str(e),
        }

    health_report["components"]["ai_models"] = check_ai_models()
    health_report["components"]["file_upload"] = check_file_upload()
    health_report["components"]["git"] = check_git_connectivity()

    # Compute overall status from the 5 tracked components
    statuses = [
        comp.get("status", "unknown")
        for comp in health_report["components"].values()
    ]

    if "unhealthy" in statuses:
        health_report["overall_status"] = "unhealthy"
    elif "degraded" in statuses:
        health_report["overall_status"] = "degraded"
    else:
        health_report["overall_status"] = "healthy"

    logger.info("Health check complete: %s", health_report["overall_status"])
    return health_report
