import os
from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS
from flask_login import current_user, login_required
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
from src.api.routes_webhook import webhook_bp
from src.api.routes_glossary import glossary_bp
from src.api.routes_tutor import tutor_bp
from src.api.routes_diagram import diagram_bp
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

    @app.route('/tool/tutor')
    @login_required
    def tutor_tool():
        return render_template('tool_tutor.html')
    
    @app.route('/tool/diagram')
    @login_required
    def diagram_tool():
        return render_template('tool_diagram.html')
    
    @app.route('/glossary/<course_id>')
    @login_required
    def glossary_page(course_id):
        return render_template('glossary.html', course_id=course_id)

    # --- Health Check ---
    @app.route('/health')
    def health_check():
        """Basic health check endpoint."""
        return jsonify({"status": "healthy"}), 200
    
    @app.route('/health/detailed')
    def detailed_health_check():
        """Detailed health check for all components."""
        from src.infrastructure.database import db
        import time
        
        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "components": {}
        }
        
        overall_healthy = True
        
        # Check MongoDB
        try:
            db.command('ping')
            health_status["components"]["mongodb"] = {
                "status": "healthy",
                "message": "Connected"
            }
        except Exception as e:
            health_status["components"]["mongodb"] = {
                "status": "unhealthy",
                "message": f"Error: {str(e)}"
            }
            overall_healthy = False
        
        # Check RabbitMQ (if available)
        try:
            import pika
            params = pika.URLParameters(settings.RABBITMQ_URI)
            connection = pika.BlockingConnection(params)
            connection.close()
            health_status["components"]["rabbitmq"] = {
                "status": "healthy",
                "message": "Connected"
            }
        except Exception as e:
            health_status["components"]["rabbitmq"] = {
                "status": "unhealthy",
                "message": f"Error: {str(e)}"
            }
            overall_healthy = False
        
        # Check AI service availability
        try:
            if settings.GEMINI_API_KEY or settings.OPENAI_API_KEY:
                health_status["components"]["ai_service"] = {
                    "status": "healthy",
                    "message": "API keys configured"
                }
            else:
                health_status["components"]["ai_service"] = {
                    "status": "unhealthy",
                    "message": "No API keys configured"
                }
                overall_healthy = False
        except Exception as e:
            health_status["components"]["ai_service"] = {
                "status": "unhealthy",
                "message": f"Error: {str(e)}"
            }
            overall_healthy = False
        
        # Check email service
        try:
            if settings.MAIL_USERNAME and settings.MAIL_PASSWORD:
                health_status["components"]["email_service"] = {
                    "status": "healthy",
                    "message": "SMTP configured"
                }
            else:
                health_status["components"]["email_service"] = {
                    "status": "degraded",
                    "message": "SMTP not configured (optional)"
                }
        except Exception as e:
            health_status["components"]["email_service"] = {
                "status": "degraded",
                "message": f"Error: {str(e)}"
            }
        
        health_status["status"] = "healthy" if overall_healthy else "unhealthy"
        status_code = 200 if overall_healthy else 503
        
        return jsonify(health_status), status_code
    
    @app.route('/health/ready')
    def readiness_check():
        """Kubernetes-style readiness probe."""
        from src.infrastructure.database import db
        
        try:
            # Check if app can serve requests
            db.command('ping')
            return jsonify({"status": "ready"}), 200
        except Exception as e:
            return jsonify({"status": "not ready", "error": str(e)}), 503
    
    @app.route('/health/live')
    def liveness_check():
        """Kubernetes-style liveness probe."""
        # Simple check that the app is running
        return jsonify({"status": "alive"}), 200

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
    port = int(os.environ.get("PORT", 5000))
    host = '0.0.0.0'
    
    logger.info(f"Starting StudyBuddy server on {host}:{port}")
    logger.info(f"Server will be accessible at:")
    logger.info(f"  - Local: http://localhost:{port}")
    logger.info(f"  - Network: http://<your-ip>:{port}")
    logger.info(f"")
    logger.info(f"To access from another computer:")
    logger.info(f"  1. Find your IP: hostname -I")
    logger.info(f"  2. Open firewall: sudo ufw allow {port}/tcp")
    logger.info(f"  3. Access via: http://<your-ip>:{port}")
    logger.info(f"")
    logger.info(f"For help, see: docs/NETWORK_ACCESS.md")
    
    app.run(host=host, port=port)
