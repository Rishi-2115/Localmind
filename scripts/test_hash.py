import asyncio
from sqlalchemy import select
import sys
import os

# add parent dir so we can import app
sys.path.append(os.path.join(os.path.dirname(__file__), "../services/api"))

from app.core.database import AsyncSessionLocal
from app.models.models import User
from app.core.security import verify_password

async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == 'admin@localmind.in'))
        user = result.scalars().first()
        print('User:', user.email if user else None)
        print('Hash:', user.hashed_password if user else None)
        print('Verify:', verify_password('localmind_admin_2027', user.hashed_password) if user else False)

asyncio.run(main())
