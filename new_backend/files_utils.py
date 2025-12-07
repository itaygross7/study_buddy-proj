# file_utils.py
"""
File utilities.

Responsibilities:
- Safe file paths and storage under a root directory.
- File type detection (by extension + mimetype).
- Save / open / delete / move / copy operations.
- Temp file management.
- Zip utilities.
- Streaming helpers for large files.
"""

from __future__ import annotations

import mimetypes
import os
import shutil
import tempfile
import uuid
import zipfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import BinaryIO, Iterator, List, Optional

from models_utils import FileInfraError


class FileType(str, Enum):
    UNKNOWN = "unknown"
    TXT = "txt"
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    MD = "md"
    HTML = "html"
    EPUB = "epub"
    IMAGE_PNG = "image_png"
    IMAGE_JPEG = "image_jpeg"
    IMAGE_WEBP = "image_webp"
    ZIP = "zip"


@dataclass(frozen=True)
class FileConfig:
    """
    Configuration for file storage.

    root_dir: root directory for persistent storage
    temp_dir: directory for temp files (inside root_dir by default)
    max_file_bytes: global safety limit; you can refine per type later.
    """
    root_dir: Path
    temp_dir: Path
    max_file_bytes: int = 128 * 1024 * 1024  # 128MB default

    @classmethod
    def from_env(
        cls,
        root_env: str = "SB_FILES_ROOT",
        temp_env: str = "SB_FILES_TEMP",
        default_root: str = "./data/files",
        default_temp_name: str = "tmp",
    ) -> "FileConfig":
        root = Path(os.getenv(root_env, default_root)).resolve()
        temp = Path(os.getenv(temp_env, str(root / default_temp_name))).resolve()
        root.mkdir(parents=True, exist_ok=True)
        temp.mkdir(parents=True, exist_ok=True)
        return cls(root_dir=root, temp_dir=temp)


@dataclass(frozen=True)
class FileRef:
    """
    Logical reference to a file in storage.
    """
    id: str
    path: Path
    original_name: Optional[str]
    file_type: FileType
    size_bytes: int


class FileTypeDetector:
    """
    Detect FileType based on extension and mimetype.
    """

    EXT_MAP = {
        ".txt": FileType.TXT,
        ".md": FileType.MD,
        ".pdf": FileType.PDF,
        ".docx": FileType.DOCX,
        ".pptx": FileType.PPTX,
        ".htm": FileType.HTML,
        ".html": FileType.HTML,
        ".epub": FileType.EPUB,
        ".zip": FileType.ZIP,
        ".png": FileType.IMAGE_PNG,
        ".jpg": FileType.IMAGE_JPEG,
        ".jpeg": FileType.IMAGE_JPEG,
        ".webp": FileType.IMAGE_WEBP,
    }

    @classmethod
    def detect(cls, path: Path) -> FileType:
        suffix = path.suffix.lower()
        if suffix in cls.EXT_MAP:
            return cls.EXT_MAP[suffix]

        mime, _ = mimetypes.guess_type(str(path))
        if not mime:
            return FileType.UNKNOWN

        if mime == "application/pdf":
            return FileType.PDF
        if mime in ("text/plain", "text/markdown"):
            return FileType.TXT
        if mime.startswith("image/"):
            if mime == "image/png":
                return FileType.IMAGE_PNG
            if mime in ("image/jpeg", "image/jpg"):
                return FileType.IMAGE_JPEG
            if mime == "image/webp":
                return FileType.IMAGE_WEBP
        if mime == "application/zip":
            return FileType.ZIP

        return FileType.UNKNOWN


class FileStorage:
    """
    Safe file storage manager.
    """

    def __init__(self, config: FileConfig) -> None:
        self.config = config

    # ---------- path helpers ----------

    def _safe_join(self, *parts: str) -> Path:
        path = (self.config.root_dir / Path(*parts)).resolve()
        if not str(path).startswith(str(self.config.root_dir)):
            raise FileInfraError("Attempted to escape root_dir with path.")
        return path

    # ---------- core operations ----------

    def save_bytes(
        self,
        content: bytes,
        *,
        subdir: Optional[str] = None,
        original_name: Optional[str] = None,
    ) -> FileRef:
        if len(content) > self.config.max_file_bytes:
            raise FileInfraError("File too large.")

        file_id = str(uuid.uuid4())
        ext = Path(original_name).suffix if original_name else ""
        dir_path = self._safe_join(subdir or "")
        dir_path.mkdir(parents=True, exist_ok=True)

        file_path = dir_path / f"{file_id}{ext}"
        file_path.write_bytes(content)

        file_type = FileTypeDetector.detect(file_path)
        size = file_path.stat().st_size

        return FileRef(
            id=file_id,
            path=file_path,
            original_name=original_name,
            file_type=file_type,
            size_bytes=size,
        )

    def open_binary(self, file_ref: FileRef) -> BinaryIO:
        return file_ref.path.open("rb")

    def delete(self, file_ref: FileRef) -> None:
        try:
            file_ref.path.unlink(missing_ok=True)
        except Exception as exc:  # noqa: BLE001
            raise FileInfraError(f"Failed to delete file: {exc}") from exc

    def move(self, file_ref: FileRef, *, new_subdir: str) -> FileRef:
        new_dir = self._safe_join(new_subdir)
        new_dir.mkdir(parents=True, exist_ok=True)
        new_path = new_dir / file_ref.path.name
        shutil.move(str(file_ref.path), str(new_path))

        size = new_path.stat().st_size
        file_type = FileTypeDetector.detect(new_path)
        return FileRef(
            id=file_ref.id,
            path=new_path,
            original_name=file_ref.original_name,
            file_type=file_type,
            size_bytes=size,
        )

    def copy(self, file_ref: FileRef, *, new_subdir: str) -> FileRef:
        new_dir = self._safe_join(new_subdir)
        new_dir.mkdir(parents=True, exist_ok=True)
        new_path = new_dir / file_ref.path.name
        shutil.copy2(str(file_ref.path), str(new_path))

        size = new_path.stat().st_size
        file_type = FileTypeDetector.detect(new_path)
        new_id = str(uuid.uuid4())
        return FileRef(
            id=new_id,
            path=new_path,
            original_name=file_ref.original_name,
            file_type=file_type,
            size_bytes=size,
        )

    # ---------- temp files ----------

    def create_temp_file(self, suffix: str = "") -> Path:
        fd, temp_path = tempfile.mkstemp(suffix=suffix, dir=self.config.temp_dir)
        os.close(fd)
        return Path(temp_path).resolve()

    def create_temp_dir(self) -> Path:
        return Path(
            tempfile.mkdtemp(dir=self.config.temp_dir)
        ).resolve()

    # ---------- zips ----------

    def create_zip(self, files: List[FileRef], *, zip_subdir: str = "zips") -> FileRef:
        zip_id = str(uuid.uuid4())
        zip_dir = self._safe_join(zip_subdir)
        zip_dir.mkdir(parents=True, exist_ok=True)
        zip_path = zip_dir / f"{zip_id}.zip"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in files:
                arcname = f.original_name or f"{f.id}{f.path.suffix}"
                zf.write(f.path, arcname=arcname)

        size = zip_path.stat().st_size
        return FileRef(
            id=zip_id,
            path=zip_path,
            original_name=None,
            file_type=FileType.ZIP,
            size_bytes=size,
        )

    def extract_zip(self, zip_ref: FileRef, *, target_subdir: str) -> List[FileRef]:
        if zip_ref.file_type is not FileType.ZIP:
            raise FileInfraError("extract_zip called with non-zip FileRef.")

        target_dir = self._safe_join(target_subdir)
        target_dir.mkdir(parents=True, exist_ok=True)

        extracted_refs: List[FileRef] = []
        with zipfile.ZipFile(zip_ref.path, "r") as zf:
            for name in zf.namelist():
                clean_name = Path(name).name
                if not clean_name:
                    continue
                out_path = target_dir / clean_name
                with zf.open(name) as src, out_path.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
                size = out_path.stat().st_size
                ftype = FileTypeDetector.detect(out_path)
                extracted_refs.append(
                    FileRef(
                        id=str(uuid.uuid4()),
                        path=out_path.resolve(),
                        original_name=clean_name,
                        file_type=ftype,
                        size_bytes=size,
                    )
                )
        return extracted_refs

    # ---------- streaming ----------

    @staticmethod
    def iter_file_chunks(
        file_ref: FileRef,
        chunk_size: int = 8192,
    ) -> Iterator[bytes]:
        with file_ref.path.open("rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk