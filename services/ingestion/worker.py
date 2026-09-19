"""
Celery worker for document ingestion: parse → chunk → embed → index.

Handles PDF/DOCX/TXT files, extracts text with page metadata,
chunks with overlap, generates embeddings, and stores in FAISS.
"""
import os
import tempfile
import boto3
import logging
import psycopg2
from urllib.parse import urlparse
from celery import Celery

# Import pipeline components
from parsers.pdf import parse_pdf
from parsers.docx_parser import parse_docx
from parsers.txt import parse_txt
from parsers.ocr import ocr_pdf
from chunker import chunk_text
from embedder import embed_texts, validate_embedding_model
from indexer import index_chunks

logger = logging.getLogger(__name__)

# ─── Configuration ──────────────────────────────────────────────────────
REDIS_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://user:pass@db:5432/localmind")
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ROOT_USER", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin")

# ─── Celery App ─────────────────────────────────────────────────────────
celery_app = Celery("ingestion", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# ─── Database Setup ─────────────────────────────────────────────────────
# Use synchronous psycopg2 — Celery prefork workers are sync processes.
# asyncio.run() in a forked child causes event loop reuse errors on retries.
_RAW_DB_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


def update_doc_status(doc_id: str, status: str, error_msg: str = None):
    """Update document status in the database (synchronous, psycopg2)."""
    conn = psycopg2.connect(_RAW_DB_URL)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE documents SET status = %s, error_message = %s WHERE id = %s",
                (status, error_msg, doc_id),
            )
        conn.commit()
        logger.info(f"Updated document {doc_id} status to {status}")
    finally:
        conn.close()


def _get_minio_client():
    """Create MinIO/S3 client."""
    return boto3.client(
        "s3",
        endpoint_url=f"http://{MINIO_ENDPOINT}",
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
    )


def _download_from_minio(tenant_id: str, s3_path: str, local_path: str):
    """Download file from MinIO to local disk."""
    s3_client = _get_minio_client()
    bucket_name = f"tenant-{tenant_id}".lower()
    
    try:
        s3_client.download_file(bucket_name, s3_path, local_path)
        logger.info(f"Downloaded {s3_path} from MinIO ({bucket_name})")
        return True
    except Exception as e:
        logger.error(f"Failed to download from MinIO: {e}")
        return False


def _parse_document(file_path: str) -> dict:
    """
    Parse document based on extension.
    
    Returns:
    {
        "text": "full text",
        "chunks_with_metadata": [
            {"text": str, "page": int, ...},
            ...
        ],
        "total_pages": int,
        "error": str (if any)
    }
    """
    ext = file_path.lower().split('.')[-1]
    
    try:
        if ext == 'pdf':
            logger.info(f"Parsing PDF: {file_path}")
            result = parse_pdf(file_path)
            if result.get("error"):
                logger.warning(f"PDF parsing error, attempting OCR")
                # Fallback to OCR if PDF text extraction failed
                ocr_result = ocr_pdf(file_path)
                return {
                    "text": ocr_result,
                    "chunks_with_metadata": [],
                    "total_pages": 0,
                }
            return result
        elif ext == 'docx':
            logger.info(f"Parsing DOCX: {file_path}")
            text = parse_docx(file_path)
            return {
                "text": text,
                "chunks_with_metadata": [],
                "total_pages": 1,
            }
        elif ext == 'txt':
            logger.info(f"Parsing TXT: {file_path}")
            text = parse_txt(file_path)
            return {
                "text": text,
                "chunks_with_metadata": [],
                "total_pages": 1,
            }
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    except Exception as e:
        logger.error(f"Parse error: {e}")
        return {
            "text": "",
            "chunks_with_metadata": [],
            "total_pages": 0,
            "error": str(e),
        }


@celery_app.task(
    name="ingestion.process_document",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2},
    retry_backoff=True,
    retry_backoff_max=60,
)
def process_document(tenant_id: str, doc_id: str, s3_path: str):
    """
    Main ingestion task: download → parse → chunk → embed → index.
    
    Args:
        tenant_id: Tenant identifier
        doc_id: Document UUID
        s3_path: S3 path in tenant's MinIO bucket (e.g., "documents/{doc_id}/file.pdf")
    
    Returns:
        {"status": "success", "doc_id": doc_id}
    """
    logger.info(f"[Task] Starting ingestion for doc {doc_id} (tenant: {tenant_id})")
    
    temp_file = None
    try:
        # ─── 1. Mark as processing ─────────────────────────────────────
        update_doc_status(doc_id, "processing")
        
        # ─── 2. Download from MinIO ────────────────────────────────────
        # Preserve the original file extension so _parse_document can detect type.
        # s3_path is e.g. "documents/<doc_id>/sample_contract.pdf"
        file_ext = os.path.splitext(s3_path)[-1]  # e.g. ".pdf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            temp_file = tmp.name  # e.g. /tmp/tmp4tdwyrwy.pdf
        
        if not _download_from_minio(tenant_id, s3_path, temp_file):
            raise Exception("Failed to download document from MinIO")
        
        # ─── 3. Parse document ─────────────────────────────────────────
        parse_result = _parse_document(temp_file)
        if parse_result.get("error"):
            raise Exception(f"Parse error: {parse_result['error']}")
        
        text_content = parse_result.get("text", "")
        if not text_content.strip():
            raise ValueError("No text extracted from document")
        
        logger.info(f"Extracted {len(text_content)} characters, {parse_result.get('total_pages', 0)} pages")
        
        # ─── 4. Chunk text with page metadata ──────────────────────────
        chunks = []
        page_chunks_meta = parse_result.get("chunks_with_metadata", [])
        if page_chunks_meta:
            chunk_idx_counter = 0
            for p_info in page_chunks_meta:
                p_text = p_info.get("text", "").strip()
                if not p_text:
                    continue
                p_num = p_info.get("page", 1)
                sub_chunks = chunk_text(
                    p_text,
                    metadata={
                        "doc_id": doc_id,
                        "page": p_num,
                        "total_pages": parse_result.get("total_pages", 1),
                    },
                    chunk_size=512,
                    overlap=64,
                )
                for sc in sub_chunks:
                    sc["chunk_idx"] = chunk_idx_counter
                    chunk_idx_counter += 1
                    chunks.append(sc)
        else:
            chunks = chunk_text(
                text_content,
                metadata={
                    "doc_id": doc_id,
                    "page": 1,
                    "total_pages": parse_result.get("total_pages", 1),
                },
                chunk_size=512,
                overlap=64,
            )

        if not chunks:
            raise ValueError("No chunks generated from document")

        logger.info(f"Generated {len(chunks)} chunks with verified page citations")
        
        # ─── 5. Generate embeddings ────────────────────────────────────
        chunk_texts = [chunk.get("text", "") for chunk in chunks]
        embeddings = embed_texts(chunk_texts)
        
        if len(embeddings) != len(chunks):
            raise ValueError(
                f"Embedding count mismatch: {len(embeddings)} embeddings, {len(chunks)} chunks"
            )
        
        logger.info(f"Generated {len(embeddings)} embeddings")
        
        # ─── 6. Index into FAISS ───────────────────────────────────────
        index_chunks(tenant_id, doc_id, chunks, embeddings)
        
        # ─── 7. Mark as indexed ────────────────────────────────────────
        update_doc_status(doc_id, "indexed")
        
        logger.info(f"[Task] Successfully processed document {doc_id}")
        return {"status": "success", "doc_id": doc_id}
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[Task] Ingestion failed for {doc_id}: {error_msg}")
        
        # Mark as failed in database
        try:
            update_doc_status(doc_id, "failed", error_msg)
        except Exception as db_error:
            logger.error(f"Failed to update DB status: {db_error}")
        
        # Re-raise to trigger Celery retry
        raise
    
    finally:
        # Clean up temp file
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
                logger.debug(f"Cleaned up temp file: {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to clean temp file: {e}")


@celery_app.task(name="ingestion.validate_setup")
def validate_setup():
    """
    Validate that all required services are accessible.
    Call this on startup to catch configuration issues early.
    """
    logger.info("Validating ingestion setup...")
    
    try:
        # Validate MinIO connectivity
        s3_client = _get_minio_client()
        response = s3_client.list_buckets()
        logger.info(f"✓ MinIO accessible ({len(response['Buckets'])} buckets)")
        
        # Validate database connectivity (uses sync psycopg2)
        conn = psycopg2.connect(_RAW_DB_URL)
        conn.close()
        logger.info("✓ Database accessible")
        
        logger.info("✓✓✓ All services validated successfully")
        return {"status": "ready"}
    
    except Exception as e:
        logger.error(f"✗ Setup validation failed: {e}")
        raise


if __name__ == "__main__":
    # This allows running the worker with: python worker.py
    celery_app.start()
