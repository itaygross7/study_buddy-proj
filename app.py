import os
from flask import Flask, jsonify, render_template, request, send_from_directory, g
from flask_cors import CORS
from flask_login import LoginManager, current_user, login_required
from werkzeug.exceptions import NotFound

from src.infrastructure.config import settings
from src.infrastructure.database import init_app as init_db
from sb_utils.logger_utils import logger
from src.services import email_service

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
from src.services import auth_service


def create_app():
    """Application factory for Flask."""
    app = Flask(__name__, template_folder='ui/templates', static_folder='ui/static')
    
    # Add Avner images folder as additional static path
    avner_folder = os.path.join(os.path.dirname(__file__), 'ui', 'Avner')
    
    @app.route('/avner/<path:filename>')
    def serve_avner(filename):
        """Serve Avner mascot images from ui/Avner folder."""
        return send_from_directory(avner_folder, filename)
    
    # Configure from settings
    app.config['MONGO_URI'] = settings.MONGO_URI
    app.config['SECRET_KEY'] = settings.SECRET_KEY
    app.config['FLASK_ENV'] = settings.FLASK_ENV
    
    # Security settings
    app.config['SESSION_COOKIE_SECURE'] = settings.SESSION_COOKIE_SECURE
    app.config['SESSION_COOKIE_HTTPONLY'] = settings.SESSION_COOKIE_HTTPONLY
    app.config['SESSION_COOKIE_SAMESITE'] = settings.SESSION_COOKIE_SAMESITE
    
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    # Initialize extensions
    init_db(app)
    
    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'יש להתחבר כדי לגשת לעמוד זה'
    login_manager.login_message_category = 'warning'
    
    # Initialize OAuth (Google/Apple Sign-In)
    init_oauth(app)
    
    # Create admin user if configured
    with app.app_context():
        from src.infrastructure.database import db
        auth_service.create_admin_if_not_exists(db)

    # Register Blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(oauth_bp, url_prefix='/oauth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(library_bp, url_prefix='/library')
    app.register_blueprint(avner_bp, url_prefix='/api/avner')
    app.register_blueprint(summary_bp, url_prefix='/api/summary')
    app.register_blueprint(flashcards_bp, url_prefix='/api/flashcards')
    app.register_blueprint(assess_bp, url_prefix='/api/assess')
    app.register_blueprint(homework_bp, url_prefix='/api/homework')
    app.register_blueprint(upload_bp, url_prefix='/api/upload')
    app.register_blueprint(task_bp, url_prefix='/api/tasks')
    app.register_blueprint(results_bp, url_prefix='/results')
    app.register_blueprint(pdf_bp, url_prefix='/export/pdf')
    
    # Context processor to make current_user available in templates
    @app.context_processor
    def inject_user():
        return dict(current_user=current_user)

    # --- Main UI Routes ---
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/tool/summary')
    @login_required
    def summary_tool():
        return render_template('tool_summary.html')

    @app.route('/tool/flashcards')
    @login_required
    def flashcards_tool():
        return render_template('tool_flashcards.html')

    @app.route('/tool/assess')
    @login_required
    def assess_tool():
        return render_template('tool_assess.html')

    @app.route('/tool/homework')
    @login_required
    def homework_tool():
        return render_template('tool_homework.html')

    # --- Health Check ---
    @app.route('/health')
    def health_check():
        return jsonify({"status": "healthy"}), 200

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
        # Send error notification to admin
        email_service.send_error_notification(
            error_type=type(error).__name__,
            error_message=str(error),
            details=f"Path: {request.path}"
        )
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred."
        }), 500

    logger.info("Flask App created successfully.")
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
