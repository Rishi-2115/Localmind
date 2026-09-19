"""
Ingestion router: upload legal documents, store in MinIO, enqueue async processing.

Flow:
1. Validate file (size, type)
2. Upload to tenant MinIO bucket
3. Create Document record with MinIO path
4. Enqueue Celery task with retry config
5. Audit log the upload
6. Return task ID for polling
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid
import boto3
import logging

from ..core.dependencies import get_current_active_user
from ..core.database import get_db
from ..models.models import User, Document, AuditLog
from ..core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize MinIO client
s3_client = boto3.client(
    "s3",
    endpoint_url=f"http://{settings.MINIO_ENDPOINT}",
    aws_access_key_id=settings.MINIO_ACCESS_KEY,
    aws_secret_access_key=settings.MINIO_SECRET_KEY,
)

# Initialize Celery app for task enqueueing
from celery import Celery
celery_app = Celery("ingestion", broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND)

# NOTE: retry config lives on the worker-side @task decorator, not on send_task.
# send_task only accepts serializable kwargs; passing Python type objects causes
# "Object of type type is not JSON serializable" errors.

# Allowed file types
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".doc"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def _get_tenant_bucket_name(tenant_id: str) -> str:
    """Get MinIO bucket name for a tenant."""
    return f"tenant-{tenant_id}".lower()


from botocore.exceptions import ClientError

def _ensure_bucket_exists(tenant_id: str) -> None:
    """Create MinIO bucket for tenant if it doesn't exist."""
    bucket_name = _get_tenant_bucket_name(tenant_id)
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        logger.info(f"Bucket {bucket_name} already exists")
    except (ClientError, Exception) as e:
        logger.info(f"Bucket {bucket_name} not found or head error ({e}) — creating bucket...")
        try:
            s3_client.create_bucket(Bucket=bucket_name)
            logger.info(f"Created bucket {bucket_name}")
        except Exception as create_err:
            logger.error(f"Failed to create bucket {bucket_name}: {create_err}")
            raise


async def _validate_upload_file(file: UploadFile) -> None:
    """Validate file extension and size."""
    # Check extension
    file_ext = "." + file.filename.split(".")[-1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_ext} not allowed. Allowed: {ALLOWED_EXTENSIONS}",
        )
    
    # Check size
    file_size = 0
    while True:
        chunk = await file.read(1024 * 1024)  # 1 MB chunks
        if not chunk:
            break
        file_size += len(chunk)
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Max size: {MAX_FILE_SIZE / (1024*1024):.0f} MB",
            )
    
    # Reset file pointer for re-reading
    await file.seek(0)


async def _upload_to_minio(tenant_id: str, doc_id: str, file: UploadFile) -> str:
    """Upload file to MinIO and return the S3 path."""
    bucket_name = _get_tenant_bucket_name(tenant_id)
    object_key = f"documents/{doc_id}/{file.filename}"
    
    # Ensure bucket exists
    _ensure_bucket_exists(tenant_id)
    
    # Read file content
    file_content = await file.read()
    
    # Upload to MinIO
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=file_content,
            ContentType=file.content_type or "application/octet-stream",
        )
        logger.info(f"Uploaded {file.filename} to s3://{bucket_name}/{object_key}")
        return object_key
    except Exception as e:
        logger.error(f"Failed to upload to MinIO: {e}")
        raise HTTPException(status_code=500, detail="Failed to store document")


@router.post("/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload legal documents for processing.
    
    Returns:
    {
        "tasks": [
            {"doc_id": "<uuid>", "filename": "...", "task_id": "<celery_id>"}
        ]
    }
    """
    tenant_id = current_user.tenant_id
    task_records = []
    doc_ids = []

    for file in files:
        try:
            # 1. Validate file
            await _validate_upload_file(file)
            
            # 2. Upload to MinIO
            doc_id = str(uuid.uuid4())
            s3_path = await _upload_to_minio(tenant_id, doc_id, file)
            
            # 3. Create Document record
            doc = Document(
                id=doc_id,
                tenant_id=tenant_id,
                filename=file.filename,
                status="queued",  # queued → processing → indexed or failed
                uploaded_by=current_user.id,
            )
            db.add(doc)
            await db.flush()  # Get the ID back
            
            # 4. Enqueue Celery task (retry config lives on the worker @task decorator)
            task = celery_app.send_task(
                "ingestion.process_document",
                args=[tenant_id, doc_id, s3_path],
            )
            
            task_records.append({
                "doc_id": doc_id,
                "filename": file.filename,
                "task_id": task.id,
            })
            doc_ids.append(doc_id)
            
            logger.info(f"Enqueued ingestion task {task.id} for doc {doc_id}")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing upload {file.filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to process {file.filename}")
    
    # 5. Audit log
    audit = AuditLog(
        tenant_id=tenant_id,
        user_id=current_user.id,
        action="ingest_upload",
        doc_ids_accessed=doc_ids,
    )
    db.add(audit)
    
    await db.commit()
    
    return {
        "message": f"Successfully queued {len(task_records)} document(s) for processing",
        "tasks": task_records,
    }


@router.get("/status/{doc_id}")
async def get_document_status(
    doc_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the processing status of a document.
    
    Returns:
    {
        "doc_id": "<uuid>",
        "filename": "...",
        "status": "queued|processing|indexed|failed",
        "error_message": null or error text,
        "task_id": "<celery_id>" if available
    }
    """
    # Fetch document
    result = await db.execute(
        select(Document).where(
            (Document.id == doc_id) & (Document.tenant_id == current_user.tenant_id)
        )
    )
    doc = result.scalars().first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {
        "doc_id": doc.id,
        "filename": doc.filename,
        "status": doc.status,
        "error_message": doc.error_message,
        "created_at": doc.created_at,
    }


@router.post("/retry/{doc_id}")
async def retry_failed_document(
    doc_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually retry a failed document ingestion.
    (Only admins can retry other users' documents)
    """
    # Fetch document
    result = await db.execute(
        select(Document).where(
            (Document.id == doc_id) & (Document.tenant_id == current_user.tenant_id)
        )
    )
    doc = result.scalars().first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if doc.status != "failed":
        raise HTTPException(status_code=400, detail="Only failed documents can be retried")
    
    # Reconstruct MinIO path from doc metadata (stored as s3_path in DB)
    # For now, we'll need to modify the Document model to store this
    # As a workaround, reconstruct from tenant_id and doc_id
    bucket_name = _get_tenant_bucket_name(current_user.tenant_id)
    s3_path = f"documents/{doc_id}/{doc.filename}"
    
    # Re-enqueue the task
    task = celery_app.send_task(
        "ingestion.process_document",
        args=[current_user.tenant_id, doc_id, s3_path],
    )
    
    # Update document status back to queued
    doc.status = "queued"
    doc.error_message = None
    await db.commit()
    
    logger.info(f"Retrying document {doc_id}, new task ID: {task.id}")
    
    return {
        "message": "Document queued for reprocessing",
        "doc_id": doc_id,
        "task_id": task.id,
    }
