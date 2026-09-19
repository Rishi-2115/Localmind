from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import query, ingest, admin, audit, auth
from .core.config import settings
from .core.startup import init_db, seed_admin
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run once on startup: create tables + seed admin user."""
    logger.info("Starting LocalMind API — initialising database…")
    await init_db()
    await seed_admin()
    logger.info("LocalMind API ready.")
    yield
    logger.info("Shutting down LocalMind API.")


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(query.router, prefix=f"{settings.API_V1_STR}/query", tags=["query"])
app.include_router(ingest.router, prefix=f"{settings.API_V1_STR}/ingest", tags=["ingest"])
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["admin"])
app.include_router(audit.router, prefix=f"{settings.API_V1_STR}/audit", tags=["audit"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}
