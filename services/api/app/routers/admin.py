from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..core.dependencies import get_current_active_admin
from ..core.database import get_db
from ..models.models import User, Document

router = APIRouter()

@router.get("/users")
async def list_users(
    current_admin: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.tenant_id == current_admin.tenant_id))
    users = result.scalars().all()
    return {"users": [{"id": u.id, "email": u.email, "role": u.role} for u in users]}

@router.get("/documents")
async def list_documents(
    current_admin: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Document).where(Document.tenant_id == current_admin.tenant_id))
    docs = result.scalars().all()
    return {"documents": [{"id": d.id, "filename": d.filename, "status": d.status} for d in docs]}
