"""FastAPI app factory (HO-3): CORS for the local frontend, lifespan SQLite init, typed error mapping.

Run from ``backend/``:  ``uvicorn app.main:app --host 127.0.0.1 --port 8000``
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.routes import SavedResultInvalidatedError, SavedResultNotFoundError, router
from .clients.cancerinfo_client import CancerInfoAPIClient, CancerInfoAPIError
from .config import ConfigurationError, Settings, get_settings
from .db.operational_store import BudgetExceededError, OperationalStore
from .investigator.common import ExtractionNotConfirmedError, PipelineStateError, ServiceContainer
from .investigator.hooks import CapabilityNotReadyError
from .providers.baseten_client import BasetenClaimVerifierClient
from .providers.governance import LiveCallsDisabledError, ProviderError
from .providers.json_utils import IncompleteGenerationError, ModelOutputValidationError
from .providers.meta_client import MetaMuseClient
from .schemas.envelope import ErrorResponse

logger = logging.getLogger("cancerlens")

API_VERSION = "1.0.0-stage2"

# (exception type, HTTP status, error_code). Messages are generic and never echo secrets or model content.
_ERROR_MAP: tuple[tuple[type[Exception], int, str], ...] = (
    (ExtractionNotConfirmedError, 422, "EXTRACTION_NOT_CONFIRMED"),
    (BudgetExceededError, 429, "BUDGET_CIRCUIT_OPEN"),
    (LiveCallsDisabledError, 503, "LIVE_LLM_CALLS_DISABLED"),
    (ConfigurationError, 503, "PROVIDER_NOT_CONFIGURED"),
    (CancerInfoAPIError, 503, "CANCER_INFO_API_UNAVAILABLE"),
    (ProviderError, 502, "PROVIDER_UNAVAILABLE"),
    (IncompleteGenerationError, 502, "MODEL_OUTPUT_INCOMPLETE"),
    (ModelOutputValidationError, 502, "MODEL_OUTPUT_REJECTED"),
    (PipelineStateError, 500, "PIPELINE_STATE_ERROR"),
    (CapabilityNotReadyError, 501, "CAPABILITY_NOT_AVAILABLE"),
    (SavedResultNotFoundError, 404, "NOT_FOUND"),
    (SavedResultInvalidatedError, 410, "SAVED_RESULT_INVALIDATED"),
)


def build_container(settings: Settings) -> ServiceContainer:
    store = OperationalStore(settings.resolved_db_path())
    store.initialize()
    return ServiceContainer(
        settings=settings,
        store=store,
        cancer_info=CancerInfoAPIClient(settings),
        meta=MetaMuseClient(settings, store),
        baseten=BasetenClaimVerifierClient(settings, store),
    )


async def close_container(c: ServiceContainer) -> None:
    for client in (c.cancer_info, c.meta, c.baseten):
        await client.aclose()
    c.store.close()


def _register_error_handlers(app: FastAPI) -> None:
    for exc_type, status_code, error_code in _ERROR_MAP:
        def handler(request: Request, exc: Exception, _status=status_code, _code=error_code) -> JSONResponse:
            if _status >= 500:
                logger.warning("%s on %s: %s", _code, request.url.path, type(exc).__name__)
            body = ErrorResponse(error_code=_code, message=str(exc)[:300])
            return JSONResponse(status_code=_status, content=body.model_dump())

        app.add_exception_handler(exc_type, handler)

    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=422, content=ErrorResponse(error_code="INVALID_REQUEST", message=str(exc)[:300]).model_dump())

    app.add_exception_handler(ValueError, value_error_handler)


def create_app(settings: Settings | None = None, container: ServiceContainer | None = None) -> FastAPI:
    """``container`` lets tests inject clients built on mocked transports. Production builds its own."""
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        owned = container is None
        app.state.container = container or build_container(settings)
        try:
            yield
        finally:
            if owned:
                await close_container(app.state.container)

    app = FastAPI(
        title="CancerLens API",
        version=API_VERSION,
        description=(
            "CancerLens backend (Track 1, Stage 2). Learn Lens (Meta Model API muse-spark-1.3) and Evaluate Lens "
            "(Baseten meta-models/muse-spark-open-1026) over the live Cancer Info API. Educational information only; "
            "not medical advice."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Capability-Token"],
    )
    _register_error_handlers(app)
    app.include_router(router)
    return app


app = create_app()
