import os
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from werkzeug.exceptions import NotFound

from src.infrastructure.config import settings
from src.infrastructure.database import db
from sb_utils.logger_utils import logger

# Import Blueprints
from src.api.routes_summary import summary_bp
from src.api.routes_flashcards import flashcards_bp
from src.api.routes_assess import assess_bp
from src.api.routes_homework import homework_bp
from src.api.routes_upload import upload_bp
from src.api.routes_task import task_bp
from src.api.routes_results import results_bp # New
from src.api.routes_pdf import pdf_bp         # New


def create_app():
    """Application factory for Flask."""
    app = Flask(__name__, template_folder='ui/templates', static_folder='ui/static')
    app.config.from_object(settings)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Initialize extensions
    db.init_app(app)

    # Register Blueprints
    app.register_blueprint(summary_bp, url_prefix='/api/summary')
    app.register_blueprint(flashcards_bp, url_prefix='/api/flashcards')
    app.register_blueprint(assess_bp, url_prefix='/api/assess')
    app.register_blueprint(homework_bp, url_prefix='/api/homework')
    app.register_blueprint(upload_bp, url_prefix='/api/upload')
    app.register_blueprint(task_bp, url_prefix='/api/tasks')
    app.register_blueprint(results_bp, url_prefix='/results') # New
    app.register_blueprint(pdf_bp, url_prefix='/export/pdf')   # New

    # --- Main UI Routes ---
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/tool/summary')
    def summary_tool():
        return render_template('tool_summary.html')

    @app.route('/tool/flashcards')
    def flashcards_tool():
        return render_template('tool_flashcards.html')

    @app.route('/tool/assess')
    def assess_tool():
        return render_template('tool_assess.html')

    @app.route('/tool/homework')
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
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred."
        }), 500

    logger.info("Flask App created successfully.")
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
