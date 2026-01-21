import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from langchain_core.language_models import BaseChatModel

from api.dependencies import get_knowledge_store, get_optional_llm
from utils.document_text_extractor import (
    DocumentTextExtractionError,
    OptionalDependencyMissingError,
    UnsupportedDocumentTypeError,
    extract_text_from_upload,
)
from vector_store.knowledge_store import KnowledgeStore

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/rag/upload", tags=["RAG"])
async def upload_documents(
    files: list[UploadFile],
    store: Annotated[Optional[KnowledgeStore], Depends(get_knowledge_store)],
):
    """
    Upload documents and index for local RAG (CE-safe).
    PDF/DOCX require optional dependencies; unsupported types return a 422 when nothing is indexed.
    """
    if not store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge store is not available",
        )

    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    total_chunks = 0
    errors: list[str] = []
    for f in files:
        try:
            content_type = (f.content_type or "").lower()
            name = f.filename or "unknown"
            data = await f.read()
            try:
                text = extract_text_from_upload(
                    filename=name,
                    content_type=content_type,
                    data=data,
                )
            except (UnsupportedDocumentTypeError, OptionalDependencyMissingError) as e:
                errors.append(str(e))
                continue
            except DocumentTextExtractionError as e:
                errors.append(f"{name}: {e}")
                continue

            if not text.strip():
                errors.append(f"{name}: No extractable text found")
                continue

            try:
                added = store.ingest_text(text=text, source=name)
                total_chunks += added
            except Exception as e:
                logger.warning("Failed to ingest %s: %s", f.filename, e)
                errors.append(f"{f.filename}: {e}")
        except Exception as e:
            logger.warning("Failed to ingest %s: %s", f.filename, e)
            errors.append(f"{f.filename}: {e}")

    if total_chunks == 0 and errors:
        raise HTTPException(
            status_code=422,
            detail={"message": "No documents were indexed", "errors": errors},
        )

    return {"message": "Upload processed", "chunks_indexed": total_chunks, "errors": errors}


@router.post("/rag/qa", tags=["RAG"])
async def rag_qa(
    question: str,
    store: Annotated[Optional[KnowledgeStore], Depends(get_knowledge_store)],
    llm: Annotated[Optional[BaseChatModel], Depends(get_optional_llm)],
    top_k: int = 5,
):
    """
    Simple QA over uploaded knowledge with citations.
    If LLM is unavailable, returns concatenated context as answer.
    """
    if not store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge store is not available",
        )
    if not question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty")

    results = store.similarity_search_with_score(question, k=top_k)
    docs = [d for d, _s in results]
    if not docs:
        return {"answer": "", "citations": []}

    context = "\n\n".join([doc.page_content for doc in docs])
    citations = [
        {"source": doc.metadata.get("source"), "chunk_index": doc.metadata.get("chunk_index")}
        for doc in docs
    ]

    if llm:
        try:
            prompt = (
                "Answer the question based only on the following context.\n\n"
                f"{context}\n\nQuestion: {question}\n\n"
                "If the answer cannot be found in the context, say you don't know."
            )
            msg = llm.invoke(prompt)
            content = getattr(msg, "content", str(msg))
            return {"answer": content, "citations": citations}
        except Exception as e:
            logger.warning("LLM invocation failed: %s", e)

    # Fallback: return context snippet
    snippet = context[:500]
    return {"answer": snippet, "citations": citations}
