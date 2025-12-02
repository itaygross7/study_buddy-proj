from flask import Blueprint, render_template, Response, abort
from weasyprint import HTML
from src.infrastructure.database import db

pdf_bp = Blueprint('pdf_bp', __name__)


@pdf_bp.route('/flashcards/<string:set_id>')
def export_flashcards_pdf(set_id: str):
    """
    Generates a PDF for a given flashcard set.
    """
    flashcard_set = db.flashcards.find_one({"_id": set_id})
    if not flashcard_set:
        abort(404)

    # Render an HTML template specifically for PDF output
    html_string = render_template('export/flashcards_pdf.html', flashcard_set=flashcard_set)

    # Use WeasyPrint to generate the PDF
    pdf = HTML(string=html_string).write_pdf()

    return Response(pdf,
                    mimetype='application/pdf',
                    headers={'Content-Disposition': 'attachment;filename=flashcards.pdf'})
