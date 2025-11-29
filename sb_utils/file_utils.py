from dataclasses import dataclass
from typing import IO, Optional
import os
import tempfile
import shutil
import logging
import mimetypes
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class UploadedFile:
    filename: str
    content_type: str
    size: int
    temp_path: str

# ...existing code...

ALLOWED_MIMETYPES = {
    "text/plain",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/png",
    "image/jpeg",
}

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB - single file limit (constant, no magic numbers)

def secure_name(filename: str) -> str:
    # Minimal secure filename: keep basename, remove path separators, limit length
    name = os.path.basename(filename)
    name = name.replace("\x00", "")  # strip null bytes
    # reduce length and remove problematic chars
    safe = "".join(c for c in name if c.isalnum() or c in " ._-")
    return safe[:200]

def digest_name(filename: str) -> str:
    # deterministic hashed filename to avoid collisions
    h = hashlib.sha256(filename.encode("utf-8")).hexdigest()[:12]
    base, ext = os.path.splitext(secure_name(filename))
    return f"{base[:80]}-{h}{ext}"

def allowed_mimetype(mime: Optional[str]) -> bool:
    return mime in ALLOWED_MIMETYPES

def save_stream_to_temp(stream: IO[bytes], original_filename: str, max_size: int = MAX_FILE_SIZE_BYTES) -> UploadedFile:
    tmp_dir = tempfile.mkdtemp(prefix="studybuddy_upload_")
    safe = digest_name(original_filename)
    temp_path = os.path.join(tmp_dir, safe)
    total = 0
    with open(temp_path, "wb") as f:
        for chunk in iter(lambda: stream.read(4096), b""):
            if not chunk:
                break
            total += len(chunk)
            if total > max_size:
                # cleanup and raise
                f.close()
                shutil.rmtree(tmp_dir, ignore_errors=True)
                raise ValueError("oversize")
            f.write(chunk)
    mime, _ = mimetypes.guess_type(original_filename)
    uploaded = UploadedFile(filename=secure_name(original_filename), content_type=mime or "application/octet-stream", size=total, temp_path=temp_path)
    logger.debug("Saved upload to temp (path hidden): size=%d, mime=%s", total, uploaded.content_type)
    return uploaded

def clean_temp_path(path: str) -> None:
    # delete temp dir safely
    try:
        base = os.path.dirname(path)
        shutil.rmtree(base, ignore_errors=True)
    except Exception:
        logger.warning("Failed to clean temp path", exc_info=True)

