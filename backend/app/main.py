"""FastAPI application entrypoint. Run with:

    uvicorn app.main:app --reload

from the `backend/` directory.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.config import settings
from app.monitoring import init_sentry

# Must run before the FastAPI app is constructed -- sentry_sdk's
# integrations patch on init, so anything created before this point
# (including `app` itself) wouldn't be instrumented.
init_sentry()

app = FastAPI(
    title="TaxEngine.de API",
    version="0.1.0",
    description="Consumer German income tax filing API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
