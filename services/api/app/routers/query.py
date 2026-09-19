from fastapi import APIRouter, Depends, Request, HTTPException
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
import json
import hashlib
import httpx
from ..core.dependencies import get_current_active_user
from ..core.database import get_db
from ..models.models import User, AuditLog
from ml.cache.semantic_cache import semantic_cache
from ml.retrieval.retriever import retriever
from ml.prompts.legal import LEGAL_QA_PROMPT
from ..core.circuit_breaker import ollama_circuit_breaker
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class QueryRequest(BaseModel):
    query: str


async def _embed_query_with_fallback(query: str) -> list[float]:
    """Get embedding for a query string via Ollama with circuit breaker fallback."""
    async def embed_call():
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/embeddings",
                json={"model": settings.EMBEDDING_MODEL, "prompt": query},
            )
            response.raise_for_status()
            return response.json()["embedding"]
    
    result = await ollama_circuit_breaker.call(embed_call)
    if isinstance(result, dict) and "error" in result:
        raise Exception("Embedding service unavailable (circuit breaker open)")
    return result


async def generate_response_with_citations(
    prompt: str,
    tenant_id: str,
    query: str,
    citations: list[dict],
):
    """
    Stream tokens from Ollama with citations in JSON format.
    Yields dicts: {"token": "<text>", "citations": [...]}
    """
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": settings.DEFAULT_MODEL,
                "prompt": prompt,
                "stream": True,
            },
        )
        response.raise_for_status()

        async for line in response.aiter_lines():
            if line:
                data = json.loads(line)
                chunk = data.get("response", "")
                if chunk:
                    yield {"token": chunk, "citations": citations}


@router.post("")
async def execute_query(
    request: QueryRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Execute a legal Q&A query with caching, retrieval, and streaming.
    
    Flow:
    1. Log audit entry (in_progress)
    2. Check semantic cache
    3. If miss: embed query → FAISS retrieve → stream LLM response
    4. Log audit exit (complete/failed) in try/finally
    5. Cache successful responses for future queries
    """
    tenant_id = current_user.tenant_id
    query_hash = hashlib.sha256(request.query.encode()).hexdigest()
    
    # Initialize audit record in in_progress state
    audit = AuditLog(
        tenant_id=tenant_id,
        user_id=current_user.id,
        action="query_start",
        query_hash=query_hash,
    )
    db.add(audit)
    await db.commit()
    audit_id = audit.id

    # ── 1. Semantic Cache check ──────────────────────────────────────
    try:
        cached_res = await semantic_cache.get_cached_response(tenant_id, request.query)
        if cached_res:
            # Update audit: cache hit
            await db.execute(
                text("UPDATE audit_logs SET action = :action WHERE id = :id"),
                {"action": "query_cache_hit", "id": audit_id},
            )
            await db.commit()
            logger.info(f"Query cache hit for tenant {tenant_id}: {query_hash[:8]}")

            async def _cached_stream():
                yield {"data": json.dumps({"token": cached_res, "citations": [], "cached": True})}

            return EventSourceResponse(_cached_stream())

        # ── 2. Embed the query (with circuit breaker) ────────────────
        logger.info(f"Embedding query for tenant {tenant_id}")
        query_emb = await _embed_query_with_fallback(request.query)

        # ── 3. FAISS top-5 retrieval ─────────────────────────────────
        logger.info(f"Retrieving top-5 docs for tenant {tenant_id}")
        retrieved_docs = await retriever.retrieve(tenant_id, query_emb, top_k=5)
        
        if not retrieved_docs:
            logger.warning(f"No documents retrieved for tenant {tenant_id}")
            retrieved_docs = []
        
        doc_ids = [doc.get("doc_id") for doc in retrieved_docs]
        
        # Build citations metadata (doc_id, page, chunk_idx)
        citations = [
            {
                "doc_id": doc.get("doc_id"),
                "page": doc.get("page", doc.get("page_number", 1)),
                "chunk_index": doc.get("chunk_idx", 0),
                "preview": doc.get("text", "")[:120],
            }
            for doc in retrieved_docs
        ]

        # ── 4. Build the legal system prompt with clear source & page headers ──
        context_blocks = []
        for i, doc in enumerate(retrieved_docs):
            p = doc.get("page", doc.get("page_number", 1))
            d_id = doc.get("doc_id", f"Doc-{i+1}")
            context_blocks.append(f"--- [Document: {d_id}, Page: {p}] ---\n{doc.get('text', '')}")
        context = "\n\n".join(context_blocks)
        prompt = LEGAL_QA_PROMPT.format(context=context, question=request.query)

        # ── 5. Update audit with retrieval details ───────────────────
        await db.execute(
            text(
                "UPDATE audit_logs SET action = :action, doc_ids_accessed = :docs "
                "WHERE id = :id"
            ),
            {"action": "query", "docs": json.dumps(doc_ids), "id": audit_id},
        )
        await db.commit()

        # ── 6. Stream response with citations ────────────────────────
        logger.info(f"Streaming response for query {query_hash[:8]}")

        async def get_stream():
            try:
                # generate_response_with_citations is now an async generator itself
                async for chunk_data in generate_response_with_citations(
                    prompt, tenant_id, request.query, citations
                ):
                    yield {"data": json.dumps(chunk_data)}
                
                logger.info(f"Query stream complete for {query_hash[:8]}")
            except Exception as e:
                logger.error(f"Stream error: {e}")
                yield {"data": json.dumps({'error': str(e), 'citations': []})}

        return EventSourceResponse(get_stream())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        # Mark audit as failed
        await db.execute(
            text("UPDATE audit_logs SET action = :action WHERE id = :id"),
            {"action": "query_failed", "id": audit_id},
        )
        await db.commit()
        raise HTTPException(status_code=500, detail=str(e))
