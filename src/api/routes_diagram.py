from flask import Blueprint, jsonify, request
from flask_login import login_required
from src.services.ai_client import ai_client
from sb_utils.logger_utils import logger

diagram_bp = Blueprint('diagram', __name__)


@diagram_bp.route('/generate', methods=['POST'])
@login_required
def generate_diagram():
    """
    Generate a Mermaid.js diagram from a topic description.
    """
    try:
        data = request.get_json()
        topic = data.get('topic', '')
        diagram_type = data.get('type', 'flowchart')  # flowchart, mindmap, timeline, etc.
        
        if not topic:
            return jsonify({"success": False, "error": "Topic is required"}), 400
        
        # Validate diagram type
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
        
        Example flowchart format:
        flowchart TD
            A[Start] --> B[Step 1]
            B --> C[Step 2]
            C --> D[End]
        
        Return only the Mermaid code.
        """
        
        mermaid_code = ai_client.generate_text(
            prompt=prompt,
            context="",
            task_type="standard"
        )
        
        # Clean up the response - remove markdown code blocks if present
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
        return jsonify({"success": False, "error": str(e)}), 500
