from flask import Blueprint, render_template, abort
from src.infrastructure.database import db

results_bp = Blueprint('results_bp', __name__)


@results_bp.route('/<string:result_id>')
def get_result(result_id: str):
    """
    Fetches a result by its ID and renders the appropriate partial.
    The result_id prefix (e.g., 'summary_', 'flashcards_') determines the type.
    """
    if result_id.startswith('summary_'):
        result_data = db.summaries.find_one({"_id": result_id})
        if not result_data:
            abort(404)
        return render_template('results/summary_result.html', summary=result_data)

    elif result_id.startswith('flashcards_'):
        result_data = db.flashcards.find_one({"_id": result_id})
        if not result_data:
            abort(404)
        return render_template('results/flashcards_result.html', flashcard_set=result_data)

    elif result_id.startswith('assessment_'):
        result_data = db.assessments.find_one({"_id": result_id})
        if not result_data:
            abort(404)
        return render_template('results/assessment_result.html', assessment=result_data)

    # For homework helper, the result is the text itself
    return render_template('results/homework_result.html', solution_text=result_id)
