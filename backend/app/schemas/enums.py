"""Shared wire enums (HO-2). Values are the exact snake/upper-case strings on the wire."""

from __future__ import annotations

from enum import Enum


class LensMode(str, Enum):
    """SG-06: locked from the user's Interactive Focal Lens Switch, never from the model."""

    LEARN = "LEARN"
    EVALUATE = "EVALUATE"


class InputModality(str, Enum):
    TEXT = "TEXT"
    IMAGE_OCR = "IMAGE_OCR"
    URL_EXTRACT = "URL_EXTRACT"


class PipelineState(str, Enum):
    """SG-01: strict forward-only backend state machine. Model output never advances it."""

    INPUT_PARSED = "INPUT_PARSED"
    TOOL_REQUESTED = "TOOL_REQUESTED"
    TOOL_EXECUTED = "TOOL_EXECUTED"
    EVIDENCE_VALIDATED = "EVIDENCE_VALIDATED"
    ASSESSMENT_VALIDATED = "ASSESSMENT_VALIDATED"
    DISPLAYABLE = "DISPLAYABLE"


PIPELINE_ORDER: tuple[PipelineState, ...] = tuple(PipelineState)


class RetrievalState(str, Enum):
    """SG-03: explicit machine retrieval state. NO_MATCHES is a coverage gap, never a contradiction."""

    TOOL_NOT_EXECUTED = "TOOL_NOT_EXECUTED"
    TOOL_FAILED = "TOOL_FAILED"
    SEARCH_EXECUTED_NO_MATCHES = "SEARCH_EXECUTED_NO_MATCHES"
    SEARCH_EXECUTED_WITH_MATCHES = "SEARCH_EXECUTED_WITH_MATCHES"


class OutcomeCode(str, Enum):
    SUPPORTED = "SUPPORTED"
    MIXED_OR_CONTEXT_DEPENDENT = "MIXED_OR_CONTEXT_DEPENDENT"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    OUT_OF_SCOPE_CLINICAL = "OUT_OF_SCOPE_CLINICAL"


# Deterministic, backend-owned display labels (the model never chooses label text).
OUTCOME_LABELS: dict[OutcomeCode, str] = {
    OutcomeCode.SUPPORTED: "Supported by the cited sources",
    OutcomeCode.MIXED_OR_CONTEXT_DEPENDENT: "Mixed or depends on context",
    OutcomeCode.CONTRADICTED: "Contradicted by the cited sources",
    OutcomeCode.INSUFFICIENT_EVIDENCE: "Insufficient evidence in the CancerLens collection",
    OutcomeCode.OUT_OF_SCOPE_CLINICAL: "Outside CancerLens scope: personal medical question",
}

CORPUS_COVERAGE_GAP_LABEL = "Insufficient evidence: corpus coverage gap"
