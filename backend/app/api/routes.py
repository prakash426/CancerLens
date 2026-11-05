"""HO-3: all ``/api/v1/*`` endpoints consumed by the frontend.

The frontend never calls Meta, Baseten or Cancer Info API directly; it only renders what
these routes return. Typed errors are converted to ``ErrorResponse`` in ``main.py``.
"""

from __future__ import annotations

import base64
from html.parser import HTMLParser
from urllib.parse import urljoin

import httpx
from fastapi import APIRouter, File, Header, Query, Request, Response, UploadFile, status

from ..clients.cancerinfo_client import CancerInfoAPIError
from ..config import create_verified_ssl_context
from ..db.operational_store import parse_ts
from ..guards.ssrf_url_guard import Resolver
from ..investigator import (
    ServiceContainer,
    run_consistency_double_check,
    run_evaluate_investigator,
    run_learn_coverage,
    run_learn_pipeline,
)
from ..investigator.common import apply_link_verdicts, new_request_id
from ..investigator.hooks import (
    CapabilityNotReadyError,
    guard_image_upload,
    guard_public_url,
    run_stage4_verifier,
    sanitize_pii,
)
from ..providers.json_utils import ModelOutputValidationError
from ..schemas.enums import InputModality, PipelineState, RetrievalState
from ..schemas.envelope import (
    BudgetHealthResponse,
    CancerCatalogResponse,
    ConsistencyDoubleCheckRequest,
    ConsistencyDoubleCheckResult,
    ErrorResponse,
    EvaluateRequest,
    ExtractionResponse,
    LearnCoverageResponse,
    LearnRequest,
    ProviderPoolStatus,
    ResultEnvelope,
    SavedResultCreatedResponse,
    SavedResultCreateRequest,
    SavedResultView,
    UrlExtractionRequest,
)

router = APIRouter(prefix="/api/v1")

MAX_IMAGE_BYTES = 5 * 1024 * 1024

_ERRORS = {
    422: {"model": ErrorResponse, "description": "Validation or confirmation error"},
    429: {"model": ErrorResponse, "description": "Budget circuit breaker open"},
    502: {"model": ErrorResponse, "description": "Provider failed or model output rejected"},
    503: {"model": ErrorResponse, "description": "Provider disabled / not configured, or Cancer Info API unavailable"},
}


class SavedResultNotFoundError(LookupError):
    pass


class SavedResultInvalidatedError(RuntimeError):
    """A cited source was withdrawn from Cancer Info API, so the snapshot is no longer valid."""


def container(request: Request) -> ServiceContainer:
    return request.app.state.container


# ---------------------------------------------------------------------------- catalog
@router.get("/cancers", response_model=CancerCatalogResponse, tags=["catalog"])
async def list_cancers(request: Request) -> CancerCatalogResponse:
    try:
        cancers = await container(request).cancer_info.list_cancers()
    except CancerInfoAPIError:
        return CancerCatalogResponse(retrieval_state=RetrievalState.TOOL_FAILED, cancers=[])
    state = RetrievalState.SEARCH_EXECUTED_WITH_MATCHES if cancers else RetrievalState.SEARCH_EXECUTED_NO_MATCHES
    return CancerCatalogResponse(retrieval_state=state, cancers=cancers)


# ---------------------------------------------------------------------------- lenses
@router.post("/learn", response_model=ResultEnvelope, responses=_ERRORS, tags=["learn"])
async def learn(body: LearnRequest, request: Request) -> ResultEnvelope:
    return await run_learn_pipeline(body, container(request))


_MAX_COVERAGE_SLUGS = 25


@router.get("/learn/coverage", response_model=LearnCoverageResponse, responses=_ERRORS, tags=["learn"])
async def learn_coverage(
    request: Request,
    cancer_id: str = Query(default="general-oncology", min_length=1, max_length=120),
    subtype_id: str | None = Query(default=None, max_length=120),
    category_slug: list[str] = Query(default=[]),
) -> LearnCoverageResponse:
    """Per-category data availability for one cancer (retrieval only, $0.00).

    The frontend probes its own category list on cancer select and hides
    ``has_data=False`` slugs, so judges never click a dead button. A probe
    uses the exact retrieval a real ``/learn`` click runs, so coverage always
    predicts what the click would show.
    """
    slugs = list(dict.fromkeys(s.strip() for s in category_slug if s and s.strip()))
    if not slugs:
        raise ValueError("At least one category_slug query value is required.")
    if len(slugs) > _MAX_COVERAGE_SLUGS:
        raise ValueError(f"At most {_MAX_COVERAGE_SLUGS} category_slug values per call.")
    return await run_learn_coverage(container(request), cancer_id.strip() or "general-oncology", subtype_id, slugs)


@router.post("/evaluate", response_model=ResultEnvelope, responses=_ERRORS, tags=["evaluate"])
async def evaluate(body: EvaluateRequest, request: Request) -> ResultEnvelope:
    return await run_evaluate_investigator(body, container(request))


@router.post("/evaluate/double-check", response_model=ConsistencyDoubleCheckResult, responses=_ERRORS, tags=["evaluate"])
async def evaluate_double_check(body: ConsistencyDoubleCheckRequest, request: Request) -> ConsistencyDoubleCheckResult:
    return await run_consistency_double_check(body, container(request))


# ---------------------------------------------------------------------------- extraction (Stage 2)
_EXTRACT_ERRORS = {**_ERRORS, 501: {"model": ErrorResponse, "description": "Capability not available yet"}}

_MAX_REDIRECTS = 3
_URL_FETCH_TIMEOUT_SECONDS = 10.0
_URL_FETCH_MAX_BYTES = 1024 * 1024
_URL_EXTRACT_MAX_CHARS = 3000


class _TextExtractor(HTMLParser):
    """Collect visible text, skipping script/style/nav/footer/noscript subtrees."""

    _SKIP_TAGS = frozenset({"script", "style", "nav", "footer", "noscript"})
    _BLOCK_TAGS = frozenset(
        {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "title"}
    )

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1
        elif tag in self._BLOCK_TAGS and self._skip_depth == 0:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._parts.append(data)

    def text(self) -> str:
        return " ".join("".join(self._parts).split())


def _html_to_text(raw_html: str) -> str:
    extractor = _TextExtractor()
    try:
        extractor.feed(raw_html)
        extractor.close()
    except Exception:
        pass  # HTMLParser is lenient; keep whatever was collected before the error
    return extractor.text()


def _is_textual_content(content_type: str) -> bool:
    subtype = content_type.split(";")[0].strip().lower()
    return subtype.startswith("text/") or "html" in subtype or subtype.endswith("xml") or subtype == "application/json"


async def fetch_guarded_url_text(
    url: str,
    *,
    resolver: Resolver | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
    max_redirects: int = _MAX_REDIRECTS,
    timeout_seconds: float = _URL_FETCH_TIMEOUT_SECONDS,
    max_bytes: int = _URL_FETCH_MAX_BYTES,
    max_chars: int = _URL_EXTRACT_MAX_CHARS,
) -> str:
    """SSRF-guarded fetch plus readable-text extraction. Raises ``ValueError`` (-> 422).

    Every URL, including each redirect target (up to ``max_redirects``), passes
    ``guard_public_url`` before any connection. ``resolver`` / ``transport`` are
    offline test seams; production passes neither.
    """
    current = guard_public_url(url, resolver=resolver)
    try:
        async with httpx.AsyncClient(
            verify=create_verified_ssl_context(),
            timeout=timeout_seconds,
            follow_redirects=False,
            transport=transport,
            headers={
                "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.1",
                "User-Agent": "CancerLens/0.2 (stage2 url-extract)",
            },
        ) as client:
            redirects = 0
            while True:
                async with client.stream("GET", current) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        if redirects >= max_redirects:
                            raise ValueError("Too many redirects while fetching the URL.")
                        location = response.headers.get("location")
                        if not location:
                            raise ValueError("Redirect without a Location header.")
                        current = guard_public_url(urljoin(current, location), resolver=resolver)
                        redirects += 1
                        continue
                    if response.status_code != 200:
                        raise ValueError(f"URL returned HTTP {response.status_code}.")
                    content_type = response.headers.get("content-type", "")
                    if content_type and not _is_textual_content(content_type):
                        raise ValueError("URL did not return readable text content.")
                    chunks: list[bytes] = []
                    total = 0
                    async for chunk in response.aiter_bytes(65536):
                        total += len(chunk)
                        chunks.append(chunk)
                        if total >= max_bytes:
                            break
                    text = _html_to_text(b"".join(chunks)[:max_bytes].decode("utf-8", errors="replace"))
                    if not text:
                        raise ValueError("No readable text found at the URL.")
                    return sanitize_pii(text[:max_chars].strip())
    except httpx.HTTPError as exc:
        raise ValueError(f"Could not retrieve the URL ({type(exc).__name__}).") from exc


_OCR_INSTRUCTIONS = (
    "You transcribe text visible in a screenshot for CancerLens. Return ONLY the visible "
    "text, preserving reading order and line breaks. Never add facts, explanations, "
    "translations or medical advice, and never describe the image. If no readable text "
    "is visible, return exactly: NO_READABLE_TEXT"
)
_OCR_INPUT_TEXT = "Transcribe all visible text in this screenshot."

_MAGIC_MIME = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"RIFF", "image/webp"),
)


def _mime_from_magic(data: bytes) -> str:
    """MIME type from magic bytes. The upload guard already validated these, so the
    fallback below is unreachable defense in depth, never a user-facing guess."""
    for magic, mime in _MAGIC_MIME:
        if data.startswith(magic):
            if mime == "image/webp" and data[8:12] != b"WEBP":
                break
            return mime
    raise ValueError("Unsupported image type (PNG, JPEG or WEBP magic bytes required).")


@router.post("/extract/image", response_model=ExtractionResponse, responses=_EXTRACT_ERRORS, tags=["extract"])
async def extract_image(request: Request, file: UploadFile = File(...)) -> ExtractionResponse:
    data = await file.read(MAX_IMAGE_BYTES + 1)
    clean = guard_image_upload(data, file.content_type)  # ValueError -> 422 on bad uploads
    mime_type = _mime_from_magic(clean)
    result = await container(request).meta.generate_text(
        request_id=new_request_id(),
        pipeline_stage="EXTRACT:image_ocr",
        instructions=_OCR_INSTRUCTIONS,
        input_text=_OCR_INPUT_TEXT,
        image=(mime_type, base64.b64encode(clean).decode("ascii")),
    )
    text = sanitize_pii(result.text.strip()[:_URL_EXTRACT_MAX_CHARS].strip())
    if not text:
        raise ModelOutputValidationError("Screenshot transcription came back empty after safety processing.")
    return ExtractionResponse(
        modality=InputModality.IMAGE_OCR,
        extracted_text=text,
        requires_user_confirmation=True,
        warnings=["Review and edit the transcribed screenshot text before running verification."],
    )


@router.post("/extract/url", response_model=ExtractionResponse, responses=_EXTRACT_ERRORS, tags=["extract"])
async def extract_url(body: UrlExtractionRequest, request: Request) -> ExtractionResponse:
    # Launch gate first so the offline suite never performs real DNS/fetch here.
    if not container(request).settings.URL_EXTRACTION_ENABLED:
        raise CapabilityNotReadyError("Public URL extraction is not enabled.")
    text = await fetch_guarded_url_text(
        body.url,
        resolver=getattr(request.app.state, "url_guard_resolver", None),
        transport=getattr(request.app.state, "url_fetch_transport", None),
    )
    return ExtractionResponse(
        modality=InputModality.URL_EXTRACT,
        extracted_text=text,
        requires_user_confirmation=True,
        warnings=["Review and edit the extracted webpage text before running verification."],
    )


# ---------------------------------------------------------------------------- saved results
def _cited_fact_ids(envelope: ResultEnvelope) -> list[str]:
    ids = [f for v in envelope.atomic_claim_verdicts for f in v.cited_fact_ids]
    ids += [f for card in envelope.learn_category_cards for f in card.cited_fact_ids]
    return list(dict.fromkeys(ids))


@router.post(
    "/saved-results", response_model=SavedResultCreatedResponse, status_code=status.HTTP_201_CREATED,
    responses={422: _ERRORS[422]}, tags=["saved-results"],
)
async def create_saved_result(body: SavedResultCreateRequest, request: Request) -> SavedResultCreatedResponse:
    c = container(request)
    envelope = body.result_envelope
    if envelope.pipeline_state is not PipelineState.DISPLAYABLE:
        raise ValueError("Only DISPLAYABLE results can be saved.")
    # Zero medical corpus on disk: source records are dropped and re-fetched live on read.
    stored = envelope.model_copy(update={"evidence_items": []})
    doc_ids = list(dict.fromkeys(
        [d for v in envelope.atomic_claim_verdicts for d in v.cited_document_ids]
        + [i.document_id for i in envelope.evidence_items]
    ))
    saved_id, token, expires = c.store.create_saved_result(
        resolved_mode=envelope.resolved_mode.value, cancer_id=envelope.cancer_id, subtype_id=envelope.subtype_id,
        category_slug=envelope.category_slug, query_or_claim_summary=envelope.interpreted_query_or_claim,
        result_envelope_json=stored.model_dump_json(), cited_document_ids=doc_ids,
        ttl_days=c.settings.SAVED_RESULT_TTL_DAYS,
    )
    return SavedResultCreatedResponse(saved_result_id=saved_id, capability_token=token, expires_at_utc=expires)


@router.get(
    "/saved-results/{saved_result_id}", response_model=SavedResultView,
    responses={404: {"model": ErrorResponse}, 410: {"model": ErrorResponse}, 503: _ERRORS[503]},
    tags=["saved-results"],
)
async def get_saved_result(
    saved_result_id: str, request: Request, x_capability_token: str = Header(..., min_length=16, max_length=200)
) -> SavedResultView:
    c = container(request)
    row = c.store.get_saved_result_by_token(saved_result_id, x_capability_token)
    if row is None:
        raise SavedResultNotFoundError("Saved result not found.")
    envelope = ResultEnvelope.model_validate_json(row["result_envelope_json"])
    fact_ids = _cited_fact_ids(envelope)
    note = "No cited sources to re-validate."
    if fact_ids:
        try:
            items = await c.cancer_info.get_facts_by_ids(fact_ids[:50])
        except CancerInfoAPIError:
            # Upstream by-ID lookup outage (live /v1/facts verified 4 Nov 2026, so this
            # is now a transient-failure path, not a missing-endpoint path): serve the
            # stored snapshot labeled as not freshly revalidated, mirroring how
            # list_cancers degrades to TOOL_FAILED instead of a bare 503. A transport
            # failure never invalidates the saved result.
            return SavedResultView(
                saved_result_id=row["saved_result_id"], created_at_utc=parse_ts(row["created_at_utc"]),
                expires_at_utc=parse_ts(row["expires_at_utc"]), result_envelope=envelope,
                revalidated_against_cancer_info_api=False,
                revalidation_note=(
                    "Live revalidation is unavailable right now: Cancer Info API by-ID lookup failed. "
                    "Showing the saved snapshot without fresh verification; the saved result was kept "
                    "and nothing was invalidated."
                ),
            )
        missing = set(fact_ids[:50]) - {i.fact_id for i in items}
        if missing:
            c.store.delete_saved_result(saved_result_id, x_capability_token)
            raise SavedResultInvalidatedError("A cited source was withdrawn or changed; this saved result was invalidated.")
        items = await apply_link_verdicts(c, items, check_live=False)  # cached verdicts only; no fetch on read
        envelope = run_stage4_verifier(envelope.model_copy(update={"evidence_items": items}), items)
        note = "Cited sources were re-fetched live from Cancer Info API and re-verified."
    return SavedResultView(
        saved_result_id=row["saved_result_id"], created_at_utc=parse_ts(row["created_at_utc"]),
        expires_at_utc=parse_ts(row["expires_at_utc"]), result_envelope=envelope,
        revalidated_against_cancer_info_api=bool(fact_ids), revalidation_note=note,
    )


@router.delete(
    "/saved-results/{saved_result_id}", status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}}, tags=["saved-results"],
)
async def delete_saved_result(
    saved_result_id: str, request: Request, x_capability_token: str = Header(..., min_length=16, max_length=200)
) -> Response:
    if not container(request).store.delete_saved_result(saved_result_id, x_capability_token):
        raise SavedResultNotFoundError("Saved result not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------- budget
@router.get("/health/budget", response_model=BudgetHealthResponse, tags=["health"])
async def budget_health(request: Request) -> BudgetHealthResponse:
    c = container(request)
    totals = c.store.get_pool_totals()
    pools = []
    for name, client, total, cap in (
        ("meta_model_api", c.meta, c.settings.META_POOL_TOTAL_USD, c.settings.META_BUDGET_CAP_USD),
        ("baseten_model_api", c.baseten, c.settings.BASETEN_POOL_TOTAL_USD, c.settings.BASETEN_BUDGET_CAP_USD),
    ):
        spent = float(totals[name]["spent_usd"])
        committed = spent + float(totals[name]["reserved_usd"])
        pools.append(ProviderPoolStatus(
            provider_name=name, model_id=client.model_id, pool_total_usd=total, pre_submission_cap_usd=cap,
            spent_usd=round(spent, 6), remaining_before_cap_usd=round(max(0.0, cap - committed), 6),
            remaining_in_pool_usd=round(max(0.0, total - spent), 6), circuit_breaker_open=committed >= cap,
            pricing_configured=client.governor.pricing_configured, calls_logged=int(totals[name]["calls"]),
        ))
    return BudgetHealthResponse(live_llm_calls_enabled=c.settings.LIVE_LLM_CALLS_ENABLED, pools=pools)
