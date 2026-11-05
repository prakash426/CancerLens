"""HO-1 extension points, hardened in Stage 2.

Thin delegates over ``backend/app/guards/`` and ``backend/app/verifiers/``.
All Stage 1 signatures, return types and re-exports are preserved exactly.
"""

from __future__ import annotations

from ..guards.clinical_boundary import CLINICAL_REFUSAL_REASON, check_clinical_boundary
from ..guards.image_upload_guard import guard_image_upload
from ..guards.pii_sanitizer import sanitize_pii
from ..guards.ssrf_url_guard import guard_public_url
from ..schemas.enums import PipelineState
from ..verifiers.stage4_verifier import normalize_for_quote_match, run_stage4_verifier


class CapabilityNotReadyError(RuntimeError):
    """A guarded capability (image / URL extraction) is not available yet."""


__all__ = [
    "CLINICAL_REFUSAL_REASON",
    "CapabilityNotReadyError",
    "PipelineState",
    "check_clinical_boundary",
    "guard_image_upload",
    "guard_public_url",
    "normalize_for_quote_match",
    "run_stage4_verifier",
    "sanitize_pii",
]
