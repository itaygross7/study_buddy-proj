"""Admin routes for system management."""
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from src.infrastructure.database import db
from src.services import auth_service
from src.domain.models.db_models import UserRole, SystemConfig
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


@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    """Admin dashboard."""
    # Get statistics
    user_count = auth_service.get_user_count(db)
    doc_count = db.documents.count_documents({})
    task_count = db.tasks.count_documents({})
    
    # Get recent users
    recent_users = list(db.users.find().sort("created_at", -1).limit(10))
    
    # Get system config
    config = get_system_config()
    
    return render_template('admin/dashboard.html',
                         user_count=user_count,
                         doc_count=doc_count,
                         task_count=task_count,
                         recent_users=recent_users,
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
    user_count = auth_service.get_user_count(db)
    doc_count = db.documents.count_documents({})
    task_count = db.tasks.count_documents({})
    
    # Tasks by status
    pending_tasks = db.tasks.count_documents({"status": "PENDING"})
    completed_tasks = db.tasks.count_documents({"status": "COMPLETED"})
    failed_tasks = db.tasks.count_documents({"status": "FAILED"})
    
    return jsonify({
        "users": user_count,
        "documents": doc_count,
        "tasks": {
            "total": task_count,
            "pending": pending_tasks,
            "completed": completed_tasks,
            "failed": failed_tasks
        }
    })
