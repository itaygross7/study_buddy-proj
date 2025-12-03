"""Webhook routes for auto-updates and maintenance."""
import hmac
import hashlib
import subprocess
from flask import Blueprint, request, jsonify
from functools import wraps

from src.infrastructure.config import settings
from sb_utils.logger_utils import logger

webhook_bp = Blueprint('webhook', __name__)

# Webhook secret for GitHub webhook verification
WEBHOOK_SECRET = settings.WEBHOOK_SECRET if hasattr(settings, 'WEBHOOK_SECRET') else None


def verify_signature(f):
    """Decorator to verify GitHub webhook signature."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not WEBHOOK_SECRET:
            logger.warning("Webhook secret not configured, skipping verification")
            return f(*args, **kwargs)
        
        signature = request.headers.get('X-Hub-Signature-256')
        if not signature:
            logger.error("No signature provided in webhook request")
            return jsonify({"error": "No signature provided"}), 403
        
        # Compute expected signature
        mac = hmac.new(
            WEBHOOK_SECRET.encode(),
            msg=request.data,
            digestmod=hashlib.sha256
        )
        expected_signature = 'sha256=' + mac.hexdigest()
        
        # Verify signature
        if not hmac.compare_digest(signature, expected_signature):
            logger.error("Invalid webhook signature")
            return jsonify({"error": "Invalid signature"}), 403
        
        return f(*args, **kwargs)
    return decorated_function


@webhook_bp.route('/update', methods=['POST'])
@verify_signature
def handle_update():
    """
    Handle GitHub webhook for auto-updates.
    
    Triggered when code is pushed to main branch.
    Runs the auto-update script to pull changes and restart.
    """
    try:
        data = request.json
        
        # Check if this is a push to main branch
        if data.get('ref') != 'refs/heads/main':
            return jsonify({
                "status": "ignored",
                "message": "Not a push to main branch"
            })
        
        logger.info(f"Received update webhook from GitHub")
        logger.info(f"Commits: {len(data.get('commits', []))}")
        
        # Run auto-update script in background
        try:
            result = subprocess.Popen(
                ['/bin/bash', './scripts/auto-update.sh'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True  # Detach from parent
            )
            
            logger.info(f"Auto-update script started (PID: {result.pid})")
            
            return jsonify({
                "status": "success",
                "message": "Update triggered",
                "commits": len(data.get('commits', []))
            })
            
        except Exception as e:
            logger.error(f"Failed to run auto-update script: {e}")
            return jsonify({
                "status": "error",
                "message": "Failed to trigger update"
            }), 500
    
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@webhook_bp.route('/health', methods=['GET'])
def health():
    """Health check endpoint for the webhook service."""
    return jsonify({
        "status": "healthy",
        "webhook_configured": WEBHOOK_SECRET is not None
    })
