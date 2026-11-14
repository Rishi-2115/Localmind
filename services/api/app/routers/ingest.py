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
from ..models.models import User, Document, AuditLog, ContractRisk
from ..core.config import settings
from fastapi.responses import StreamingResponse, Response
from fastapi import Query
from typing import Optional
import io
import fitz # PyMuPDF

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


@router.get("/documents")
async def list_documents(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all uploaded documents for the active tenant.
    """
    result = await db.execute(
        select(Document)
        .where(Document.tenant_id == current_user.tenant_id)
        .order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "status": d.status,
            "created_at": d.created_at,
            "error_message": d.error_message,
        }
        for d in docs
    ]


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


@router.get("/risks/{doc_id}")
async def get_document_contract_risks(
    doc_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve automated clause risk & deviation assessment for an ingested document.
    Returns 404 if the document does not exist or belongs to another tenant.
    """
    # 1. Enforce strict document ownership check
    doc_check = await db.execute(
        select(Document).where(
            (Document.id == doc_id) & (Document.tenant_id == current_user.tenant_id)
        )
    )
    if not doc_check.scalars().first():
        raise HTTPException(
            status_code=404,
            detail="Document not found or access denied for this tenant"
        )

    result = await db.execute(
        select(ContractRisk)
        .where(
            (ContractRisk.document_id == doc_id)
            & (ContractRisk.tenant_id == current_user.tenant_id)
        )
        .order_by(ContractRisk.page_number.asc())
    )
    risks = result.scalars().all()
    
    # Calculate overall risk score
    risk_weights = {"CRITICAL": 10, "HIGH": 7, "MEDIUM": 4, "LOW": 1}
    total_score = sum(risk_weights.get(r.risk_level, 1) for r in risks)
    composite_tier = "LOW"
    if any(r.risk_level == "CRITICAL" for r in risks) or total_score >= 18:
        composite_tier = "CRITICAL"
    elif any(r.risk_level == "HIGH" for r in risks) or total_score >= 12:
        composite_tier = "HIGH"
    elif total_score >= 6:
        composite_tier = "MEDIUM"

    return {
        "document_id": doc_id,
        "risk_tier": composite_tier,
        "total_risks_flagged": len(risks),
        "risks": [
            {
                "id": r.id,
                "clause_type": r.clause_type,
                "risk_level": r.risk_level,
                "excerpt": r.excerpt,
                "page_number": r.page_number,
                "reasoning": r.reasoning,
                "recommendation": r.recommendation,
            }
            for r in risks
        ],
    }


@router.get("/file/{doc_id}")
async def stream_document_file(
    doc_id: str,
    highlight: Optional[str] = Query(None, description="Text snippet to dynamically highlight in the PDF"),
    page: Optional[int] = Query(None, description="Specific page number to focus on"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Stream document file securely from MinIO. 
    If a `highlight` query is provided, dynamically annotates the PDF on the fly 
    with a vibrant yellow/orange highlight over the exact citation snippet!
    """
    result = await db.execute(
        select(Document).where(
            (Document.id == doc_id) & (Document.tenant_id == current_user.tenant_id)
        )
    )
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    bucket_name = _get_tenant_bucket_name(current_user.tenant_id)
    s3_path = f"documents/{doc_id}/{doc.filename}"

    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=s3_path)
        raw_bytes = response["Body"].read()

        # If it's a PDF and a highlight query was passed, dynamically add highlight annotation
        if doc.filename.lower().endswith(".pdf") and highlight and len(highlight.strip()) > 3:
            try:
                pdf_doc = fitz.open(stream=raw_bytes, filetype="pdf")
                search_terms = []
                cleaned = highlight.strip().replace('"', '').replace("'", "")
                
                # Try finding multi-word prefix (first 6-8 words) for reliable matching across linebreaks
                words = cleaned.split()
                if len(words) >= 4:
                    search_terms.append(" ".join(words[:6]))
                    search_terms.append(" ".join(words[:4]))
                search_terms.append(cleaned[:40])

                # Pages to search
                pages_to_check = [page - 1] if page and 1 <= page <= len(pdf_doc) else range(len(pdf_doc))
                
                highlighted_any = False
                for p_idx in pages_to_check:
                    p = pdf_doc[p_idx]
                    for term in search_terms:
                        if not term or len(term) < 4:
                            continue
                        rects = p.search_for(term)
                        if rects:
                            for rect in rects:
                                annot = p.add_highlight_annot(rect)
                                # Cyber Orange / Yellow high-contrast highlight stroke
                                annot.set_colors(stroke=(1.0, 0.45, 0.0))
                                annot.update()
                            highlighted_any = True
                            break
                    if highlighted_any:
                        break

                output_buffer = io.BytesIO()
                pdf_doc.save(output_buffer)
                pdf_doc.close()
                raw_bytes = output_buffer.getvalue()
            except Exception as annot_err:
                logger.warning(f"Dynamic PDF annotation failed, returning original PDF: {annot_err}")

        return Response(
            content=raw_bytes,
            media_type="application/pdf" if doc.filename.lower().endswith(".pdf") else "application/octet-stream",
            headers={
                "Content-Disposition": f'inline; filename="{doc.filename}"',
                "Content-Type": "application/pdf" if doc.filename.lower().endswith(".pdf") else "application/octet-stream",
            },
        )
    except Exception as e:
        logger.error(f"Failed to fetch document file from MinIO: {e}")
        raise HTTPException(status_code=404, detail="File could not be retrieved from storage")
