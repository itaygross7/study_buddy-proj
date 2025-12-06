"""Comprehensive health monitoring service for StudyBuddy AI.

Tests all critical components:
- AI models (OpenAI, Gemini)
- File upload and processing
- RabbitMQ worker
- Git connectivity
- Database connections
"""
import os
import tempfile
import subprocess
from datetime import datetime, timezone
from pymongo.database import Database
import pika

from src.infrastructure.config import settings
from src.infrastructure.database import db as flask_db
from src.services.ai_client import AIClient
from sb_utils.logger_utils import logger


def _get_db(db_conn: Database = None) -> Database:
    """Returns the provided db_conn or the default Flask db proxy."""
    return db_conn or flask_db


def check_mongodb(db_conn: Database = None) -> dict:
    """Check MongoDB connection and basic operations."""
    db = _get_db(db_conn)
    
    try:
        # Test connection
        db.command('ping')
        
        # Test write operation
        test_doc = {
            "_id": "health_check_test",
            "timestamp": datetime.now(timezone.utc),
            "type": "health_check"
        }
        db.health_checks.replace_one({"_id": "health_check_test"}, test_doc, upsert=True)
        
        # Test read operation
        result = db.health_checks.find_one({"_id": "health_check_test"})
        
        if result:
            return {
                "status": "healthy",
                "latency_ms": 0,  # Could measure actual latency
                "can_read": True,
                "can_write": True
            }
        else:
            return {
                "status": "degraded",
                "error": "Write succeeded but read failed"
            }
            
    except Exception as e:
        logger.error(f"MongoDB health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e)
        }


def check_rabbitmq() -> dict:
    """Check RabbitMQ connection."""
    try:
        connection = pika.BlockingConnection(
            pika.URLParameters(settings.RABBITMQ_URI)
        )
        channel = connection.channel()
        
        # Check if queues exist
        queues = ['file_processing', 'summarize', 'flashcards', 'assess', 'homework', 'avner_chat']
        queue_status = {}
        
        for queue_name in queues:
            try:
                method = channel.queue_declare(queue=queue_name, durable=True, passive=True)
                queue_status[queue_name] = {
                    "exists": True,
                    "message_count": method.method.message_count,
                    "consumer_count": method.method.consumer_count
                }
            except Exception as q_error:
                queue_status[queue_name] = {
                    "exists": False,
                    "error": str(q_error)
                }
        
        connection.close()
        
        # Check if any queue has consumers (worker is running)
        has_consumers = any(q.get("consumer_count", 0) > 0 for q in queue_status.values())
        
        return {
            "status": "healthy",
            "queues": queue_status,
            "worker_active": has_consumers
        }
        
    except Exception as e:
        logger.error(f"RabbitMQ health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e),
            "worker_active": False
        }


def check_ai_models() -> dict:
    """Test AI model connectivity and functionality."""
    results = {}
    
    # Test OpenAI
    if settings.OPENAI_API_KEY:
        try:
            ai_client = AIClient()
            # Use task_type "standard" to route to GPT-4o-mini
            test_response = ai_client.generate_text(
                prompt="Say 'OK' if you can read this.",
                context="You are a test bot. Respond with exactly 'OK'.",
                task_type="standard"
            )
            
            results["openai"] = {
                "status": "healthy" if test_response else "degraded",
                "model": settings.SB_OPENAI_MODEL,
                "response_received": bool(test_response),
                "test_passed": "ok" in test_response.lower() if test_response else False
            }
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}", exc_info=True)
            results["openai"] = {
                "status": "unhealthy",
                "model": settings.SB_OPENAI_MODEL,
                "error": str(e)
            }
    else:
        results["openai"] = {
            "status": "not_configured",
            "message": "No API key provided"
        }
    
    # Test Gemini
    if settings.GEMINI_API_KEY:
        try:
            ai_client = AIClient()
            # Use task_type "heavy_file" to route to Gemini Flash (without actual file)
            test_response = ai_client.generate_text(
                prompt="Say 'OK' if you can read this.",
                context="You are a test bot. Respond with exactly 'OK'.",
                task_type="heavy_file"
            )
            
            results["gemini"] = {
                "status": "healthy" if test_response else "degraded",
                "model": settings.SB_GEMINI_MODEL,
                "response_received": bool(test_response),
                "test_passed": "ok" in test_response.lower() if test_response else False
            }
        except Exception as e:
            logger.error(f"Gemini health check failed: {e}", exc_info=True)
            results["gemini"] = {
                "status": "unhealthy",
                "model": settings.SB_GEMINI_MODEL,
                "error": str(e)
            }
    else:
        results["gemini"] = {
            "status": "not_configured",
            "message": "No API key provided"
        }
    
    # Determine overall AI status
    healthy_models = sum(1 for r in results.values() if r.get("status") == "healthy")
    
    if healthy_models == 0:
        overall_status = "unhealthy"
    elif healthy_models < len([k for k in results if results[k].get("status") != "not_configured"]):
        overall_status = "degraded"
    else:
        overall_status = "healthy"
    
    return {
        "status": overall_status,
        "default_provider": settings.SB_DEFAULT_PROVIDER,
        "models": results,
        "healthy_count": healthy_models
    }


def check_file_upload() -> dict:
    """Test file upload and processing capability."""
    try:
        # Create a test text file
        test_content = "This is a health check test file. שלום! Testing Hebrew text."
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(test_content)
            test_file_path = f.name
        
        try:
            # Test file processing
            from src.utils.file_processing import process_file_from_path
            
            extracted_text = process_file_from_path(test_file_path, "health_check_test.txt")
            
            # Clean up
            if os.path.exists(test_file_path):
                os.remove(test_file_path)
            
            # Verify extraction worked
            if extracted_text and "health check test" in extracted_text.lower():
                return {
                    "status": "healthy",
                    "can_process_files": True,
                    "text_extraction_working": True
                }
            else:
                return {
                    "status": "degraded",
                    "can_process_files": True,
                    "text_extraction_working": False,
                    "error": "Text extraction returned unexpected result"
                }
                
        except Exception as proc_error:
            # Clean up on error
            if os.path.exists(test_file_path):
                os.remove(test_file_path)
            raise proc_error
            
    except Exception as e:
        logger.error(f"File upload health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e)
        }


def check_git_connectivity() -> dict:
    """Test Git connectivity and ability to pull updates."""
    try:
        # Check if we're in a git repository
        result = subprocess.run(
            ['git', 'rev-parse', '--git-dir'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return {
                "status": "unhealthy",
                "error": "Not a git repository",
                "can_pull": False
            }
        
        # Get current branch
        branch_result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5
        )
        current_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"
        
        # Get current commit
        commit_result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5
        )
        current_commit = commit_result.stdout.strip() if commit_result.returncode == 0 else "unknown"
        
        # Test git fetch (doesn't modify local files, just checks connectivity)
        fetch_result = subprocess.run(
            ['git', 'fetch', '--dry-run'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        can_fetch = fetch_result.returncode == 0
        
        # Check for uncommitted changes
        status_result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True,
            text=True,
            timeout=5
        )
        has_changes = bool(status_result.stdout.strip()) if status_result.returncode == 0 else False
        
        return {
            "status": "healthy" if can_fetch else "degraded",
            "current_branch": current_branch,
            "current_commit": current_commit,
            "can_fetch": can_fetch,
            "can_pull": can_fetch and not has_changes,
            "has_uncommitted_changes": has_changes,
            "auto_update_possible": can_fetch and not has_changes
        }
        
    except subprocess.TimeoutExpired:
        return {
            "status": "unhealthy",
            "error": "Git command timed out",
            "can_pull": False
        }
    except FileNotFoundError:
        return {
            "status": "unhealthy",
            "error": "Git not installed",
            "can_pull": False
        }
    except Exception as e:
        logger.error(f"Git connectivity check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e),
            "can_pull": False
        }


def get_comprehensive_health(db_conn: Database = None) -> dict:
    """
    Run all health checks and return comprehensive status.
    
    Returns:
        Dict with overall status and individual component statuses
    """
    health_report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall_status": "healthy",
        "components": {}
    }
    
    # Check all components
    logger.info("Running comprehensive health checks...")
    
    # MongoDB
    health_report["components"]["mongodb"] = check_mongodb(db_conn)
    
    # RabbitMQ and Worker
    health_report["components"]["rabbitmq"] = check_rabbitmq()
    
    # AI Models
    health_report["components"]["ai_models"] = check_ai_models()
    
    # File Upload
    health_report["components"]["file_upload"] = check_file_upload()
    
    # Git Connectivity
    health_report["components"]["git"] = check_git_connectivity()
    
    # Determine overall status
    component_statuses = [comp.get("status", "unknown") for comp in health_report["components"].values()]
    
    if "unhealthy" in component_statuses:
        health_report["overall_status"] = "unhealthy"
    elif "degraded" in component_statuses:
        health_report["overall_status"] = "degraded"
    else:
        health_report["overall_status"] = "healthy"
    
    # Add summary
    health_report["summary"] = {
        "healthy_components": sum(1 for s in component_statuses if s == "healthy"),
        "degraded_components": sum(1 for s in component_statuses if s == "degraded"),
        "unhealthy_components": sum(1 for s in component_statuses if s == "unhealthy"),
        "total_components": len(component_statuses)
    }
    
    logger.info(f"Health check complete: {health_report['overall_status']}")
    
    return health_report
