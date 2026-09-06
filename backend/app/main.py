from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.db import engine

# import all models so SQLAlchemy registers them before create_all
from app.models.scan import Base, Scan  # noqa: F401
from app.models.scan_image import ScanImage  # noqa: F401
from app.models.field import ExtractedField  # noqa: F401
from app.models.violation import Violation  # noqa: F401
from app.models.report import Report  # noqa: F401
from app.models.pair_token import PairToken  # noqa: F401
from app.models.object_store import StoredObject  # noqa: F401

from app.api.routes.scan import router as scan_router
from app.api.routes.pair import router as pair_router
from app.api.routes.dashboard import router as dashboard_router

setup_logging()

app = FastAPI(
    title="SIH26034 Legal Metrology Compliance API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_version="3.0.2",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.CORS_ORIGINS == "*" else settings.CORS_ORIGINS.split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health", tags=["health"])
def health():
    return {"ok": True, "service": "lm-api", "version": "0.1.0"}


app.include_router(scan_router)
app.include_router(pair_router)
app.include_router(dashboard_router)
