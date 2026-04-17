from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.integrations.stripe_client import configure_stripe
from app.middleware.rate_limit import RateLimitMiddleware
from app.models.schemas import HealthResponse

logger = logging.getLogger("picvibez")

APP_VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    logger.info("Starting PicVibez API v%s [%s]", APP_VERSION, settings.APP_ENV)

    configure_stripe()

    yield

    logger.info("Shutting down PicVibez API")


app = FastAPI(
    title="PicVibez API",
    version=APP_VERSION,
    docs_url="/docs" if not get_settings().is_production else None,
    redoc_url="/redoc" if not get_settings().is_production else None,
    lifespan=lifespan,
)

# ── Middleware (applied bottom-to-top) ──

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware, max_requests=200, window_seconds=60)


# ── Exception handlers ──


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field = " -> ".join(str(loc) for loc in err["loc"])
        errors.append({"field": field, "message": err["msg"]})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": errors},
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# ── Routes ──


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check():
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        version=APP_VERSION,
        environment=settings.APP_ENV,
    )


app.include_router(api_router, prefix="/api/v1")
