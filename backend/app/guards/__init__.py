"""Stage 2 security, privacy, image and SSRF guards (SEC-03, SEC-04, SG-10, SEC-06).

Pure deterministic checks with no network or model calls. ``hooks.py`` delegates
to these modules while keeping its Stage 1 signatures.
"""

from .clinical_boundary import CLINICAL_REFUSAL_REASON, check_clinical_boundary
from .image_upload_guard import MAX_DIMENSION, MAX_IMAGE_BYTES, guard_image_upload
from .pii_sanitizer import sanitize_pii
from .ssrf_url_guard import guard_public_url

__all__ = [
    "CLINICAL_REFUSAL_REASON",
    "MAX_DIMENSION",
    "MAX_IMAGE_BYTES",
    "check_clinical_boundary",
    "guard_image_upload",
    "guard_public_url",
    "sanitize_pii",
]
