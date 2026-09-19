"""
Startup lifecycle hooks for FastAPI — auto-creates tables and seeds the default
admin user on first boot so the system is immediately usable after
`docker-compose up`.
"""
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database import engine, AsyncSessionLocal
from ..models.models import Base, User
from ..core.security import get_password_hash
from ..core.config import settings

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Create all tables if they don't exist yet (replaces Alembic for dev)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Ensure must_change_password column exists if table was created previously
        try:
            await conn.execute(
                text("ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN DEFAULT TRUE")
            )
        except Exception:
            pass
    logger.info("Database tables verified / created.")


async def seed_admin() -> None:
    """Insert the default admin user for the pilot tenant if it doesn't exist."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": settings.DEFAULT_ADMIN_EMAIL},
        )
        existing = result.scalars().first()
        if existing:
            logger.info(f"Admin user {settings.DEFAULT_ADMIN_EMAIL} already exists — skipping seed.")
            return

        admin = User(
            tenant_id=settings.DEFAULT_TENANT_ID,
            email=settings.DEFAULT_ADMIN_EMAIL,
            hashed_password=get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
            role="admin",
            must_change_password=True,
        )
        session.add(admin)
        await session.commit()
        logger.info(
            f"Seeded admin user: {settings.DEFAULT_ADMIN_EMAIL} "
            f"(tenant: {settings.DEFAULT_TENANT_ID})"
        )
