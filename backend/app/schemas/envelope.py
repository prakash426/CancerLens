"""Wire contracts shared with the frontend (HO-2) and Stage 2 guards (HO-1).

Every model forbids unknown fields and uses snake_case. WHO Licence 202610792
Clauses 3 & 6: AI-authored text (``ai_plain_language_*``) lives in different fields
from Cancer Info API facts (``structured_fact_or_summary``) and verbatim quotes
(``limited_verbatim_excerpt``).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import InputModality, LensMode, OutcomeCode, PipelineState, RetrievalState

_FORBID = ConfigDict(extra="forbid")


class CancerInfoEvidenceItem(BaseModel):
    """Exact contract from DATABASE.md Section 2. Dates are nullable and never fabricated."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fact_id: str = Field(description="Stable ID from Cancer Info API")
    document_id: str = Field(description="Originating source document ID")
    source_id: str = Field(description="Delivery source ID (e.g. WHO, NCI)")
    origin_source_id: str = Field(description="Upstream producer ID (prevents double-counting consensus)")
    organization_name: str
    permission_reference: str | None = Field(description='e.g. "WHO Licence 202610792"')
    source_title: str
    canonical_url: str = Field(description="Direct original URL (WHO Clause 3/6)")
    cancer_id: str
    subtype_id: str | None
    category_slug: str
    structured_fact_or_summary: str = Field(description="Cancer Info API structured fact or concise summary")
    limited_verbatim_excerpt: str | None = Field(description="Short permitted quotation, if authorized for display")
    study_design_scope: str = Field(description="guideline | rct_meta | epidemiology | preclinical")
    population_scope: str = Field(description="human_adult_general | human_high_risk | preclinical_non_human")
    jurisdiction_code: str
    observed_source_date: date | None
    retrieved_at_utc: datetime
    reviewed_at_date: date
    attribution_text: str = Field(description="Mandatory Clause 3 bibliographical reference & non-endorsement notice")
    ai_processing_allowed: bool = Field(description="Clause 6 gate checked before any external LLM transmission")


class ContextDimensionComparison(BaseModel):
    model_config = _FORBID

    dimension_name: Literal[
        "cancer_and_subtype", "population_and_stage", "study_design", "endpoint_measured", "caveat_or_dose"
    ]
    claim_assumes: str
    evidence_actually_shows: str
    is_mismatch: bool


class AtomicClaimVerdict(BaseModel):
    model_config = _FORBID

    subclaim_id: str
    atomic_claim_text: str
    outcome_code: OutcomeCode
    outcome_label: str
    ai_plain_language_explanation: str = Field(description="AI-authored (CancerLens AI), never attributed to a source")
    context_comparisons_5d: list[ContextDimensionComparison]
    cited_fact_ids: list[str]
    cited_document_ids: list[str]
    verbatim_quote_verified: bool = False
    stage4_downgraded: bool = False
    stage4_downgrade_reason: str | None = None
    pivot_to_learn_cancer_id: str | None = None
    pivot_to_learn_category_slug: str | None = None


class LearnCategoryCard(BaseModel):
    model_config = _FORBID

    category_slug: str
    category_title: str
    coverage_status: Literal["COVERED", "PARTIAL", "COVERAGE_GAP"]
    ai_plain_language_explanation: str
    cited_fact_ids: list[str]
    common_public_claims: list[str] = Field(
        default_factory=list, description="APPROVED reviewed claims only (Mechanism B chips)"
    )


class RelatedReviewedClaimItem(BaseModel):
    model_config = _FORBID

    claim_memory_id: str
    canonical_claim_text: str
    primary_outcome_code: OutcomeCode
    outcome_label: str
    nuance_warning_note: str
    how_this_differs_note: str


class ComplianceAndAttributionBanner(BaseModel):
    model_config = _FORBID

    ai_author_label: str = "AI-Generated Plain-Language Summary — Authored by CancerLens AI"
    medical_boundary_disclaimer: str = (
        "CancerLens provides general educational information and evidence analysis, "
        "not personal medical diagnosis or treatment advice."
    )
    who_non_endorsement_notice: str = (
        "Source materials used under permission (including WHO Licence 202610792 where applicable). "
        "Independently developed; not published, endorsed, or sponsored by the World Health Organization."
    )


class TelemetrySnapshot(BaseModel):
    """Redacted telemetry: no secrets, no reasoning content, no user narrative (SG-10)."""

    model_config = _FORBID

    request_id: str
    pipeline_state: PipelineState
    retrieval_state: RetrievalState
    primary_provider: str
    primary_model: str
    total_latency_ms: int
    hops_executed: int
    learned_query_mapping_applied: str | None = None
    meta_pool_spent_usd: float
    meta_pool_remaining_usd: float
    baseten_pool_spent_usd: float
    baseten_pool_remaining_usd: float


class ResultEnvelope(BaseModel):
    model_config = _FORBID

    request_id: str
    resolved_mode: LensMode
    pipeline_state: PipelineState
    retrieval_state: RetrievalState
    interpreted_query_or_claim: str
    cancer_id: str | None = None
    cancer_name: str | None = None
    subtype_id: str | None = None
    category_slug: str | None = None
    overall_outcome_code: OutcomeCode
    overall_outcome_label: str
    ai_plain_language_summary: str = Field(description="AI-authored; strictly separate from evidence_items")
    learn_category_cards: list[LearnCategoryCard] = Field(default_factory=list)
    atomic_claim_verdicts: list[AtomicClaimVerdict] = Field(default_factory=list)
    evidence_items: list[CancerInfoEvidenceItem] = Field(default_factory=list)
    related_reviewed_claims: list[RelatedReviewedClaimItem] = Field(default_factory=list)
    limitations_and_gaps_note: str
    compliance_banner: ComplianceAndAttributionBanner = Field(default_factory=ComplianceAndAttributionBanner)
    telemetry: TelemetrySnapshot


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class LearnRequest(BaseModel):
    model_config = _FORBID

    cancer_id: str = Field(default="general-oncology", min_length=1, max_length=120)
    subtype_id: str | None = Field(default=None, max_length=120)
    category_slug: str | None = Field(default=None, max_length=120)
    user_question: str | None = Field(default=None, max_length=1000)
    resolved_mode: Literal[LensMode.LEARN] = LensMode.LEARN

    @field_validator("cancer_id", mode="before")
    @classmethod
    def _default_cancer_id(cls, v: Any) -> str:
        if v is None or (isinstance(v, str) and not v.strip()):
            return "general-oncology"
        return v


class EvaluateRequest(BaseModel):
    model_config = _FORBID

    claim_text: str = Field(min_length=3, max_length=8000)
    source_modality: InputModality = InputModality.TEXT
    user_confirmed_extraction: bool = True
    cancer_id_hint: str | None = Field(default=None, max_length=120)
    subtype_id_hint: str | None = Field(default=None, max_length=120)
    resolved_mode: Literal[LensMode.EVALUATE] = LensMode.EVALUATE


class ConsistencyDoubleCheckRequest(BaseModel):
    model_config = _FORBID

    request_id: str = Field(min_length=1, max_length=120)
    claim_text: str = Field(min_length=3, max_length=8000)
    cited_fact_ids: list[str] = Field(min_length=1, max_length=50)
    primary_outcome_code: OutcomeCode


class UrlExtractionRequest(BaseModel):
    model_config = _FORBID

    url: str = Field(min_length=8, max_length=2048, description="Public https URL (SSRF guard applies)")


class ExtractionResponse(BaseModel):
    """Editable draft for the Inline Confirmation Drawer. Never evaluated without user confirmation."""

    model_config = _FORBID

    extracted_text: str
    requires_user_confirmation: Literal[True] = True
    modality: InputModality
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Supporting response models (Stage 1 additions needed to type the HO-3 routes)
# ---------------------------------------------------------------------------


class ConsistencyDoubleCheckResult(BaseModel):
    model_config = _FORBID

    original_request_id: str
    original_outcome_code: OutcomeCode
    recheck_outcome_code: OutcomeCode
    is_consistent: bool
    consistency_note: str
    recheck_envelope: ResultEnvelope


class CancerCatalogResponse(BaseModel):
    """Pass-through of the Cancer Info API taxonomy. Entry shape is owned by Cancer Info API."""

    model_config = _FORBID

    retrieval_state: RetrievalState
    cancers: list[dict[str, Any]] = Field(default_factory=list)


class SavedResultCreateRequest(BaseModel):
    model_config = _FORBID

    result_envelope: ResultEnvelope


class SavedResultCreatedResponse(BaseModel):
    model_config = _FORBID

    saved_result_id: str
    capability_token: str = Field(description="Shown once. Send as X-Capability-Token to read or delete.")
    expires_at_utc: datetime
    is_public: Literal[False] = False


class SavedResultView(BaseModel):
    model_config = _FORBID

    saved_result_id: str
    created_at_utc: datetime
    expires_at_utc: datetime
    result_envelope: ResultEnvelope
    revalidated_against_cancer_info_api: bool
    revalidation_note: str


class ProviderPoolStatus(BaseModel):
    model_config = _FORBID

    provider_name: Literal["meta_model_api", "baseten_model_api"]
    model_id: str
    pool_total_usd: float
    pre_submission_cap_usd: float
    spent_usd: float
    remaining_before_cap_usd: float
    remaining_in_pool_usd: float
    circuit_breaker_open: bool
    pricing_configured: bool
    calls_logged: int


class BudgetHealthResponse(BaseModel):
    model_config = _FORBID

    live_llm_calls_enabled: bool
    pools: list[ProviderPoolStatus]


class ErrorResponse(BaseModel):
    model_config = _FORBID

    error_code: str
    message: str
    request_id: str | None = None
