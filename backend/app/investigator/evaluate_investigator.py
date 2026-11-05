"""Evaluate Lens: bounded claim verification on Baseten ``meta-models/muse-spark-open-1026``.

Flow (SG-01): INPUT_PARSED (T2/T3 normalize + split) -> TOOL_REQUESTED (T4 tool plan, SG-02
prose purge) -> TOOL_EXECUTED (backend runs <= 3 hops against Cancer Info API, SG-03) ->
EVIDENCE_VALIDATED (Clause 6 admission) -> T5 grounded verdicts + 5D matrix (SG-07) ->
ASSESSMENT_VALIDATED (Stage-4, SG-08) -> DISPLAYABLE.

The model never decides the mode (SG-06), never sees zero-match states as evidence (SG-03),
and its outcome labels are replaced by backend labels.
"""

from __future__ import annotations

import logging
import time

from ..clients.cancerinfo_client import CancerInfoAPIError
from ..providers.baseten_client import DIMENSIONS_5D, ModelClaimVerdict, VerificationOutput
from ..schemas.enums import OUTCOME_LABELS, InputModality, LensMode, OutcomeCode, PipelineState, RetrievalState
from ..schemas.envelope import (
    AtomicClaimVerdict,
    CancerInfoEvidenceItem,
    ComplianceAndAttributionBanner,
    ConsistencyDoubleCheckRequest,
    ConsistencyDoubleCheckResult,
    EvaluateRequest,
    ResultEnvelope,
)
from .common import (
    NOT_AI_PROCESSABLE_NOTE,
    OUT_OF_SCOPE_NOTE,
    ExtractionNotConfirmedError,
    PipelineTracker,
    ServiceContainer,
    abstention_envelope,
    apply_link_verdicts,
    build_telemetry,
    combine_retrieval_states,
    dedupe_items,
    deterministic_summary,
    evidence_version_hash,
    label_for_non_assessed,
    new_request_id,
    related_reviewed_claims,
)
from .hooks import check_clinical_boundary, run_stage4_verifier, sanitize_pii

logger = logging.getLogger("cancerlens.evaluate")

MAX_EVIDENCE_ITEMS = 24
SEARCH_LIMIT_PER_CALL = 8
NOT_A_CANCER_CLAIM_LABEL = "Not assessed: this does not appear to be a cancer-related claim"


def _subclaim_id(request_id: str, index: int) -> str:
    return f"{request_id}-c{index}"


def _missing_verdict(request_id: str, index: int, claim: str, reason: str) -> AtomicClaimVerdict:
    return AtomicClaimVerdict(
        subclaim_id=_subclaim_id(request_id, index), atomic_claim_text=claim,
        outcome_code=OutcomeCode.INSUFFICIENT_EVIDENCE, outcome_label=OUTCOME_LABELS[OutcomeCode.INSUFFICIENT_EVIDENCE],
        ai_plain_language_explanation=f"No usable assessment was produced for this sub-claim ({reason}).",
        context_comparisons_5d=[], cited_fact_ids=[], cited_document_ids=[],
        stage4_downgraded=True, stage4_downgrade_reason=reason,
    )


def build_verdicts(
    request_id: str, claims: list[str], output: VerificationOutput
) -> tuple[list[AtomicClaimVerdict], dict[str, str]]:
    """Map model verdicts onto backend-owned claim slots. Returns (verdicts, claimed_quotes)."""
    by_index: dict[int, ModelClaimVerdict] = {}
    for verdict in output.verdicts:
        by_index.setdefault(verdict.subclaim_index, verdict)
    verdicts: list[AtomicClaimVerdict] = []
    quotes: dict[str, str] = {}
    for index, claim in enumerate(claims, start=1):
        model = by_index.get(index)
        if model is None:
            verdicts.append(_missing_verdict(request_id, index, claim, "the model returned no verdict for it"))
            continue
        dims = [d.dimension_name for d in model.context_comparisons_5d]
        if sorted(dims) != sorted(DIMENSIONS_5D):
            verdicts.append(_missing_verdict(request_id, index, claim, "the 5D context comparison was incomplete"))
            continue
        order = {name: i for i, name in enumerate(DIMENSIONS_5D)}
        code = OutcomeCode(model.outcome_code)
        sid = _subclaim_id(request_id, index)
        verdicts.append(AtomicClaimVerdict(
            subclaim_id=sid, atomic_claim_text=claim, outcome_code=code, outcome_label=OUTCOME_LABELS[code],
            ai_plain_language_explanation=model.ai_plain_language_explanation.strip(),
            context_comparisons_5d=sorted(model.context_comparisons_5d, key=lambda d: order[d.dimension_name]),
            cited_fact_ids=model.cited_fact_ids, cited_document_ids=model.cited_document_ids,
        ))
        if model.quoted_excerpt and model.quoted_excerpt.strip():
            quotes[sid] = model.quoted_excerpt.strip()
    return verdicts, quotes


async def _retrieve(
    c: ServiceContainer, request_id: str, claims: list[str], cancer_topic: str, req_hints: tuple[str | None, str | None]
) -> tuple[RetrievalState, list[CancerInfoEvidenceItem], int]:
    """Bounded hop loop. Backend executes every search; model prose is never used (SG-02)."""
    cancer_id_hint, subtype_hint = req_hints
    states: list[RetrievalState] = []
    items: list[CancerInfoEvidenceItem] = []
    prior: list[dict] = []
    hops = 0
    for hop in range(c.settings.EVALUATE_MAX_HOPS):
        planned = await c.baseten.plan_evidence_search_tool_call(
            claims, cancer_topic, hop, request_id=request_id, prior_searches=prior
        )
        if not planned:
            break
        hops += 1
        hop_states = []
        for call in planned:
            state, found = await c.cancer_info.search_evidence(
                call.search_query, cancer_id=cancer_id_hint, subtype_id=subtype_hint, limit=SEARCH_LIMIT_PER_CALL
            )
            hop_states.append(state)
            items.extend(found)
            prior.append({"search_query": call.search_query, "retrieval_state": state.value, "match_count": len(found)})
        states.extend(hop_states)
        if items or all(s is RetrievalState.TOOL_FAILED for s in hop_states):
            break
    return combine_retrieval_states(states), dedupe_items(items)[:MAX_EVIDENCE_ITEMS], hops


def _capture_claim_memory(c: ServiceContainer, verdicts: list[AtomicClaimVerdict], items: list[CancerInfoEvidenceItem]) -> None:
    """PENDING_REVIEW candidates only, PII-sanitized (SG-10). Disabled unless CLAIM_MEMORY_CAPTURE_ENABLED."""
    if not c.settings.CLAIM_MEMORY_CAPTURE_ENABLED:
        return
    by_fact = {i.fact_id: i for i in items}
    for verdict in verdicts:
        cited = [by_fact[f] for f in verdict.cited_fact_ids if f in by_fact]
        if verdict.stage4_downgraded or not cited or verdict.outcome_code is OutcomeCode.OUT_OF_SCOPE_CLINICAL:
            continue
        text = sanitize_pii(verdict.atomic_claim_text).strip()
        if not 15 <= len(text) <= 600:
            continue
        try:
            c.store.record_candidate_claim_memory(
                canonical_claim_text=text, cancer_id=cited[0].cancer_id, subtype_id=cited[0].subtype_id,
                category_slug=cited[0].category_slug, primary_outcome_code=verdict.outcome_code.value,
                outcome_label=verdict.outcome_label, nuance_warning_note=verdict.ai_plain_language_explanation[:300],
                cited_document_ids=verdict.cited_document_ids, cited_fact_ids=verdict.cited_fact_ids,
                cancer_info_api_version_hash=evidence_version_hash(cited), pii_sanitized_verified=True,
            )
        except Exception:  # noqa: BLE001 - memory capture is best-effort
            logger.exception("Claim memory capture failed")


async def _assess(
    c: ServiceContainer,
    *,
    tracker: PipelineTracker,
    started: float,
    interpreted: str,
    claims: list[str],
    retrieval_state: RetrievalState,
    items: list[CancerInfoEvidenceItem],
    hops: int,
    cancer_id_hint: str | None,
    subtype_hint: str | None,
) -> ResultEnvelope:
    """Shared tail for Evaluate and the double-check: TOOL_EXECUTED -> ... -> DISPLAYABLE."""
    common = dict(cancer_id=cancer_id_hint, subtype_id=subtype_hint)
    related = related_reviewed_claims(c, interpreted, cancer_id_hint)
    provider = dict(primary_provider=c.baseten.provider_name, primary_model=c.baseten.model_id)

    if retrieval_state is not RetrievalState.SEARCH_EXECUTED_WITH_MATCHES:  # SG-03: never CONTRADICTED
        label, note = label_for_non_assessed(retrieval_state)
        return abstention_envelope(
            c, tracker=tracker, mode=LensMode.EVALUATE, retrieval_state=retrieval_state,
            outcome_code=OutcomeCode.INSUFFICIENT_EVIDENCE, outcome_label=label, summary=note, note=note,
            interpreted=interpreted, started_at=started, hops_executed=hops, related=related,
            walk_states=retrieval_state is RetrievalState.SEARCH_EXECUTED_NO_MATCHES, **provider, **common,
        )

    items = await apply_link_verdicts(c, items)
    admitted = [i for i in items if i.ai_processing_allowed is True]  # WHO Clause 6 gate
    tracker.advance(PipelineState.EVIDENCE_VALIDATED)
    if not admitted:
        return abstention_envelope(
            c, tracker=tracker, mode=LensMode.EVALUATE, retrieval_state=retrieval_state,
            outcome_code=OutcomeCode.INSUFFICIENT_EVIDENCE,
            outcome_label="Not assessed: sources found but AI processing is not permitted",
            summary=NOT_AI_PROCESSABLE_NOTE, note=NOT_AI_PROCESSABLE_NOTE, interpreted=interpreted,
            started_at=started, hops_executed=hops, evidence_items=items, related=related, walk_states=True,
            **provider, **common,
        )

    output = await c.baseten.verify_claims_against_evidence(
        claims, retrieval_state, admitted, request_id=tracker.request_id
    )
    verdicts, quotes = build_verdicts(tracker.request_id, claims, output)
    envelope = ResultEnvelope(
        request_id=tracker.request_id, resolved_mode=LensMode.EVALUATE, pipeline_state=tracker.state,
        retrieval_state=retrieval_state, interpreted_query_or_claim=interpreted, **common,
        overall_outcome_code=OutcomeCode.INSUFFICIENT_EVIDENCE, overall_outcome_label="(computed by Stage-4)",
        ai_plain_language_summary=output.overall_summary.strip(), atomic_claim_verdicts=verdicts,
        evidence_items=items, related_reviewed_claims=related,
        limitations_and_gaps_note=(
            "Assessed only against records in the CancerLens collection; other evidence may exist. "
            "Not medical advice."
            + (" Some records were shown without AI processing because their permissions do not allow it."
               if len(admitted) < len(items) else "")
        ),
        compliance_banner=ComplianceAndAttributionBanner(),
        telemetry=build_telemetry(
            c, request_id=tracker.request_id, pipeline_state=tracker.state, retrieval_state=retrieval_state,
            started_at=started, hops_executed=hops, **provider,
        ),
    )
    if any(v.stage4_downgraded for v in verdicts):
        envelope = envelope.model_copy(update={"ai_plain_language_summary": ""})
    envelope = run_stage4_verifier(envelope, admitted, quotes)  # SG-08
    if not envelope.ai_plain_language_summary:
        envelope = envelope.model_copy(update={"ai_plain_language_summary": deterministic_summary(envelope.atomic_claim_verdicts)})
    if envelope.cancer_id is None and envelope.atomic_claim_verdicts:
        first = next((v.pivot_to_learn_cancer_id for v in envelope.atomic_claim_verdicts if v.pivot_to_learn_cancer_id), None)
        envelope = envelope.model_copy(update={"cancer_id": first})
    tracker.advance(PipelineState.ASSESSMENT_VALIDATED)
    tracker.advance(PipelineState.DISPLAYABLE)
    _capture_claim_memory(c, envelope.atomic_claim_verdicts, admitted)
    return envelope.model_copy(update={
        "pipeline_state": tracker.state,
        "telemetry": build_telemetry(
            c, request_id=tracker.request_id, pipeline_state=tracker.state, retrieval_state=retrieval_state,
            started_at=started, hops_executed=hops, **provider,
        ),
    })


async def run_evaluate_investigator(req: EvaluateRequest, c: ServiceContainer) -> ResultEnvelope:
    started = time.monotonic()
    tracker = PipelineTracker(new_request_id())  # SG-06: mode is EVALUATE by request type
    if req.source_modality is not InputModality.TEXT and not req.user_confirmed_extraction:
        raise ExtractionNotConfirmedError("Extracted text must be confirmed by the user before evaluation.")

    claim_text = sanitize_pii(" ".join(req.claim_text.split()))
    common = dict(cancer_id=req.cancer_id_hint, subtype_id=req.subtype_id_hint)
    out_of_scope, _ = check_clinical_boundary(claim_text)
    if out_of_scope:
        return abstention_envelope(
            c, tracker=tracker, mode=LensMode.EVALUATE, retrieval_state=RetrievalState.TOOL_NOT_EXECUTED,
            outcome_code=OutcomeCode.OUT_OF_SCOPE_CLINICAL, outcome_label=OUTCOME_LABELS[OutcomeCode.OUT_OF_SCOPE_CLINICAL],
            summary=OUT_OF_SCOPE_NOTE, note=OUT_OF_SCOPE_NOTE, interpreted=claim_text, started_at=started, **common,
        )

    normalized = await c.baseten.normalize_and_split_claims(claim_text, request_id=tracker.request_id)
    provider = dict(primary_provider=c.baseten.provider_name, primary_model=c.baseten.model_id)
    interpreted = " | ".join(normalized.claims)
    # Model intent is advisory (SG-06); it may only make the result MORE cautious.
    if normalized.intent == "personal_clinical_question":
        return abstention_envelope(
            c, tracker=tracker, mode=LensMode.EVALUATE, retrieval_state=RetrievalState.TOOL_NOT_EXECUTED,
            outcome_code=OutcomeCode.OUT_OF_SCOPE_CLINICAL, outcome_label=OUTCOME_LABELS[OutcomeCode.OUT_OF_SCOPE_CLINICAL],
            summary=OUT_OF_SCOPE_NOTE, note=OUT_OF_SCOPE_NOTE, interpreted=interpreted, started_at=started,
            **provider, **common,
        )
    if normalized.intent == "out_of_scope":
        note = "This does not appear to be a cancer-related claim, so CancerLens did not search or assess it."
        return abstention_envelope(
            c, tracker=tracker, mode=LensMode.EVALUATE, retrieval_state=RetrievalState.TOOL_NOT_EXECUTED,
            outcome_code=OutcomeCode.INSUFFICIENT_EVIDENCE, outcome_label=NOT_A_CANCER_CLAIM_LABEL,
            summary=note, note=note, interpreted=interpreted, started_at=started, **provider, **common,
        )

    tracker.advance(PipelineState.TOOL_REQUESTED)
    retrieval_state, items, hops = await _retrieve(
        c, tracker.request_id, normalized.claims, normalized.cancer_topic or "", (req.cancer_id_hint, req.subtype_id_hint)
    )
    if retrieval_state is RetrievalState.TOOL_NOT_EXECUTED:
        label, note = label_for_non_assessed(retrieval_state)
        return abstention_envelope(
            c, tracker=tracker, mode=LensMode.EVALUATE, retrieval_state=retrieval_state,
            outcome_code=OutcomeCode.INSUFFICIENT_EVIDENCE, outcome_label=label, summary=note, note=note,
            interpreted=interpreted, started_at=started, hops_executed=hops, **provider, **common,
        )
    tracker.advance(PipelineState.TOOL_EXECUTED)
    return await _assess(
        c, tracker=tracker, started=started, interpreted=interpreted, claims=normalized.claims,
        retrieval_state=retrieval_state, items=items, hops=hops,
        cancer_id_hint=req.cancer_id_hint, subtype_hint=req.subtype_id_hint,
    )


async def run_consistency_double_check(req: ConsistencyDoubleCheckRequest, c: ServiceContainer) -> ConsistencyDoubleCheckResult:
    """1-click re-verification of a claim against the SAME cited facts, re-fetched live.

    Agreement between two runs shows stability, not correctness.
    """
    started = time.monotonic()
    tracker = PipelineTracker(new_request_id())
    claim_text = sanitize_pii(" ".join(req.claim_text.split()))
    normalized = await c.baseten.normalize_and_split_claims(claim_text, request_id=tracker.request_id)
    tracker.advance(PipelineState.TOOL_REQUESTED)
    try:
        items = await c.cancer_info.get_facts_by_ids(req.cited_fact_ids)
    except CancerInfoAPIError as exc:
        # A re-check without live facts cannot run honestly, so this stays a 503;
        # the message names the cause so the UI can render it as a labeled banner.
        raise CancerInfoAPIError(
            "Consistency double-check is unavailable right now: cited facts could not be "
            "re-fetched live (Cancer Info API by-ID lookup failed). "
            "The original result stands as returned."
        ) from exc
    tracker.advance(PipelineState.TOOL_EXECUTED)
    state = RetrievalState.SEARCH_EXECUTED_WITH_MATCHES if items else RetrievalState.SEARCH_EXECUTED_NO_MATCHES
    envelope = await _assess(
        c, tracker=tracker, started=started, interpreted=" | ".join(normalized.claims), claims=normalized.claims,
        retrieval_state=state, items=items, hops=1, cancer_id_hint=None, subtype_hint=None,
    )
    consistent = envelope.overall_outcome_code is req.primary_outcome_code
    missing = len(set(req.cited_fact_ids) - {i.fact_id for i in items})
    note = (
        "The re-check reached the same overall outcome." if consistent
        else "The re-check reached a different overall outcome; treat this result with extra caution."
    )
    if missing:
        note += f" {missing} originally cited fact(s) are no longer returned by Cancer Info API."
    return ConsistencyDoubleCheckResult(
        original_request_id=req.request_id, original_outcome_code=req.primary_outcome_code,
        recheck_outcome_code=envelope.overall_outcome_code, is_consistent=consistent,
        consistency_note=note, recheck_envelope=envelope,
    )
