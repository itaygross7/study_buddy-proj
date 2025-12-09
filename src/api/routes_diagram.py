from flask import Blueprint, request, jsonify
from flask_login import login_required

from src.services.ai_client import ai_client
from sb_utils.logger_utils import logger

diagram_bp = Blueprint('diagram', __name__)


@diagram_bp.route('/generate', methods=['POST'])
@login_required
def generate_diagram():
    try:
        data = request.get_json() or {}
        topic = data.get('topic', '').strip()
        diagram_type = data.get('type', 'flowchart').strip()

        if not topic:
            return jsonify({"success": False, "error": "Topic is required"}), 400

        valid_types = ['flowchart', 'mindmap', 'timeline', 'sequence', 'class', 'state']
        if diagram_type not in valid_types:
            diagram_type = 'flowchart'

        prompt = f"""
        Create a {diagram_type} diagram for the topic: "{topic}"

        Return ONLY valid Mermaid.js code, no explanations or markdown code blocks.
        The diagram should be clear, well-structured, and educational.

        For flowchart, use: flowchart TD
        For mindmap, use: mindmap
        For timeline, use: timeline
        For sequence, use: sequenceDiagram
        For class diagram, use: classDiagram
        For state diagram, use: stateDiagram-v2
        """

        mermaid_code = ai_client.generate_text(
            prompt=prompt,
            context="",
            task_type="diagram",
        )

        mermaid_code = mermaid_code.strip()
        if mermaid_code.startswith('```mermaid'):
            mermaid_code = mermaid_code[len('```mermaid'):].strip()
        if mermaid_code.startswith('```'):
            mermaid_code = mermaid_code[3:].strip()
        if mermaid_code.endswith('```'):
            mermaid_code = mermaid_code[:-3].strip()

        return jsonify({
            "success": True,
            "mermaid_code": mermaid_code,
            "diagram_type": diagram_type
        }), 200

    except Exception as e:
        logger.error(f"Error generating diagram: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500
