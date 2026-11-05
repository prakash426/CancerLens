"""Deterministic Stage-4 provenance and quote verification (SG-08 / Gate 5)."""

from .stage4_verifier import normalize_for_quote_match, run_stage4_verifier

__all__ = ["normalize_for_quote_match", "run_stage4_verifier"]
