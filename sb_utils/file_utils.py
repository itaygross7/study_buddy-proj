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
    """
    Represents a single uploaded file stored temporarily on disk.
    """
    filename: str
    content_type: str
    size: int
    temp_path: str

ALLOWED_MIMETYPES = {
    "text/plain",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/png",
    "image/jpeg",
}

# per-file size limit (10MB)
MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024

_CHUNK_SIZE_BYTES: int = 4096  # for streaming reads

def secure_name(filename: str) -> str:
    """
    Minimal secure filename: remove path components and null bytes
    and restrict characters + length.
    """
    name = os.path.basename(filename or "")
    name = name.replace("\x00", "")  # strip null bytes
    safe = "".join(c for c in name if c.isalnum() or c in " ._-")
    return safe[:200]

def digest_name(filename: str) -> str:
    """
    Deterministic hashed filename to avoid collisions and leaking originals.
    """
    safe_original = secure_name(filename)
    h = hashlib.sha256(safe_original.encode("utf-8")).hexdigest()[:12]
    base, ext = os.path.splitext(safe_original)
    return f"{base[:80]}-{h}{ext}"

def allowed_mimetype(mime: Optional[str]) -> bool:
    return mime in ALLOWED_MIMETYPES

def save_stream_to_temp(
    stream: IO[bytes],
    original_filename: str,
    max_size: int = MAX_FILE_SIZE_BYTES,
) -> UploadedFile:
    """
    Stream an upload to a unique temp directory, enforcing a size limit.
    Does not log filename or content.
    """
    tmp_dir = tempfile.mkdtemp(prefix="studybuddy_upload_")
    safe = digest_name(original_filename)
    temp_path = os.path.join(tmp_dir, safe)
    total = 0

    try:
        with open(temp_path, "wb") as f:
            for chunk in iter(lambda: stream.read(_CHUNK_SIZE_BYTES), b""):
                if not chunk:
                    break
                total += len(chunk)
                if total > max_size:
                    # cleanup and raise
                    f.close()
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                    logger.debug("Upload rejected: size exceeded limit bytes=%d", max_size)
                    raise ValueError("oversize")
                f.write(chunk)
    except Exception:
        # best effort cleanup on failure
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise

    mime, _ = mimetypes.guess_type(original_filename)
    uploaded = UploadedFile(
        filename=secure_name(original_filename),
        content_type=mime or "application/octet-stream",
        size=total,
        temp_path=temp_path,
    )
    # do not log filename or content
    logger.debug("Saved upload to temp (size=%d, mime=%s)", total, uploaded.content_type)
    return uploaded

def clean_temp_path(path: str) -> None:
    """
    Delete the temp directory that contains the given file.
    """
    try:
        base = os.path.dirname(path)
        if base and os.path.isdir(base):
            shutil.rmtree(base, ignore_errors=True)
    except Exception:
        logger.warning("Failed to clean temp upload directory", exc_info=True)
