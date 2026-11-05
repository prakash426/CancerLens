"""Shared pipeline plumbing: service container, SG-01 state tracker, deterministic envelopes.

Stage 1 helper module (not in the handoff file tree) so Learn and Evaluate share one
implementation of telemetry, abstention envelopes and outcome aggregation.
"""

from __future__ import annotations

import hashlib
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..schemas.enums import (
    CORPUS_COVERAGE_GAP_LABEL,
    OUTCOME_LABELS,
    PIPELINE_ORDER,
    LensMode,
    OutcomeCode,
    PipelineState,
    RetrievalState,
)
from ..guards.link_check import verify_source_links
from ..schemas.envelope import (
    AtomicClaimVerdict,
    CancerInfoEvidenceItem,
    ComplianceAndAttributionBanner,
    LearnCategoryCard,
    RelatedReviewedClaimItem,
    ResultEnvelope,
    TelemetrySnapshot,
)

if TYPE_CHECKING:
    import httpx

    from ..clients.cancerinfo_client import CancerInfoAPIClient
    from ..config import Settings
    from ..db.operational_store import OperationalStore
    from ..guards.ssrf_url_guard import Resolver
    from ..providers.baseten_client import BasetenClaimVerifierClient
    from ..providers.meta_client import MetaMuseClient

logger = logging.getLogger("cancerlens.investigator")

NO_PROVIDER = "none"

GAP_NOTE = (
    "CORPUS_COVERAGE_GAP: the CancerLens collection returned no matching records. This is not evidence that the "
    "statement is false. For authoritative information, consult official sources such as the U.S. National Cancer "
    "Institute (https://www.cancer.gov) or the World Health Organization (https://www.who.int), and talk with a "
    "licensed clinician about personal questions."
)
TOOL_FAILED_NOTE = (
    "The Cancer Info API could not be reached or returned an invalid response, so nothing was assessed. "
    "This is a service problem, not a finding about the statement. Please try again shortly."
)
NOT_EXECUTED_NOTE = "No evidence search was executed, so nothing was assessed."
OUT_OF_SCOPE_NOTE = (
    "CancerLens cannot help with personal diagnosis, symptom triage, treatment choices or dosing. Please talk "
    "with a licensed clinician. If this is urgent, contact local emergency services."
)
NOT_AI_PROCESSABLE_NOTE = (
    "Matching source records were found, but their permissions do not allow AI processing, so no AI assessment "
    "was generated. The source facts and original links are shown directly."
)


class PipelineStateError(RuntimeError):
    pass


class ExtractionNotConfirmedError(ValueError):
    """SG-01: OCR / URL text must be confirmed by the user before evaluation."""


@dataclass
class ServiceContainer:
    settings: "Settings"
    store: "OperationalStore"
    cancer_info: "CancerInfoAPIClient"
    meta: "MetaMuseClient"
    baseten: "BasetenClaimVerifierClient"
    # Offline seams for source-link verification (None = real network + real DNS).
    link_check_transport: httpx.AsyncBaseTransport | None = None
    link_check_resolver: Resolver | None = None


@dataclass
class PipelineTracker:
    """SG-01: forward-only state machine. Only backend code advances it, one step at a time."""

    request_id: str
    state: PipelineState = PipelineState.INPUT_PARSED
    history: list[PipelineState] = field(default_factory=lambda: [PipelineState.INPUT_PARSED])
    abstained_from: PipelineState | None = None

    def advance(self, target: PipelineState) -> None:
        current = PIPELINE_ORDER.index(self.state)
        if PIPELINE_ORDER.index(target) != current + 1:
            raise PipelineStateError(f"Illegal transition {self.state.value} -> {target.value}")
        self.state = target
        self.history.append(target)

    def advance_to(self, target: PipelineState) -> None:
        while self.state != target:
            self.advance(PIPELINE_ORDER[PIPELINE_ORDER.index(self.state) + 1])

    def abstain(self) -> None:
        """Deterministic safe exit (refusal / not executed): finalize without a model verdict."""
        if self.state != PipelineState.DISPLAYABLE:
            self.abstained_from = self.state
            self.state = PipelineState.DISPLAYABLE
            self.history.append(PipelineState.DISPLAYABLE)


def new_request_id() -> str:
    return f"req_{uuid.uuid4().hex}"


def titleize_slug(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.replace("_", "-").split("-") if part)


def evidence_version_hash(items: list[CancerInfoEvidenceItem]) -> str:
    """Fingerprint of the exact evidence used (no API version header is known in Stage 1)."""
    material = "|".join(
        sorted(f"{i.fact_id}:{i.document_id}:{i.reviewed_at_date.isoformat()}" for i in items)
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def dedupe_items(items: list[CancerInfoEvidenceItem]) -> list[CancerInfoEvidenceItem]:
    seen: dict[str, CancerInfoEvidenceItem] = {}
    for item in items:
        seen.setdefault(item.fact_id, item)
    return list(seen.values())


async def apply_link_verdicts(
    c: ServiceContainer, items: list[CancerInfoEvidenceItem], *, check_live: bool = True
) -> list[CancerInfoEvidenceItem]:
    """Return copies of ``items`` with ``link_ok=False`` where the canonical URL is proven dead.

    Cached verdicts (24h TTL) are reused; only uncached URLs are fetched, in one
    parallel batch. Never raises and never drops evidence: any failure keeps
    every link visible. With ``check_live=False`` only cached verdicts apply.
    """
    if not items:
        return items
    try:
        urls = list(dict.fromkeys(i.canonical_url.strip() for i in items if i.canonical_url.strip()))
        verdicts: dict[str, bool] = {}
        uncached = []
        for url in urls:
            cached = c.store.get_link_verdict(url)
            if cached is None:
                uncached.append(url)
            else:
                verdicts[url] = cached
        if uncached and check_live:
            live = await verify_source_links(
                uncached, transport=c.link_check_transport, resolver=c.link_check_resolver
            )
            for url, alive in live.items():
                verdicts[url] = alive
                try:
                    c.store.set_link_verdict(url, alive)
                except Exception:  # noqa: BLE001 - verdict caching is best-effort
                    logger.exception("Link verdict caching failed")
        return [
            item.model_copy(update={"link_ok": verdicts.get(item.canonical_url.strip(), True)})
            for item in items
        ]
    except Exception:  # noqa: BLE001 - link verification must never break a pipeline
        logger.exception("Source-link verification failed; keeping all links visible")
        return items


def combine_retrieval_states(states: list[RetrievalState]) -> RetrievalState:
    """WITH_MATCHES wins; any failure without matches is TOOL_FAILED (a gap cannot be claimed)."""
    if not states:
        return RetrievalState.TOOL_NOT_EXECUTED
    if RetrievalState.SEARCH_EXECUTED_WITH_MATCHES in states:
        return RetrievalState.SEARCH_EXECUTED_WITH_MATCHES
    if RetrievalState.TOOL_FAILED in states:
        return RetrievalState.TOOL_FAILED
    if RetrievalState.SEARCH_EXECUTED_NO_MATCHES in states:
        return RetrievalState.SEARCH_EXECUTED_NO_MATCHES
    return RetrievalState.TOOL_NOT_EXECUTED


def aggregate_outcome(verdicts: list[AtomicClaimVerdict]) -> tuple[OutcomeCode, str]:
    if not verdicts:
        return OutcomeCode.INSUFFICIENT_EVIDENCE, OUTCOME_LABELS[OutcomeCode.INSUFFICIENT_EVIDENCE]
    codes = {v.outcome_code for v in verdicts}
    if len(codes) == 1:
        code = codes.pop()
        return code, OUTCOME_LABELS[code]
    return OutcomeCode.MIXED_OR_CONTEXT_DEPENDENT, "Sub-claims have different outcomes; review each verdict"


def deterministic_summary(verdicts: list[AtomicClaimVerdict]) -> str:
    counts: dict[str, int] = {}
    for verdict in verdicts:
        counts[verdict.outcome_label] = counts.get(verdict.outcome_label, 0) + 1
    parts = ", ".join(f"{n} {label.lower()}" for label, n in counts.items())
    return (
        f"CancerLens checked {len(verdicts)} sub-claim(s): {parts}. "
        "Some AI reasoning could not be verified against the retrieved sources and was withheld."
    )


def build_telemetry(
    c: ServiceContainer,
    *,
    request_id: str,
    pipeline_state: PipelineState,
    retrieval_state: RetrievalState,
    primary_provider: str,
    primary_model: str,
    started_at: float,
    hops_executed: int,
    learned_query_mapping_applied: str | None = None,
) -> TelemetrySnapshot:
    totals = c.store.get_pool_totals()
    meta_spent = float(totals["meta_model_api"]["spent_usd"])
    baseten_spent = float(totals["baseten_model_api"]["spent_usd"])
    return TelemetrySnapshot(
        request_id=request_id,
        pipeline_state=pipeline_state,
        retrieval_state=retrieval_state,
        primary_provider=primary_provider,
        primary_model=primary_model,
        total_latency_ms=int((time.monotonic() - started_at) * 1000),
        hops_executed=hops_executed,
        learned_query_mapping_applied=learned_query_mapping_applied,
        meta_pool_spent_usd=round(meta_spent, 6),
        meta_pool_remaining_usd=round(c.settings.META_POOL_TOTAL_USD - meta_spent, 6),
        baseten_pool_spent_usd=round(baseten_spent, 6),
        baseten_pool_remaining_usd=round(c.settings.BASETEN_POOL_TOTAL_USD - baseten_spent, 6),
    )


def related_reviewed_claims(c: ServiceContainer, query_text: str, cancer_id: str | None) -> list[RelatedReviewedClaimItem]:
    """APPROVED rows only (Gate 7). Failures here never break the main result."""
    try:
        rows = c.store.search_approved_similar_claims_fts(query_text, cancer_id, limit=3)
    except Exception:  # noqa: BLE001 - memory is best-effort
        logger.exception("Related reviewed claims lookup failed")
        return []
    return [
        RelatedReviewedClaimItem(
            claim_memory_id=row["claim_memory_id"],
            canonical_claim_text=row["canonical_claim_text"],
            primary_outcome_code=OutcomeCode(row["primary_outcome_code"]),
            outcome_label=row["outcome_label"],
            nuance_warning_note=row["nuance_warning_note"],
            how_this_differs_note=(
                "A separately reviewed claim. Its wording, population or context may differ from yours."
            ),
        )
        for row in rows
    ]


def abstention_envelope(
    c: ServiceContainer,
    *,
    tracker: PipelineTracker,
    mode: LensMode,
    retrieval_state: RetrievalState,
    outcome_code: OutcomeCode,
    outcome_label: str,
    summary: str,
    note: str,
    interpreted: str,
    started_at: float,
    cancer_id: str | None = None,
    subtype_id: str | None = None,
    category_slug: str | None = None,
    hops_executed: int = 0,
    primary_provider: str = NO_PROVIDER,
    primary_model: str = NO_PROVIDER,
    learn_cards: list[LearnCategoryCard] | None = None,
    evidence_items: list[CancerInfoEvidenceItem] | None = None,
    related: list[RelatedReviewedClaimItem] | None = None,
    walk_states: bool = False,
    mapping_applied: str | None = None,
) -> ResultEnvelope:
    """Deterministic envelope with no model verdict. ``walk_states`` walks the full SG-01 chain
    (used when retrieval genuinely executed); otherwise the tracker abstains."""
    if walk_states:
        tracker.advance_to(PipelineState.DISPLAYABLE)
    else:
        tracker.abstain()
    return ResultEnvelope(
        request_id=tracker.request_id,
        resolved_mode=mode,
        pipeline_state=tracker.state,
        retrieval_state=retrieval_state,
        interpreted_query_or_claim=interpreted,
        cancer_id=cancer_id,
        subtype_id=subtype_id,
        category_slug=category_slug,
        overall_outcome_code=outcome_code,
        overall_outcome_label=outcome_label,
        ai_plain_language_summary=summary,
        learn_category_cards=learn_cards or [],
        evidence_items=evidence_items or [],
        related_reviewed_claims=related or [],
        limitations_and_gaps_note=note,
        compliance_banner=ComplianceAndAttributionBanner(),
        telemetry=build_telemetry(
            c,
            request_id=tracker.request_id,
            pipeline_state=tracker.state,
            retrieval_state=retrieval_state,
            primary_provider=primary_provider,
            primary_model=primary_model,
            started_at=started_at,
            hops_executed=hops_executed,
            learned_query_mapping_applied=mapping_applied,
        ),
    )


def label_for_non_assessed(retrieval_state: RetrievalState) -> tuple[str, str]:
    """(label, note) for retrieval states that never reach a model verdict (SG-03)."""
    if retrieval_state is RetrievalState.SEARCH_EXECUTED_NO_MATCHES:
        return CORPUS_COVERAGE_GAP_LABEL, GAP_NOTE
    if retrieval_state is RetrievalState.TOOL_FAILED:
        return "Not assessed: evidence service unavailable", TOOL_FAILED_NOTE
    return "Not assessed: no evidence search was executed", NOT_EXECUTED_NOTE
