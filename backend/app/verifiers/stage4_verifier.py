"""SG-08 deterministic Stage-4 provenance and quote verifier.

Factored verbatim from the Stage 1 ``hooks.py`` baseline into
``backend/app/verifiers/`` in Stage 2 with no behavior change:
every cited ``fact_id`` / ``document_id`` and verbatim quote is mechanically
checked in Python against the ``Cancer Info API`` items retrieved in that
request before the envelope reaches ``DISPLAYABLE``.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping

from ..investigator.common import aggregate_outcome, deterministic_summary
from ..schemas.enums import OUTCOME_LABELS, LensMode, OutcomeCode
from ..schemas.envelope import AtomicClaimVerdict, CancerInfoEvidenceItem, LearnCategoryCard, ResultEnvelope

_QUOTE_TRANSLATION = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-"})


def normalize_for_quote_match(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(_QUOTE_TRANSLATION).casefold()
    return " ".join(text.split()).strip(" \"'.,;:")


def _quote_is_verbatim(quote: str, cited_items: list[CancerInfoEvidenceItem]) -> bool:
    needle = normalize_for_quote_match(quote)
    if len(needle) < 8:
        return False
    return any(
        item.limited_verbatim_excerpt and needle in normalize_for_quote_match(item.limited_verbatim_excerpt)
        for item in cited_items
    )


def _downgrade(verdict: AtomicClaimVerdict, reason: str, valid_fact_ids: list[str], valid_doc_ids: list[str]) -> AtomicClaimVerdict:
    return verdict.model_copy(
        update={
            "outcome_code": OutcomeCode.INSUFFICIENT_EVIDENCE,
            "outcome_label": OUTCOME_LABELS[OutcomeCode.INSUFFICIENT_EVIDENCE],
            "ai_plain_language_explanation": (
                "CancerLens could not verify this assessment against the sources retrieved for this request, "
                f"so it is shown as insufficient evidence. Reason: {reason}"
            ),
            "context_comparisons_5d": [],
            "cited_fact_ids": valid_fact_ids,
            "cited_document_ids": valid_doc_ids,
            "verbatim_quote_verified": False,
            "stage4_downgraded": True,
            "stage4_downgrade_reason": reason,
        }
    )


def _verify_verdict(
    verdict: AtomicClaimVerdict,
    by_fact: dict[str, CancerInfoEvidenceItem],
    known_docs: set[str],
    claimed_quote: str | None,
) -> AtomicClaimVerdict:
    if verdict.outcome_code is OutcomeCode.OUT_OF_SCOPE_CLINICAL:
        return verdict
    cited = list(dict.fromkeys(verdict.cited_fact_ids))
    valid_facts = [fid for fid in cited if fid in by_fact]
    unknown_facts = [fid for fid in cited if fid not in by_fact]
    cited_items = [by_fact[fid] for fid in valid_facts]
    # Document IDs are derived from the valid facts; any model-supplied doc not in this request is an error.
    derived_docs = list(dict.fromkeys(item.document_id for item in cited_items))
    unknown_docs = [d for d in dict.fromkeys(verdict.cited_document_ids) if d not in known_docs]

    reason: str | None = None
    if unknown_facts:
        reason = f"cited fact_id(s) not returned by Cancer Info API in this request: {', '.join(unknown_facts[:5])}"
    elif unknown_docs:
        reason = f"cited document_id(s) not returned in this request: {', '.join(unknown_docs[:5])}"
    elif verdict.outcome_code is not OutcomeCode.INSUFFICIENT_EVIDENCE and not valid_facts:
        reason = "assessment has no supporting citation"
    elif claimed_quote and not _quote_is_verbatim(claimed_quote, cited_items):
        reason = "quoted text is not an exact excerpt of a cited source"
    if reason:
        return _downgrade(verdict, reason, valid_facts, derived_docs)

    pivot_item = cited_items[0] if cited_items else None
    return verdict.model_copy(
        update={
            "cited_fact_ids": valid_facts,
            "cited_document_ids": derived_docs,
            "verbatim_quote_verified": bool(claimed_quote),
            "pivot_to_learn_cancer_id": pivot_item.cancer_id if pivot_item else verdict.pivot_to_learn_cancer_id,
            "pivot_to_learn_category_slug": pivot_item.category_slug if pivot_item else verdict.pivot_to_learn_category_slug,
        }
    )


def _verify_card(card: LearnCategoryCard, by_fact: dict[str, CancerInfoEvidenceItem]) -> tuple[LearnCategoryCard, bool]:
    if card.coverage_status == "COVERAGE_GAP":
        return card.model_copy(update={"cited_fact_ids": [f for f in card.cited_fact_ids if f in by_fact]}), False
    cited = list(dict.fromkeys(card.cited_fact_ids))
    valid = [fid for fid in cited if fid in by_fact and by_fact[fid].category_slug == card.category_slug]
    if len(valid) != len(cited) or not valid:
        return (
            card.model_copy(
                update={
                    "coverage_status": "PARTIAL",
                    "cited_fact_ids": valid,
                    "ai_plain_language_explanation": (
                        "The AI explanation for this category was withheld because its citations could not be "
                        "verified. The source facts and original links are shown directly."
                    ),
                }
            ),
            True,
        )
    return card.model_copy(update={"cited_fact_ids": valid}), False


def run_stage4_verifier(
    envelope: ResultEnvelope,
    retrieved_items: list[CancerInfoEvidenceItem],
    claimed_quotes: Mapping[str, str] | None = None,
) -> ResultEnvelope:
    """SG-08: mechanically check every citation and quote against this request's retrieved items.

    ``retrieved_items`` must be the items actually supplied to the model for this request.
    ``claimed_quotes`` maps ``subclaim_id`` -> quote the model claimed was verbatim.
    Evidence items lacking Clause 3 attribution or a canonical URL are removed from display.
    Dates are passed through untouched (never fabricated).
    """
    by_fact = {item.fact_id: item for item in retrieved_items}
    known_docs = {item.document_id for item in retrieved_items}
    quotes = claimed_quotes or {}

    verdicts = [_verify_verdict(v, by_fact, known_docs, quotes.get(v.subclaim_id)) for v in envelope.atomic_claim_verdicts]
    any_downgrade = any(v.stage4_downgraded and not o.stage4_downgraded for v, o in zip(verdicts, envelope.atomic_claim_verdicts))

    cards: list[LearnCategoryCard] = []
    any_card_withheld = False
    for card in envelope.learn_category_cards:
        checked, withheld = _verify_card(card, by_fact)
        cards.append(checked)
        any_card_withheld = any_card_withheld or withheld

    displayable_items = [i for i in envelope.evidence_items if i.attribution_text.strip() and i.canonical_url.strip()]
    removed = len(envelope.evidence_items) - len(displayable_items)

    update: dict = {"atomic_claim_verdicts": verdicts, "learn_category_cards": cards, "evidence_items": displayable_items}
    notes = [envelope.limitations_and_gaps_note]
    if envelope.resolved_mode is LensMode.EVALUATE and verdicts:
        code, label = aggregate_outcome(verdicts)
        update["overall_outcome_code"], update["overall_outcome_label"] = code, label
        if any_downgrade:
            update["ai_plain_language_summary"] = deterministic_summary(verdicts)
            notes.append("Stage-4 verification downgraded one or more sub-claims to insufficient evidence.")
    if any_card_withheld:
        notes.append("Some AI category explanations were withheld because their citations could not be verified.")
    if removed:
        notes.append(f"{removed} source record(s) were hidden because they lacked required attribution or a source link.")
    update["limitations_and_gaps_note"] = " ".join(n for n in notes if n)
    return envelope.model_copy(update=update)


__all__ = ["normalize_for_quote_match", "run_stage4_verifier"]
