"""Admin routes for system management."""
import platform
import psutil
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from src.infrastructure.database import db
from src.services import auth_service
from src.domain.models.db_models import SystemConfig
from src.api.routes_auth import admin_required
from sb_utils.logger_utils import logger

admin_bp = Blueprint('admin', __name__)


def get_system_config() -> SystemConfig:
    """Get or create system configuration."""
    config_data = db.system_config.find_one({"_id": "system_config"})
    if config_data:
        return SystemConfig(**config_data)
    # Create default config
    config = SystemConfig()
    db.system_config.insert_one(config.to_dict())
    return config


def update_system_config(updates: dict) -> bool:
    """Update system configuration."""
    updates["updated_at"] = datetime.now(timezone.utc)
    result = db.system_config.update_one(
        {"_id": "system_config"},
        {"$set": updates},
        upsert=True
    )
    return result.modified_count > 0 or result.upserted_id is not None


def get_system_health():
    """Get system health information."""
    health = {
        "status": "healthy",
        "issues": [],
        "metrics": {}
    }

    try:
        # CPU Usage
        cpu_percent = psutil.cpu_percent(interval=1)
        health["metrics"]["cpu"] = {
            "percent": cpu_percent,
            "cores": psutil.cpu_count(),
            "status": "good" if cpu_percent < 80 else "warning" if cpu_percent < 95 else "critical"
        }
        if cpu_percent >= 80:
            health["issues"].append(f"CPU usage high: {cpu_percent}%")

        # Memory Usage
        memory = psutil.virtual_memory()
        health["metrics"]["memory"] = {
            "total_gb": round(memory.total / (1024**3), 2),
            "used_gb": round(memory.used / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "percent": memory.percent,
            "status": "good" if memory.percent < 80 else "warning" if memory.percent < 95 else "critical"
        }
        if memory.percent >= 80:
            health["issues"].append(f"Memory usage high: {memory.percent}%")

        # Disk Usage
        disk = psutil.disk_usage('/')
        health["metrics"]["disk"] = {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "percent": round(disk.percent, 1),
            "status": "good" if disk.percent < 80 else "warning" if disk.percent < 95 else "critical"
        }
        if disk.percent >= 80:
            health["issues"].append(f"Disk usage high: {disk.percent}%")

        # System Info
        health["metrics"]["system"] = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
            "hostname": platform.node(),
            "uptime_hours": round((datetime.now().timestamp() - psutil.boot_time()) / 3600, 1)
        }

        # Database Status
        try:
            db_stats = db.command("dbStats")
            health["metrics"]["database"] = {
                "status": "connected",
                "size_mb": round(db_stats.get("dataSize", 0) / (1024**2), 2),
                "storage_mb": round(db_stats.get("storageSize", 0) / (1024**2), 2),
                "collections": db_stats.get("collections", 0),
                "objects": db_stats.get("objects", 0)
            }
        except Exception as e:
            health["metrics"]["database"] = {"status": "error", "error": str(e)}
            health["issues"].append("Database connection issue")

        # Determine overall status
        if any(m.get("status") == "critical" for m in health["metrics"].values() if isinstance(m, dict)):
            health["status"] = "critical"
        elif any(m.get("status") == "warning" for m in health["metrics"].values() if isinstance(m, dict)):
            health["status"] = "warning"
        elif health["issues"]:
            health["status"] = "warning"

    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        health["status"] = "error"
        health["issues"].append(f"Error collecting metrics: {str(e)}")

    return health


def get_app_statistics():
    """Get application-specific statistics."""
    try:
        stats = {
            "users": {
                "total": db.users.count_documents({}),
                "verified": db.users.count_documents({"is_verified": True}),
                "active": db.users.count_documents({"is_active": True}),
                "admins": db.users.count_documents({"role": "admin"}),
                "today": db.users.count_documents({
                    "created_at": {"$gte": datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)}
                })
            },
            "content": {
                "documents": db.documents.count_documents({}),
                "courses": db.courses.count_documents({}) if "courses" in db.list_collection_names() else 0,
                "summaries": db.summaries.count_documents({}) if "summaries" in db.list_collection_names() else 0,
                "flashcard_sets": db.flashcard_sets.count_documents({}),
                "assessments": db.assessments.count_documents({})
            },
            "tasks": {
                "total": db.tasks.count_documents({}),
                "pending": db.tasks.count_documents({"status": "PENDING"}),
                "processing": db.tasks.count_documents({"status": "PROCESSING"}),
                "completed": db.tasks.count_documents({"status": "COMPLETED"}),
                "failed": db.tasks.count_documents({"status": "FAILED"})
            }
        }
        return stats
    except Exception as e:
        logger.error(f"Error getting app statistics: {e}")
        return {}


@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    """Admin dashboard with system status."""
    # Get system health
    health = get_system_health()

    # Get app statistics
    stats = get_app_statistics()

    # Get recent users
    recent_users = list(db.users.find().sort("created_at", -1).limit(10))

    # Get recent errors/warnings from tasks
    recent_failures = list(db.tasks.find({"status": "FAILED"}).sort("updated_at", -1).limit(5))

    # Get system config
    config = get_system_config()

    return render_template('admin/dashboard.html',
                           health=health,
                           stats=stats,
                           recent_users=recent_users,
                           recent_failures=recent_failures,
                           config=config)


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """User management page."""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    skip = (page - 1) * per_page

    users_list = auth_service.get_all_users(db, skip=skip, limit=per_page)
    total_users = auth_service.get_user_count(db)
    total_pages = (total_users + per_page - 1) // per_page

    return render_template('admin/users.html',
                           users=users_list,
                           page=page,
                           total_pages=total_pages,
                           total_users=total_users)


@admin_bp.route('/users/<user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    """Toggle user active status."""
    user = auth_service.get_user_by_id(db, user_id)
    if not user:
        flash('משתמש לא נמצא', 'error')
        return redirect(url_for('admin.users'))

    # Don't allow deactivating yourself
    if user_id == current_user.id:
        flash('לא ניתן לשנות את הסטטוס של עצמך', 'error')
        return redirect(url_for('admin.users'))

    new_status = not user.is_active
    auth_service.update_user_status(db, user_id, new_status)

    status_text = 'הופעל' if new_status else 'הושבת'
    flash(f'המשתמש {status_text} בהצלחה', 'success')
    logger.info(f"Admin toggled user {user_id} status to {new_status}")

    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user."""
    # Don't allow deleting yourself
    if user_id == current_user.id:
        flash('לא ניתן למחוק את עצמך', 'error')
        return redirect(url_for('admin.users'))

    if auth_service.delete_user(db, user_id):
        flash('המשתמש נמחק בהצלחה', 'success')
        logger.info(f"Admin deleted user {user_id}")
    else:
        flash('שגיאה במחיקת המשתמש', 'error')

    return redirect(url_for('admin.users'))


@admin_bp.route('/config', methods=['GET', 'POST'])
@login_required
@admin_required
def config():
    """System configuration page."""
    if request.method == 'POST':
        try:
            updates = {
                "max_prompts_per_day": int(request.form.get('max_prompts_per_day', 50)),
                "max_file_size_mb": int(request.form.get('max_file_size_mb', 10)),
                "default_flashcards_count": int(request.form.get('default_flashcards_count', 10)),
                "default_questions_count": int(request.form.get('default_questions_count', 5)),
                "maintenance_mode": request.form.get('maintenance_mode') == 'on',
            }

            # Handle enabled modules
            enabled_modules = request.form.getlist('enabled_modules')
            if enabled_modules:
                updates["enabled_modules"] = enabled_modules

            update_system_config(updates)
            flash('ההגדרות עודכנו בהצלחה', 'success')
            logger.info("Admin updated system configuration")

        except Exception as e:
            logger.error(f"Config update error: {e}", exc_info=True)
            flash('שגיאה בעדכון ההגדרות', 'error')

        return redirect(url_for('admin.config'))

    system_config = get_system_config()
    return render_template('admin/config.html', config=system_config)


@admin_bp.route('/api/stats')
@login_required
@admin_required
def api_stats():
    """Get system statistics as JSON."""
    stats = get_app_statistics()
    return jsonify(stats)


@admin_bp.route('/api/health')
@login_required
@admin_required
def api_health():
    """Get system health as JSON (for real-time updates)."""
    health = get_system_health()
    return jsonify(health)


@admin_bp.route('/system')
@login_required
@admin_required
def system_status():
    """Detailed system status page."""
    health = get_system_health()
    stats = get_app_statistics()
    config = get_system_config()

    return render_template('admin/system.html',
                           health=health,
                           stats=stats,
                           config=config)
