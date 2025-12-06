"""
🎓 Admin Teaching Interface API

Admin-only routes for teaching and improving Avner.

SECURITY: Requires admin authentication.
PURPOSE: Let admins improve AI personalization and teaching.
"""

from flask import Blueprint, request, jsonify
from functools import wraps

from src.services.avner_learning import (
    admin_teaching,
    usage_analytics,
    preference_learner,
    continuous_improvement
)
from src.services.auth_service import verify_admin  # You'll need to implement this
from sb_utils.logger_utils import logger


# Create blueprint
admin_learning_bp = Blueprint('admin_learning', __name__, url_prefix='/api/admin/learning')


# Admin authentication decorator
def admin_required(f):
    """Decorator to require admin authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get auth token from header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({"error": "No authorization header"}), 401
        
        # Extract token
        try:
            token = auth_header.split(' ')[1]  # "Bearer <token>"
        except IndexError:
            return jsonify({"error": "Invalid authorization header"}), 401
        
        # Verify admin (you'll need to implement this)
        # For now, we'll check for a simple admin token
        # TODO: Implement proper admin verification
        if token != "ADMIN_TOKEN_HERE":  # Replace with real auth
            return jsonify({"error": "Admin access required"}), 403
        
        # Get admin ID from token (implement this)
        request.admin_id = "admin_user"  # Replace with real admin ID extraction
        
        return f(*args, **kwargs)
    
    return decorated_function


# ============================================================================
# ANALYTICS & INSIGHTS
# ============================================================================

@admin_learning_bp.route('/dashboard', methods=['GET'])
@admin_required
def get_dashboard():
    """
    Get admin dashboard with learning statistics.
    
    GET /api/admin/learning/dashboard
    
    Returns:
        Dashboard stats and insights
    """
    try:
        stats = admin_teaching.get_admin_dashboard_stats()
        
        return jsonify({
            "success": True,
            "stats": stats
        }), 200
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@admin_learning_bp.route('/usage-patterns', methods=['GET'])
@admin_required
def get_usage_patterns():
    """
    Get usage patterns (anonymized).
    
    GET /api/admin/learning/usage-patterns
    
    Query params:
        - task_type: Filter by task type
        - study_level: Filter by study level
    
    Returns:
        Aggregated usage patterns
    """
    try:
        filters = {}
        if request.args.get('task_type'):
            filters['task_type'] = request.args.get('task_type')
        if request.args.get('study_level'):
            filters['study_level'] = request.args.get('study_level')
        
        patterns = usage_analytics.get_usage_patterns(filters)
        
        return jsonify({
            "success": True,
            "patterns": patterns,
            "count": len(patterns)
        }), 200
        
    except Exception as e:
        logger.error(f"Usage patterns error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ============================================================================
# TEACHING EXAMPLES
# ============================================================================

@admin_learning_bp.route('/teaching-examples', methods=['POST'])
@admin_required
def add_teaching_example():
    """
    Add a teaching example.
    
    POST /api/admin/learning/teaching-examples
    
    Body:
        {
            "category": "preference_detection|teaching_style|response_adaptation",
            "example_input": "Example user input",
            "ideal_response": "How Avner should respond",
            "explanation": "Why this is ideal",
            "tags": ["tag1", "tag2"]
        }
    
    Returns:
        Example ID
    """
    try:
        data = request.json
        
        # Validate required fields
        required = ['category', 'example_input', 'ideal_response', 'explanation']
        if not all(field in data for field in required):
            return jsonify({"error": "Missing required fields"}), 400
        
        example_id = admin_teaching.add_teaching_example(
            admin_id=request.admin_id,
            category=data['category'],
            example_input=data['example_input'],
            ideal_response=data['ideal_response'],
            explanation=data['explanation'],
            tags=data.get('tags', [])
        )
        
        return jsonify({
            "success": True,
            "example_id": example_id,
            "message": "Teaching example added successfully"
        }), 201
        
    except Exception as e:
        logger.error(f"Add teaching example error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@admin_learning_bp.route('/teaching-examples', methods=['GET'])
@admin_required
def get_teaching_examples():
    """
    Get teaching examples.
    
    GET /api/admin/learning/teaching-examples
    
    Query params:
        - category: Filter by category
        - tags: Comma-separated tags
    
    Returns:
        List of teaching examples
    """
    try:
        category = request.args.get('category')
        tags = request.args.get('tags')
        tags_list = tags.split(',') if tags else None
        
        examples = admin_teaching.get_teaching_examples(category, tags_list)
        
        return jsonify({
            "success": True,
            "examples": examples,
            "count": len(examples)
        }), 200
        
    except Exception as e:
        logger.error(f"Get teaching examples error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ============================================================================
# IMPROVEMENT RULES
# ============================================================================

@admin_learning_bp.route('/improvement-rules', methods=['POST'])
@admin_required
def add_improvement_rule():
    """
    Add an improvement rule.
    
    POST /api/admin/learning/improvement-rules
    
    Body:
        {
            "rule_type": "preference_adjustment|response_enhancement|teaching_strategy",
            "condition": {
                "proficiency_level": "beginner",
                "task_type": "summary"
            },
            "action": {
                "add_examples": true,
                "simplify_language": true
            },
            "description": "Human-readable explanation"
        }
    
    Returns:
        Rule ID
    """
    try:
        data = request.json
        
        # Validate required fields
        required = ['rule_type', 'condition', 'action', 'description']
        if not all(field in data for field in required):
            return jsonify({"error": "Missing required fields"}), 400
        
        rule_id = admin_teaching.add_improvement_rule(
            admin_id=request.admin_id,
            rule_type=data['rule_type'],
            condition=data['condition'],
            action=data['action'],
            description=data['description']
        )
        
        return jsonify({
            "success": True,
            "rule_id": rule_id,
            "message": "Improvement rule added successfully"
        }), 201
        
    except Exception as e:
        logger.error(f"Add improvement rule error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@admin_learning_bp.route('/improvement-rules', methods=['GET'])
@admin_required
def get_improvement_rules():
    """
    Get improvement rules.
    
    GET /api/admin/learning/improvement-rules
    
    Query params:
        - rule_type: Filter by rule type
        - active: Filter by active status (true/false)
    
    Returns:
        List of improvement rules
    """
    try:
        rule_type = request.args.get('rule_type')
        
        rules = admin_teaching.get_improvement_rules(rule_type)
        
        return jsonify({
            "success": True,
            "rules": rules,
            "count": len(rules)
        }), 200
        
    except Exception as e:
        logger.error(f"Get improvement rules error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@admin_learning_bp.route('/improvement-rules/<rule_id>', methods=['PUT'])
@admin_required
def update_improvement_rule(rule_id):
    """
    Update an improvement rule (enable/disable).
    
    PUT /api/admin/learning/improvement-rules/<rule_id>
    
    Body:
        {
            "active": true/false
        }
    
    Returns:
        Success status
    """
    try:
        data = request.json
        
        admin_teaching.db.admin_improvement_rules.update_one(
            {"_id": rule_id},
            {"$set": {"active": data.get('active', True)}}
        )
        
        return jsonify({
            "success": True,
            "message": "Rule updated successfully"
        }), 200
        
    except Exception as e:
        logger.error(f"Update improvement rule error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ============================================================================
# USER BEHAVIOR ANALYSIS
# ============================================================================

@admin_learning_bp.route('/analyze-user/<user_id>', methods=['GET'])
@admin_required
def analyze_user_behavior(user_id):
    """
    Analyze a specific user's behavior (for understanding patterns).
    
    GET /api/admin/learning/analyze-user/<user_id>
    
    🔒 PRIVACY: Returns patterns only, not actual content.
    
    Returns:
        Behavior analysis and suggestions
    """
    try:
        analysis = preference_learner.analyze_user_behavior(user_id)
        
        return jsonify({
            "success": True,
            "analysis": analysis
        }), 200
        
    except Exception as e:
        logger.error(f"Analyze user behavior error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ============================================================================
# TEST & PREVIEW
# ============================================================================

@admin_learning_bp.route('/test-enhancement', methods=['POST'])
@admin_required
def test_enhancement():
    """
    Test how learnings would enhance a prompt.
    
    POST /api/admin/learning/test-enhancement
    
    Body:
        {
            "base_prompt": "Explain photosynthesis",
            "user_id": "user123",
            "task_type": "summary",
            "user_prefs": {
                "proficiency_level": "beginner",
                "study_level": "high_school"
            }
        }
    
    Returns:
        Original and enhanced prompts for comparison
    """
    try:
        data = request.json
        
        base_prompt = data.get('base_prompt', '')
        user_id = data.get('user_id', 'test_user')
        task_type = data.get('task_type', 'standard')
        user_prefs = data.get('user_prefs', {})
        
        enhanced_prompt = continuous_improvement.enhance_prompt_with_learnings(
            base_prompt=base_prompt,
            user_id=user_id,
            task_type=task_type,
            user_prefs=user_prefs
        )
        
        return jsonify({
            "success": True,
            "original": base_prompt,
            "enhanced": enhanced_prompt,
            "improvements": enhanced_prompt != base_prompt
        }), 200
        
    except Exception as e:
        logger.error(f"Test enhancement error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# Export blueprint
__all__ = ['admin_learning_bp']
