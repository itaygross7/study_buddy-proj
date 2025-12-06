"""Routes for user library and course management."""
import uuid
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from src.infrastructure.database import db
from src.domain.models.db_models import Course, UserProfile, Language
from src.api.routes_admin import get_system_config
from src.services import auth_service
from sb_utils.logger_utils import logger

library_bp = Blueprint('library', __name__)

# Available course icons
COURSE_ICONS = ['📚', '📖', '📝', '🔬', '🧮', '🎨', '🎵', '💻', '🌍', '⚖️', '💼', '🏥', '🔧', '📊', '🧠', '✏️']
COURSE_COLORS = ['#F2C94C', '#7CB342', '#42A5F5', '#AB47BC', '#EF5350', '#26A69A', '#FF7043', '#8D6E63']


def get_user_profile(user_id: str) -> UserProfile:
    """Get or create user profile."""
    profile_data = db.user_profiles.find_one({"_id": user_id})
    if profile_data:
        return UserProfile(**profile_data)
    # Create default profile
    profile = UserProfile(_id=user_id)
    db.user_profiles.insert_one(profile.to_dict())
    return profile


def get_user_courses(user_id: str):
    """Get all courses for a user."""
    courses = []
    for course_data in db.courses.find({"user_id": user_id}).sort("updated_at", -1):
        courses.append(Course(**course_data))
    return courses


def get_course_by_id(course_id: str, user_id: str):
    """Get a specific course, ensuring user ownership."""
    course_data = db.courses.find_one({"_id": course_id, "user_id": user_id})
    return Course(**course_data) if course_data else None


def get_course_documents(course_id: str):
    """Get all documents in a course."""
    return list(db.documents.find({"course_id": course_id}).sort("created_at", -1))


def get_course_context(course_id: str, user_id: str, max_chars: int = 5000) -> str:
    """Get combined context from all course documents for AI."""
    documents = db.documents.find({"course_id": course_id, "user_id": user_id})
    context_parts = []
    total_chars = 0

    for doc in documents:
        content = doc.get("content_text", "")
        if total_chars + len(content) > max_chars:
            # Add truncated content
            remaining = max_chars - total_chars
            if remaining > 100:
                context_parts.append(content[:remaining] + "...")
            break
        context_parts.append(content)
        total_chars += len(content)

    return "\n\n---\n\n".join(context_parts)


@library_bp.route('/')
@login_required
def index():
    """User's library - list of all courses."""
    courses = get_user_courses(current_user.id)
    profile = get_user_profile(current_user.id)
    config = get_system_config()

    return render_template('library/index.html',
                           courses=courses,
                           profile=profile,
                           max_courses=config.max_courses_per_user,
                           icons=COURSE_ICONS,
                           colors=COURSE_COLORS)


@library_bp.route('/course/new', methods=['GET', 'POST'])
@login_required
def new_course():
    """Create a new course."""
    config = get_system_config()
    current_count = db.courses.count_documents({"user_id": current_user.id})

    # Admin users have no course limit
    from src.domain.models.db_models import UserRole
    if current_user.role != UserRole.ADMIN and current_count >= config.max_courses_per_user:
        flash(f'הגעת למקסימום {config.max_courses_per_user} קורסים', 'error')
        return redirect(url_for('library.index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        language = request.form.get('language', 'he')
        icon = request.form.get('icon', '📚')
        color = request.form.get('color', '#F2C94C')

        if not name:
            flash('יש להזין שם לקורס', 'error')
            return render_template('library/new_course.html', icons=COURSE_ICONS, colors=COURSE_COLORS)

        if len(name) > 100:
            flash('שם הקורס ארוך מדי (מקסימום 100 תווים)', 'error')
            return render_template('library/new_course.html', icons=COURSE_ICONS, colors=COURSE_COLORS)

        course = Course(
            _id=str(uuid.uuid4()),
            user_id=current_user.id,
            name=name,
            description=description,
            language=Language.HEBREW if language == 'he' else Language.ENGLISH,
            icon=icon,
            color=color
        )

        db.courses.insert_one(course.to_dict())
        logger.info(f"User {current_user.id} created course: {name}")
        flash('הקורס נוצר בהצלחה! 📚', 'success')
        return redirect(url_for('library.course_page', course_id=course.id))

    return render_template('library/new_course.html', icons=COURSE_ICONS, colors=COURSE_COLORS)


@library_bp.route('/course/<course_id>')
@login_required
def course_page(course_id):
    """Course page with all tools."""
    course = get_course_by_id(course_id, current_user.id)
    if not course:
        flash('הקורס לא נמצא', 'error')
        return redirect(url_for('library.index'))

    documents = get_course_documents(course_id)

    # Get summaries, flashcards, assessments for this course
    summaries = list(db.summaries.find({"course_id": course_id}).sort("created_at", -1).limit(10))
    flashcard_sets = list(db.flashcard_sets.find({"course_id": course_id}).sort("created_at", -1).limit(10))
    assessments = list(db.assessments.find({"course_id": course_id}).sort("created_at", -1).limit(10))

    return render_template('library/course.html',
                           course=course,
                           documents=documents,
                           summaries=summaries,
                           flashcard_sets=flashcard_sets,
                           assessments=assessments,
                           has_content=len(documents) > 0)


@library_bp.route('/course/<course_id>/settings', methods=['GET', 'POST'])
@login_required
def course_settings(course_id):
    """Edit course settings."""
    course = get_course_by_id(course_id, current_user.id)
    if not course:
        flash('הקורס לא נמצא', 'error')
        return redirect(url_for('library.index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        language = request.form.get('language', 'he')
        icon = request.form.get('icon', course.icon)
        color = request.form.get('color', course.color)

        if not name:
            flash('יש להזין שם לקורס', 'error')
            return render_template('library/course_settings.html', course=course,
                                   icons=COURSE_ICONS, colors=COURSE_COLORS)

        db.courses.update_one(
            {"_id": course_id, "user_id": current_user.id},
            {"$set": {
                "name": name,
                "description": description,
                "language": language,
                "icon": icon,
                "color": color,
                "updated_at": datetime.now(timezone.utc)
            }}
        )

        flash('הקורס עודכן בהצלחה', 'success')
        return redirect(url_for('library.course_page', course_id=course_id))

    return render_template('library/course_settings.html', course=course, icons=COURSE_ICONS, colors=COURSE_COLORS)


@library_bp.route('/course/<course_id>/delete', methods=['POST'])
@login_required
def delete_course(course_id):
    """Delete a course and all its content."""
    course = get_course_by_id(course_id, current_user.id)
    if not course:
        flash('הקורס לא נמצא', 'error')
        return redirect(url_for('library.index'))

    # Delete all related data
    db.documents.delete_many({"course_id": course_id, "user_id": current_user.id})
    db.summaries.delete_many({"course_id": course_id, "user_id": current_user.id})
    db.flashcard_sets.delete_many({"course_id": course_id, "user_id": current_user.id})
    db.assessments.delete_many({"course_id": course_id, "user_id": current_user.id})
    db.courses.delete_one({"_id": course_id, "user_id": current_user.id})

    logger.info(f"User {current_user.id} deleted course: {course.name}")
    flash('הקורס נמחק בהצלחה', 'success')
    return redirect(url_for('library.index'))


@library_bp.route('/course/<course_id>/upload', methods=['POST'])
@login_required
def upload_to_course(course_id):
    """Upload a document to a course."""
    course = get_course_by_id(course_id, current_user.id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    # This will be handled by the existing upload route with course_id parameter
    # Redirect to the upload API
    return redirect(url_for('upload_bp.upload_file_route', course_id=course_id))


@library_bp.route('/course/<course_id>/<tool>')
@login_required
def course_tool(course_id, tool):
    """Use a specific tool within a course context."""
    course = get_course_by_id(course_id, current_user.id)
    if not course:
        flash('הקורס לא נמצא', 'error')
        return redirect(url_for('library.index'))

    # Check if course has content
    doc_count = db.documents.count_documents({"course_id": course_id})
    if doc_count == 0:
        flash('יש להעלות חומר לימוד לפני השימוש בכלים', 'warning')
        return redirect(url_for('library.course_page', course_id=course_id))

    # Valid tools
    valid_tools = ['summary', 'flashcards', 'assess', 'homework']
    if tool not in valid_tools:
        flash('כלי לא קיים', 'error')
        return redirect(url_for('library.course_page', course_id=course_id))

    # Get course context for the tool
    context = get_course_context(course_id, current_user.id)
    documents = get_course_documents(course_id)

    return render_template(f'tool_{tool}.html',
                           course=course,
                           documents=documents,
                           context=context,
                           course_id=course_id)


# ============ User Profile Routes ============

@library_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page."""
    user_profile = get_user_profile(current_user.id)

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        institution = request.form.get('institution', '').strip()
        degree = request.form.get('degree', '').strip()
        year_of_study = request.form.get('year_of_study', '').strip()
        general_context = request.form.get('general_context', '').strip()
        preferred_language = request.form.get('preferred_language', 'he')

        db.user_profiles.update_one(
            {"_id": current_user.id},
            {"$set": {
                "full_name": full_name,
                "phone": phone,
                "institution": institution,
                "degree": degree,
                "year_of_study": year_of_study,
                "general_context": general_context[:1000],  # Limit context length
                "preferred_language": preferred_language,
                "updated_at": datetime.now(timezone.utc)
            }},
            upsert=True
        )

        # Also update user name
        db.users.update_one(
            {"_id": current_user.id},
            {"$set": {"name": full_name}}
        )

        flash('הפרופיל עודכן בהצלחה', 'success')
        return redirect(url_for('library.profile'))

    courses_count = db.courses.count_documents({"user_id": current_user.id})
    documents_count = db.documents.count_documents({"user_id": current_user.id})

    return render_template('library/profile.html',
                           profile=user_profile,
                           courses_count=courses_count,
                           documents_count=documents_count)


@library_bp.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password."""
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not current_password or not new_password:
        flash('יש למלא את כל השדות', 'error')
        return redirect(url_for('library.profile'))

    if new_password != confirm_password:
        flash('הסיסמאות החדשות אינן תואמות', 'error')
        return redirect(url_for('library.profile'))

    if len(new_password) < 8:
        flash('הסיסמה החדשה חייבת להכיל לפחות 8 תווים', 'error')
        return redirect(url_for('library.profile'))

    # Check if user has a password (OAuth users don't)
    user = db.users.find_one({"_id": current_user.id})
    if not user.get('password_hash'):
        flash('לא ניתן לשנות סיסמה למשתמשי OAuth. אנא השתמש בשיטת ההתחברות המקורית.', 'error')
        return redirect(url_for('library.profile'))

    # Attempt to change password
    if auth_service.change_password(db, current_user.id, current_password, new_password):
        flash('הסיסמה שונתה בהצלחה! 🔒', 'success')
    else:
        flash('הסיסמה הנוכחית שגויה', 'error')

    return redirect(url_for('library.profile'))


# ============ API Endpoints ============

@library_bp.route('/api/courses')
@login_required
def api_list_courses():
    """API: List user's courses."""
    courses = get_user_courses(current_user.id)
    return jsonify([{
        "id": c.id,
        "name": c.name,
        "icon": c.icon,
        "color": c.color,
        "language": c.language.value,
        "has_content": c.has_content(),
        "document_count": c.document_count
    } for c in courses])


@library_bp.route('/api/course/<course_id>/context')
@login_required
def api_course_context(course_id):
    """API: Get course context for AI (ensures user ownership)."""
    course = get_course_by_id(course_id, current_user.id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    context = get_course_context(course_id, current_user.id)
    profile = get_user_profile(current_user.id)

    return jsonify({
        "course_name": course.name,
        "language": course.language.value,
        "context": context,
        "user_context": profile.general_context
    })
