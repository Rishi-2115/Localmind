from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..core.dependencies import get_current_active_user, get_current_active_admin
from ..core.database import get_db
from ..models.models import User, AuditLog

router = APIRouter()

@router.get("/")
async def get_audit_logs(
    current_admin: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db)
):
    # Only admins can view the full audit log
    result = await db.execute(
        select(AuditLog).where(AuditLog.tenant_id == current_admin.tenant_id).order_by(AuditLog.timestamp.desc())
    )
    logs = result.scalars().all()
    return {
        "logs": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action,
                "timestamp": log.timestamp,
                "doc_ids_accessed": log.doc_ids_accessed,
                "query_hash": log.query_hash
            } for log in logs
        ]
    }
