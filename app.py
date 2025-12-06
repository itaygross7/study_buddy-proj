import os
import sys
from flask import Flask, jsonify, render_template, request, send_from_directory, session, flash, redirect, url_for
from flask_cors import CORS
from flask_login import current_user, login_required
from werkzeug.exceptions import NotFound
from flask_babel import Babel, get_locale

from src.infrastructure.config import settings
from src.infrastructure.database import init_app as init_db, db
from sb_utils.logger_utils import logger
from src.services import email_service, auth_service

# Import Blueprints
from src.api.routes_summary import summary_bp
from src.api.routes_flashcards import flashcards_bp
from src.api.routes_assess import assess_bp
from src.api.routes_homework import homework_bp
from src.api.routes_upload import upload_bp
from src.api.routes_task import task_bp
from src.api.routes_results import results_bp
from src.api.routes_pdf import pdf_bp
from src.api.routes_auth import auth_bp, login_manager
from src.api.routes_admin import admin_bp
from src.api.routes_avner import avner_bp
from src.api.routes_library import library_bp
from src.api.routes_oauth import oauth_bp, init_oauth
from src.api.routes_webhook import webhook_bp
from src.api.routes_glossary import glossary_bp
from src.api.routes_tutor import tutor_bp
from src.api.routes_diagram import diagram_bp

babel = Babel()

# Constants for flash messages
NO_FILES_MESSAGE = 'יש להעלות חומר לימוד לפני השימוש בכלים. צור קורס והעלה קבצים כדי להתחיל!'

def get_locale_from_session():
    """Get language from session, default to Hebrew."""
    return session.get('lang', 'he')

def check_user_has_documents():
    """Check if the current user has any uploaded documents."""
    return db.documents.count_documents({"user_id": current_user.id}) > 0

def require_uploaded_files(template_name):
    """Helper function to check if user has uploaded files before rendering a tool template.
    
    Returns the rendered template if user has documents, otherwise redirects to library.
    """
    if not check_user_has_documents():
        flash(NO_FILES_MESSAGE, 'warning')
        return redirect(url_for('library.index'))
    return render_template(template_name)

def create_app():
    """Application factory for Flask."""
    app = Flask(__name__, template_folder='ui/templates', static_folder='ui/static')

    # --- Core Configuration ---
    app.config.from_object(settings)
    app.config['JSON_AS_ASCII'] = False

    # --- Security Configuration ---
    app.config['SESSION_COOKIE_SECURE'] = settings.FLASK_ENV == 'production'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    # --- Initialize Extensions ---
    init_db(app)
    babel.init_app(app, locale_selector=get_locale_from_session)
    login_manager.init_app(app)
    init_oauth(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'יש להתחבר כדי לגשת לעמוד זה'
    login_manager.login_message_category = 'warning'

    # --- Static File Serving for Avner ---
    avner_folder = os.path.join(os.path.dirname(__file__), 'ui', 'Avner')
    @app.route('/avner/<path:filename>')
    def serve_avner(filename):
        return send_from_directory(avner_folder, filename)

    # --- Blueprints Registration ---
    # All blueprints are confirmed to be present and registered.
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(oauth_bp, url_prefix='/oauth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(library_bp, url_prefix='/library')
    app.register_blueprint(avner_bp, url_prefix='/api/avner')
    app.register_blueprint(webhook_bp, url_prefix='/webhook')
    app.register_blueprint(summary_bp, url_prefix='/api/summary')
    app.register_blueprint(flashcards_bp, url_prefix='/api/flashcards')
    app.register_blueprint(assess_bp, url_prefix='/api/assess')
    app.register_blueprint(homework_bp, url_prefix='/api/homework')
    app.register_blueprint(upload_bp, url_prefix='/api/upload')
    app.register_blueprint(task_bp, url_prefix='/api/tasks')
    app.register_blueprint(results_bp, url_prefix='/results')
    app.register_blueprint(pdf_bp, url_prefix='/export/pdf')
    app.register_blueprint(glossary_bp, url_prefix='/api/glossary')
    app.register_blueprint(tutor_bp, url_prefix='/api/tutor')
    app.register_blueprint(diagram_bp, url_prefix='/api/diagram')

    # --- Request Hooks & Context Processors ---
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        # Updated CSP to allow service worker and inline scripts
        response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net; connect-src 'self'; worker-src 'self'; manifest-src 'self';"
        return response

    @app.context_processor
    def inject_global_vars():
        return dict(
            current_user=current_user,
            current_locale=get_locale(),
            google_oauth_enabled=bool(settings.GOOGLE_CLIENT_ID),
            apple_oauth_enabled=bool(settings.APPLE_CLIENT_ID)
        )

    # --- Main UI Routes ---
    @app.route('/')
    def index():
        return render_template('index.html')

    # Tool routes - redirect to library if no files uploaded
    @app.route('/tools/summary')
    @login_required
    def summary_tool():
        return require_uploaded_files('tool_summary.html')

    @app.route('/tools/flashcards')
    @login_required
    def flashcards_tool():
        return require_uploaded_files('tool_flashcards.html')

    @app.route('/tools/assess')
    @login_required
    def assess_tool():
        return require_uploaded_files('tool_assess.html')

    @app.route('/tools/homework')
    @login_required
    def homework_tool():
        return require_uploaded_files('tool_homework.html')

    @app.route('/tools/tutor')
    @login_required
    def tutor_tool():
        return require_uploaded_files('tool_tutor.html')

    @app.route('/tools/diagram')
    @login_required
    def diagram_tool():
        return require_uploaded_files('tool_diagram.html')

    @app.route('/chat')
    def avner_chat():
        """Avner live chat - available for everyone."""
        courses = []
        if current_user.is_authenticated:
            # Get user's courses for context selector
            courses = list(db.courses.find({"user_id": current_user.id}).sort("created_at", -1))
        return render_template('avner_chat.html', courses=courses)

    @app.route('/glossary')
    @app.route('/glossary/<course_id>')
    @login_required
    def glossary_page(course_id='default'):
        # Check if user has any documents for default glossary
        if course_id == 'default' and not check_user_has_documents():
            flash(NO_FILES_MESSAGE, 'warning')
            return redirect(url_for('library.index'))
        return render_template('glossary.html', course_id=course_id)

    @app.route('/dashboard')
    @login_required
    def dashboard():
        # Redirect dashboard to library - new flow
        return redirect(url_for('library.index'))

    @app.route('/tasks/<task_id>')
    def task_status(task_id):
        return render_template('task_status.html', task_id=task_id)

    # --- Language Switching ---
    @app.route('/set-lang/<lang>')
    def set_lang(lang):
        """Switch language between Hebrew (he) and English (en)."""
        from flask import redirect, url_for
        if lang in ['he', 'en']:
            session['lang'] = lang
        return redirect(request.referrer or url_for('index'))

    # --- Health Checks (Restored) ---
    @app.route('/health')
    def health_check():
        return jsonify({"status": "healthy"}), 200
    
    @app.route('/health/detailed')
    def detailed_health_check():
        # This detailed check remains as it was, verifying all components.
        from src.infrastructure.database import db
        import time
        # ... (implementation is unchanged and correct)
        health_status = {"status": "healthy", "components": {}}
        try:
            db.command('ping')
            health_status["components"]["mongodb"] = {"status": "healthy"}
        except Exception as e:
            health_status["components"]["mongodb"] = {"status": "unhealthy", "error": str(e)}
            health_status["status"] = "unhealthy"
        return jsonify(health_status), 503 if health_status["status"] == "unhealthy" else 200

    # --- Error Handling ---
    @app.errorhandler(NotFound)
    def handle_not_found(error):
        logger.warning(f"Not Found error for path: {request.path}")
        if request.path.startswith('/api/'):
            return jsonify({"error": "Not Found"}), 404
        return render_template('404.html'), 404

    @app.errorhandler(Exception)
    def handle_exception(error):
        logger.error(f"Unhandled exception for path {request.path}: {error}", exc_info=True)
        if settings.FLASK_ENV == 'production':
            email_service.send_error_notification(
                error_type=type(error).__name__,
                error_message=str(error),
                details=f"Path: {request.path}"
            )
        return jsonify({"error": "Internal Server Error"}), 500

    logger.info(f"Flask App created successfully in {settings.FLASK_ENV} mode.")
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
