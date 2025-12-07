# worker_utils.py
"""
Worker utility services.

This does NOT define Celery tasks directly, but provides
service classes that Celery tasks / routes can call.

Workers:
- DataWorkerService: storage + DB for documents & indexes.
- ProcessingWorkerService: parse files, build text + chunks + pickled docs.
- AIWorkerService: talk to LLMHandler, retrieve prepared data, build prompts.
- UserCommService: convenience layer for API/HTTP routes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from bson import ObjectId

from infra_utils import MongoHandler, LLMHandler
from models_utils import ModelPurpose, LLMError, MongoError
from file_utils import FileStorage, FileRef, FileType
from document_parsers import (
    DocumentParserDispatcher,
    DocumentText,
    simple_text_chunker,
    pickle_document_text,
    load_pickled_document_text,
)
from validation_utils import ProcessDocumentRequest, AskQuestionRequest

logger = logging.getLogger("studybuddy.workers")


APP_CHAT_REFUSAL_MESSAGE = (
    "אני כאן רק בשביל StudyBuddyAI 🙂\n"
    "אני יכול לעזור רק עם שאלות על האפליקציה, על התכונות שלה, על תקלות, שימוש, פרטיות או חוויית המשתמש.\n"
    "נסה לשאול משהו שקשור לאפליקציה עצמה."
)


# =========================
# DataWorkerService
# =========================

@dataclass
class DataWorkerService:
    """
    Handles all DB + file storage related operations for documents and indexes.
    """

    mongo: MongoHandler
    storage: FileStorage

    # Collection names (logical)
    documents_collection: str = "documents"
    indexes_collection: str = "indexes"

    def store_uploaded_file(
        self,
        *,
        user_id: str,
        content: bytes,
        original_name: Optional[str],
    ) -> str:
        file_ref = self.storage.save_bytes(
            content,
            subdir=f"uploads/{user_id}",
            original_name=original_name,
        )

        doc = {
            "user_id": user_id,
            "file_id": file_ref.id,
            "file_path": str(file_ref.path),
            "original_name": original_name,
            "file_type": file_ref.file_type.value,
            "size_bytes": file_ref.size_bytes,
            "status": "uploaded",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        inserted_id = self.mongo.insert_one(self.documents_collection, doc)
        document_id = str(inserted_id)

        logger.info(
            "DataWorkerService.store_uploaded_file",
            extra={"user_id": user_id, "document_id": document_id, "file_id": file_ref.id},
        )
        return document_id

    def get_document_record(self, document_id: str) -> Optional[Dict[str, Any]]:
        try:
            oid = ObjectId(document_id)
        except Exception:
            oid = document_id
        return self.mongo.find_one(self.documents_collection, {"_id": oid})

    def mark_document_status(self, document_id: str, status: str) -> None:
        try:
            oid = ObjectId(document_id)
        except Exception:
            oid = document_id
        self.mongo.update_one(
            self.documents_collection,
            {"_id": oid},
            {"$set": {"status": status, "updated_at": datetime.utcnow()}},
        )

    def save_index_record(
        self,
        *,
        user_id: str,
        document_id: str,
        chunks_count: int,
        pickle_path: Path,
        extra_meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        doc: Dict[str, Any] = {
            "user_id": user_id,
            "document_id": document_id,
            "chunks_count": chunks_count,
            "pickle_path": str(pickle_path),
            "created_at": datetime.utcnow(),
        }
        if extra_meta:
            doc["meta"] = extra_meta
        index_id = str(self.mongo.insert_one(self.indexes_collection, doc))

        logger.info(
            "DataWorkerService.save_index_record",
            extra={"user_id": user_id, "document_id": document_id, "index_id": index_id},
        )
        return index_id


# =========================
# ProcessingWorkerService
# =========================

@dataclass
class ProcessingWorkerService:
    """
    Handles heavy data processing:
    - Reads FileRefs for documents.
    - Parses them into DocumentText.
    - Builds chunks.
    - Pickles DocumentText for fast reuse.
    - Writes index metadata via DataWorkerService.
    """

    data_worker: DataWorkerService
    parser_dispatcher: DocumentParserDispatcher

    def process_documents(self, req: ProcessDocumentRequest) -> List[str]:
        req.validate()
        index_ids: List[str] = []

        for doc_id in req.document_ids:
            try:
                index_id = self._process_single_document(user_id=req.user_id, document_id=doc_id)
                index_ids.append(index_id)
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "ProcessingWorkerService.process_documents.failed",
                    extra={"user_id": req.user_id, "document_id": doc_id, "error": str(exc)},
                )

        return index_ids

    def _process_single_document(self, user_id: str, document_id: str) -> str:
        try:
            oid = ObjectId(document_id)
        except Exception:
            oid = document_id

        doc_record = self.data_worker.mongo.find_one(
            self.data_worker.documents_collection,
            {"_id": oid},
        )
        if not doc_record:
            raise MongoError(f"Document {document_id} not found.")

        file_path = Path(doc_record["file_path"])
        file_ref = FileRef(
            id=doc_record["file_id"],
            path=file_path,
            original_name=doc_record.get("original_name"),
            file_type=FileType(doc_record["file_type"]),
            size_bytes=doc_record["size_bytes"],
        )

        self.data_worker.mark_document_status(document_id, "processing")

        doc_text = self.parser_dispatcher.parse(file_ref)
        chunks = doc_text.chunks or simple_text_chunker(doc_text.text)

        pickle_dir = self.data_worker.storage._safe_join(f"indexes/{user_id}")
        pickle_dir.mkdir(parents=True, exist_ok=True)
        pickle_path = pickle_dir / f"{document_id}.pkl"
        pickle_document_text(doc_text, pickle_path)

        index_id = self.data_worker.save_index_record(
            user_id=user_id,
            document_id=document_id,
            chunks_count=len(chunks),
            pickle_path=pickle_path,
            extra_meta=doc_text.metadata,
        )
        self.data_worker.mark_document_status(document_id, "ready")

        return index_id


# =========================
# AIWorkerService
# =========================

@dataclass
class AIWorkerService:
    """
    Handles ALL LLM interactions.

    - Validates input (via AskQuestionRequest).
    - Retrieves indexed documents for the user.
    - Loads pickled DocumentText for relevant docs.
    - Builds prompts that constrain the LLM to user data.
    - Calls LLMHandler.chat with proper ModelPurpose.
    - Also handles PROTECTED app-support chat.
    """

    mongo: MongoHandler
    llm: LLMHandler
    storage: FileStorage

    indexes_collection: str = "indexes"

    def answer_question(self, req: AskQuestionRequest) -> str:
        req.validate()

        query: Dict[str, Any] = {"user_id": req.user_id}
        if req.document_ids:
            query["document_id"] = {"$in": req.document_ids}

        cursor = self.mongo.collection(self.indexes_collection).find(query)
        index_docs = list(cursor)
        if not index_docs:
            raise MongoError("No indexed documents found for this request.")

        doc_texts: List[DocumentText] = []
        for idx_doc in index_docs:
            pickle_path = Path(idx_doc["pickle_path"])
            try:
                doc_texts.append(load_pickled_document_text(pickle_path))
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "AIWorkerService.answer_question.skipping_index",
                    extra={"index_id": str(idx_doc.get("_id")), "error": str(exc)},
                )
                continue

        if not doc_texts:
            raise MongoError("No usable indexed documents; pickles missing or corrupted.")

        context_pieces: List[str] = []
        for dt in doc_texts:
            for ch in dt.chunks[:20]:
                context_pieces.append(ch)

        context = "\n\n---\n\n".join(context_pieces)

        system_prompt = (
            "You are StudyBuddy, an assistant that must answer ONLY based on the provided user documents. "
            "If the answer is not in the documents, say you don't know and ask for more info."
        )
        user_prompt = (
            "User question:\n"
            f"{req.question.strip()}\n\n"
            "Relevant study material:\n"
            f"{context}\n\n"
            "Answer in a clear, student-friendly way. If information is missing, say so."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            answer = self.llm.chat(
                messages,
                purpose=ModelPurpose.RAG_QUERY,
                require_reasoning=True,
                metadata={"user_id": req.user_id, "doc_count": len(doc_texts)},
            )
        except LLMError:
            logger.exception(
                "AIWorkerService.answer_question.llm_failed",
                extra={"user_id": req.user_id},
            )
            raise

        return answer

    # ---------- Protected app chat ----------

    def app_support_chat(self, user_id: str, message: str) -> str:
        """
        Handle chat messages that are ONLY allowed to be about the StudyBuddy app.
        """
        msg_clean = (message or "").strip()
        if not msg_clean:
            return (
                "אנא כתוב שאלה או תיאור קצר של הבעיה שלך עם StudyBuddyAI 🙂"
            )

        classifier_system_prompt = (
            "You are a simple classifier.\n"
            "Decide if the user message is about the StudyBuddy web app called "
            "\"StudyBuddy\", \"StudyBuddyAI\" or \"CapyBuddy\": its features, usage, bugs, "
            "UI/UX, configuration, performance, security, or data.\n\n"
            "If it IS about the app, respond with exactly: APP_RELATED\n"
            "If it is NOT about the app, respond with exactly: NOT_APP_RELATED\n"
            "No explanations. No other words."
        )

        classifier_messages = [
            {"role": "system", "content": classifier_system_prompt},
            {"role": "user", "content": msg_clean},
        ]

        try:
            classification = self.llm.chat(
                classifier_messages,
                purpose=ModelPurpose.CHAT_LIGHT,
                require_reasoning=False,
                metadata={
                    "mode": "app_chat_classifier",
                    "user_id": user_id,
                },
                temperature=0.0,
                max_tokens=4,
            ).strip().upper()
        except LLMError:
            logger.exception(
                "AIWorkerService.app_support_chat.classifier_failed",
                extra={"user_id": user_id},
            )
            return APP_CHAT_REFUSAL_MESSAGE

        if classification != "APP_RELATED":
            return APP_CHAT_REFUSAL_MESSAGE

        support_system_prompt = (
            "You are StudyBuddy Support Assistant.\n"
            "You must ONLY answer questions about the StudyBuddy / StudyBuddyAI / CapyBuddy application.\n"
            "Allowed topics:\n"
            "- how to use the app and its tools\n"
            "- uploads, parsing, flashcards, summaries\n"
            "- UI issues, bugs, errors, account behavior\n"
            "- performance, data storage, privacy, security\n"
            "- understanding features and workflows\n\n"
            "You are NOT allowed to answer general knowledge questions, school material, "
            "coding questions, life advice, or anything not directly related to the StudyBuddy app.\n"
            "If the question is not about the app, politely refuse and explain that you only support StudyBuddy."
        )

        support_messages = [
            {"role": "system", "content": support_system_prompt},
            {"role": "user", "content": msg_clean},
        ]

        purpose = (
            ModelPurpose.CHAT_DEEP if len(msg_clean) > 300 else ModelPurpose.CHAT_LIGHT
        )

        try:
            answer = self.llm.chat(
                support_messages,
                purpose=purpose,
                require_reasoning=False,
                metadata={
                    "mode": "app_support_chat",
                    "user_id": user_id,
                },
            )
            return answer
        except LLMError:
            logger.exception(
                "AIWorkerService.app_support_chat.llm_failed",
                extra={"user_id": user_id},
            )
            return (
                "קרה משהו בצד ה-AI בזמן שניסיתי לעזור 😅\n"
                "נסה שוב עוד כמה רגעים, ואם זה ממשיך לחזור – דווח על התקלה."
            )


# =========================
# UserCommService
# =========================

@dataclass
class UserCommService:
    """
    High-level façade to be used by HTTP routes / API layer.

    - Accepts uploads.
    - Triggers processing.
    - Forwards questions to AIWorkerService.
    - Provides protected app-support chat.
    """

    data_worker: DataWorkerService
    processing_worker: ProcessingWorkerService
    ai_worker: AIWorkerService

    def handle_upload(
        self,
        *,
        user_id: str,
        file_bytes: bytes,
        filename: Optional[str],
    ) -> str:
        return self.data_worker.store_uploaded_file(
            user_id=user_id,
            content=file_bytes,
            original_name=filename,
        )

    def handle_processing_request(self, user_id: str, document_ids: List[str]) -> List[str]:
        req = ProcessDocumentRequest(user_id=user_id, document_ids=document_ids)
        return self.processing_worker.process_documents(req)

    def handle_question(
        self,
        *,
        user_id: str,
        question: str,
        document_ids: Optional[List[str]] = None,
    ) -> str:
        req = AskQuestionRequest(user_id=user_id, question=question, document_ids=document_ids)
        return self.ai_worker.answer_question(req)

    def handle_app_chat(self, user_id: str, message: str) -> str:
        return self.ai_worker.app_support_chat(user_id=user_id, message=message)