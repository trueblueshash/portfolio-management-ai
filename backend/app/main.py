import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.middleware.auth import APIKeyMiddleware
from app.api.routes import companies, intelligence, documents, metrics, onepager, comps, youtube

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
)

# Middleware order: last added runs first on incoming requests.
# Add APIKey first (inner), then CORS (outer) so CORS handles preflight and headers before auth.
app.add_middleware(APIKeyMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(companies.router, prefix=settings.API_V1_PREFIX)
app.include_router(intelligence.router, prefix=settings.API_V1_PREFIX)
app.include_router(documents.router, prefix=settings.API_V1_PREFIX)
app.include_router(metrics.router, prefix=settings.API_V1_PREFIX)
app.include_router(onepager.router, prefix=settings.API_V1_PREFIX)
app.include_router(comps.router, prefix=settings.API_V1_PREFIX)
app.include_router(youtube.router, prefix=settings.API_V1_PREFIX)


@app.get("/")
def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}

