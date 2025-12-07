"""
Robust health monitoring utilities for StudyBuddyAI.

This module provides:
- Per-component health checks (MongoDB, RabbitMQ, AI models, filesystem, config, disk).
- Aggregated system health snapshot with HEALTHY / DEGRADED / UNHEALTHY states.
- Optional admin notification when the system is not healthy.

Intended to be used by:
- /health HTTP endpoint (for load balancers / uptime checks).
- health_monitor.py background worker (periodic deep checks + notifications).
"""

from __future__ import annotations

import os
import shutil
import smtplib
import socket
import tempfile
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
from enum import Enum
from typing import Any, Dict, List, Optional

import pika
import pymongo
from pika.adapters.blocking_connection import BlockingConnection
from tenacity import retry, stop_after_attempt, wait_fixed

from src.infrastructure.config import settings
from src.infrastructure.database import db as flask_db
from src.services.ai_client import AIClient
from sb_utils.logger_utils import logger


# ──────────────────────────────────────────────────────────────
# Enums & dataclasses
# ──────────────────────────────────────────────────────────────

class HealthState(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    name: str
    status: HealthState
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemHealthSnapshot:
    timestamp: str
    overall_status: HealthState
    components: Dict[str, ComponentHealth]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "overall_status": self.overall_status.value,
            "components": {
                name: {
                    "status": comp.status.value,
                    "details": comp.details,
                }
                for name, comp in self.components.items()
            },
        }


# Global (in-process) alert throttle to avoid spamming admin
_LAST_ALERT_SENT_AT: Optional[datetime] = None
ALERT_COOLDOWN_SECONDS = 900  # 15 minutes


# ──────────────────────────────────────────────────────────────
# MongoDB health
# ──────────────────────────────────────────────────────────────

def check_mongodb() -> ComponentHealth:
    try:
        client: pymongo.MongoClient = flask_db.client  # type: ignore[assignment]
        client.admin.command("ping")
        logger.debug("MongoDB ping successful")
        return ComponentHealth(
            name="mongodb",
            status=HealthState.HEALTHY,
            details={"message": "MongoDB ping OK"},
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("MongoDB health check failed: %s", exc, exc_info=True)
        return ComponentHealth(
            name="mongodb",
            status=HealthState.UNHEALTHY,
            details={"error": str(exc)},
        )


# ──────────────────────────────────────────────────────────────
# RabbitMQ health (queues + depth)
# ──────────────────────────────────────────────────────────────

REQUIRED_QUEUES: List[str] = [
    "summarize",
    "flashcards",
    "assess",
    "homework",
    "avner_chat",
]


@retry(wait=wait_fixed(5), stop=stop_after_attempt(3))
def _rabbitmq_connection() -> BlockingConnection:
    uri = settings.RABBITMQ_URI
    return pika.BlockingConnection(pika.URLParameters(uri))


def check_rabbitmq() -> ComponentHealth:
    connection: Optional[BlockingConnection] = None
    channel = None
    details: Dict[str, Any] = {"queues": {}}
    status = HealthState.HEALTHY

    try:
        connection = _rabbitmq_connection()
        channel = connection.channel()

        for queue_name in REQUIRED_QUEUES:
            # Ensure queue exists (idempotent)
            q = channel.queue_declare(queue=queue_name, durable=True)
            message_count = q.method.message_count

            details["queues"][queue_name] = {
                "message_count": message_count,
            }

            # Simple heuristic: many stuck messages → degraded
            if message_count > 100:
                status = HealthState.DEGRADED

        logger.info("RabbitMQ health check passed")
        return ComponentHealth(
            name="rabbitmq",
            status=status,
            details=details,
        )

    except Exception as exc:  # noqa: BLE001
        logger.error("RabbitMQ health check failed: %s", exc, exc_info=True)
        return ComponentHealth(
            name="rabbitmq",
            status=HealthState.UNHEALTHY,
            details={"error": str(exc)},
        )
    finally:
        if connection and connection.is_open:
            try:
                connection.close()
                logger.debug("RabbitMQ health check connection closed.")
            except Exception:  # noqa: BLE001
                pass


# ──────────────────────────────────────────────────────────────
# AI models health
# ──────────────────────────────────────────────────────────────

def check_ai_models() -> ComponentHealth:
    try:
        client = AIClient()
        models_details: Dict[str, Any] = {}

        for attr in ("primary_model", "fallback_model", "available_models"):
            if hasattr(client, attr):
                models_details[attr] = getattr(client, attr)

        logger.info("AI models health check passed")
        return ComponentHealth(
            name="ai_models",
            status=HealthState.HEALTHY,
            details=models_details,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("AI models health check failed: %s", exc, exc_info=True)
        return ComponentHealth(
            name="ai_models",
            status=HealthState.UNHEALTHY,
            details={"error": str(exc)},
        )


# ──────────────────────────────────────────────────────────────
# Filesystem / upload health (includes PDF)
# ──────────────────────────────────────────────────────────────

def check_filesystem() -> ComponentHealth:
    """
    Validate that we can:
    - Create a temporary directory
    - Write & read a text file
    - Write & read a tiny PDF file (more complex format)
    """
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            txt_path = os.path.join(tmpdir, "health_check.txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("studybuddy health check\n")

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

            # Read back
            with open(txt_path, "r", encoding="utf-8") as f:
                _ = f.read()

            with open(pdf_path, "rb") as f:
                _ = f.read(64)

        logger.info("Filesystem health check passed (text + PDF)")
        return ComponentHealth(
            name="filesystem",
            status=HealthState.HEALTHY,
            details={"message": "Temp text and PDF files created/read successfully"},
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Filesystem health check failed: %s", exc, exc_info=True)
        return ComponentHealth(
            name="filesystem",
            status=HealthState.UNHEALTHY,
            details={"error": str(exc)},
        )


# ──────────────────────────────────────────────────────────────
# Disk space / OS-level health
# ──────────────────────────────────────────────────────────────

def check_disk_space(path: str = "/") -> ComponentHealth:
    try:
        usage = shutil.disk_usage(path)
        total_gb = round(usage.total / (1024**3), 2)
        free_gb = round(usage.free / (1024**3), 2)
        free_percent = round(usage.free / usage.total * 100, 2)

        status = HealthState.HEALTHY
        if free_percent < 5:
            status = HealthState.UNHEALTHY
        elif free_percent < 10:
            status = HealthState.DEGRADED

        logger.info("Disk space check: free=%s%%", free_percent)
        return ComponentHealth(
            name="disk",
            status=status,
            details={
                "total_gb": total_gb,
                "free_gb": free_gb,
                "free_percent": free_percent,
                "path": path,
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Disk space check failed: %s", exc, exc_info=True)
        return ComponentHealth(
            name="disk",
            status=HealthState.UNHEALTHY,
            details={"error": str(exc)},
        )


# ──────────────────────────────────────────────────────────────
# Configuration / env health
# ──────────────────────────────────────────────────────────────

REQUIRED_SETTINGS: List[str] = [
    "MONGO_URI",
    "RABBITMQ_URI",
    "SECRET_KEY",
    "ADMIN_EMAIL",
]


def check_config() -> ComponentHealth:
    missing: List[str] = []
    details: Dict[str, Any] = {}

    for name in REQUIRED_SETTINGS:
        if not hasattr(settings, name) or not getattr(settings, name):
            missing.append(name)

    if missing:
        logger.warning("Config health: missing critical settings: %s", missing)
        return ComponentHealth(
            name="config",
            status=HealthState.DEGRADED,
            details={"missing_settings": missing},
        )

    details["env"] = {
        "hostname": socket.gethostname(),
        "flask_env": os.getenv("FLASK_ENV", "production"),
    }

    logger.debug("Config health OK")
    return ComponentHealth(
        name="config",
        status=HealthState.HEALTHY,
        details=details,
    )


# ──────────────────────────────────────────────────────────────
# Aggregation + admin notifications
# ──────────────────────────────────────────────────────────────

def run_comprehensive_health_check() -> SystemHealthSnapshot:
    """
    Run all checks and compute overall system state.
    This is used by:
    - HTTP /health endpoint
    - health_monitor worker
    """
    components: Dict[str, ComponentHealth] = {}

    logger.info("Running comprehensive health checks...")

    for check_fn in (
        check_mongodb,
        check_rabbitmq,
        check_ai_models,
        check_filesystem,
        check_disk_space,
        check_config,
    ):
        comp = check_fn()
        components[comp.name] = comp

    overall_status = _compute_overall_state(components)
    snapshot = SystemHealthSnapshot(
        timestamp=datetime.now(timezone.utc).isoformat(),
        overall_status=overall_status,
        components=components,
    )

    logger.info(
        "Health checks complete: %s",
        snapshot.overall_status.value,
        extra={"health_snapshot": snapshot.to_dict()},
    )
    return snapshot


def _compute_overall_state(components: Dict[str, ComponentHealth]) -> HealthState:
    statuses = {c.status for c in components.values()}
    if HealthState.UNHEALTHY in statuses:
        return HealthState.UNHEALTHY
    if HealthState.DEGRADED in statuses:
        return HealthState.DEGRADED
    return HealthState.HEALTHY


def notify_admin_if_needed(snapshot: SystemHealthSnapshot) -> None:
    """
    Send an admin email when system is DEGRADED or UNHEALTHY,
    with a simple cooldown to avoid spamming.
    """
    global _LAST_ALERT_SENT_AT

    if snapshot.overall_status == HealthState.HEALTHY:
        return

    now = datetime.now(timezone.utc)
    if _LAST_ALERT_SENT_AT is not None:
        elapsed = (now - _LAST_ALERT_SENT_AT).total_seconds()
        if elapsed < ALERT_COOLDOWN_SECONDS:
            logger.info(
                "Health alert suppressed (cooldown still active, %s seconds remaining)",
                ALERT_COOLDOWN_SECONDS - int(elapsed),
            )
            return

    try:
        _send_admin_email(snapshot)
        _LAST_ALERT_SENT_AT = now
        logger.info("Admin health alert sent")
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to send admin health alert: %s", exc, exc_info=True)


def _send_admin_email(snapshot: SystemHealthSnapshot) -> None:
    """
    Minimal SMTP-based email alert.

    Requires the following settings to be configured:
    - SMTP_HOST
    - SMTP_PORT
    - SMTP_USERNAME
    - SMTP_PASSWORD
    - ADMIN_EMAIL
    """
    smtp_host = getattr(settings, "SMTP_HOST", None)
    smtp_port = int(getattr(settings, "SMTP_PORT", "587"))
    smtp_user = getattr(settings, "SMTP_USERNAME", None)
    smtp_pass = getattr(settings, "SMTP_PASSWORD", None)
    admin_email = getattr(settings, "ADMIN_EMAIL", None)

    if not all([smtp_host, smtp_port, smtp_user, smtp_pass, admin_email]):
        logger.warning(
            "Admin email alert skipped: SMTP/ADMIN settings not fully configured"
        )
        return

    msg = EmailMessage()
    msg["Subject"] = f"[StudyBuddy] Health Alert: {snapshot.overall_status.value.upper()}"
    msg["From"] = smtp_user
    msg["To"] = admin_email

    body = [
        f"Time (UTC): {snapshot.timestamp}",
        f"Overall status: {snapshot.overall_status.value}",
        "",
        "Components:",
    ]
    for name, comp in snapshot.components.items():
        body.append(f"- {name}: {comp.status.value}")
        if comp.details:
            body.append(f"  details: {comp.details}")

    msg.set_content("\n".join(body))

    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
