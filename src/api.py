from flask import Flask, request, jsonify, render_template
from typing import Dict
import logging
from services.file_service import FileService
from services.ai_service import AIService

logger = logging.getLogger("studybuddy")
app = Flask(__name__, template_folder="../templates", static_folder="../static")
# enforce safe config
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024  # slightly above per-file limit

file_service = FileService()

class DummyClient:
    def generate(self, prompt: str, timeout: int = 20, **kwargs: Dict) -> str:
        # local stub — replace with real LLM client wrapper
        return f"[תשובת דמו ל: {prompt[:80]}]"

ai_service = AIService(client=DummyClient())

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/api/summarize", methods=["POST"])
def summarize():
    try:
        # support pasted text or file upload
        text: str = request.form.get("text", "").strip()
        uploaded = None

        if not text and "file" in request.files:
            f = request.files["file"]
            uploaded = file_service.validate_and_store(f.stream, f.filename)
            try:
                text = file_service.extract_text(uploaded)
            finally:
                # clean temp on completion
                FileService.cleanup(uploaded)

        if not text:
            return jsonify({"ok": False, "error": "לא הוזן טקסט או קובץ"}), 400

        # send to AI service (service layer)
        result = ai_service.call(prompt=text, params={"task": "summarize"})
        return jsonify({"ok": True, "summary": result})
    except ValueError as ve:
        logger.debug("Validation error in summarize", exc_info=True)
        return jsonify({"ok": False, "error": str(ve)}), 400
    except Exception:
        logger.exception("Unhandled error in summarize")
        return jsonify({"ok": False, "error": "אירעה שגיאה פנימית. אנא נסה שוב."}), 500
