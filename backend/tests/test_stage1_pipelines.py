"""Stage 1 pipeline and route checks (SG-01, SG-03, SG-06, SG-08, Clause 6). Mocked transports only."""

from __future__ import annotations

import json

import httpx
import pytest

from app.investigator import run_evaluate_investigator, run_learn_pipeline
from app.main import create_app
from app.schemas import (
    EvaluateRequest,
    InputModality,
    LearnRequest,
    LensMode,
    OutcomeCode,
    PipelineState,
    RetrievalState,
)

from .conftest import BasetenMock, CancerInfoMock, MetaMock, five_d, make_item, make_settings


def _verdict(index=1, code="SUPPORTED", facts=("f1",), docs=("doc-f1",), quote=None):
    return {"subclaim_index": index, "outcome_code": code, "ai_plain_language_explanation": "AI text.",
            "context_comparisons_5d": five_d(), "cited_fact_ids": list(facts), "cited_document_ids": list(docs),
            "quoted_excerpt": quote}


# ------------------------------------------------------------------ Evaluate
async def test_evaluate_happy_path_full_state_machine(harness_factory):
    h = harness_factory(cancer_info=CancerInfoMock(search_items=[make_item("f1"), make_item("f2", ai_processing_allowed=False)]))
    env = await run_evaluate_investigator(EvaluateRequest(claim_text="I read that sugar causes breast cancer"), h.container)
    assert env.resolved_mode is LensMode.EVALUATE
    assert env.pipeline_state is PipelineState.DISPLAYABLE
    assert env.retrieval_state is RetrievalState.SEARCH_EXECUTED_WITH_MATCHES
    verdict = env.atomic_claim_verdicts[0]
    assert verdict.outcome_code is OutcomeCode.SUPPORTED and not verdict.stage4_downgraded
    assert [d.dimension_name for d in verdict.context_comparisons_5d] == [
        "cancer_and_subtype", "population_and_stage", "study_design", "endpoint_measured", "caveat_or_dose"]
    assert verdict.pivot_to_learn_cancer_id == "breast" and verdict.pivot_to_learn_category_slug == "risk-factors"
    assert env.overall_outcome_code is OutcomeCode.SUPPORTED
    assert env.telemetry.primary_model == "meta-models/muse-spark-open-1026" and env.telemetry.hops_executed == 1
    # WHO Clause 6: the non-AI item is displayed but never sent to Baseten
    assert {i.fact_id for i in env.evidence_items} == {"f1", "f2"}
    verify_payload = next(p for p in h.baseten.payloads
                          if (p.get("response_format") or {}).get("json_schema", {}).get("name") == "claim_verification")
    assert '"f2"' not in verify_payload["messages"][1]["content"]
    # SG-02: the T4-style premature prose never reaches the envelope; reasoning_content never surfaces
    dumped = env.model_dump_json()
    assert "Premature verdict" not in dumped and "SECRET-REASONING" not in dumped
    # AI text and source facts stay in separate fields (Clause 6)
    assert env.ai_plain_language_summary == "AI summary of the synthetic records."
    assert env.compliance_banner.ai_author_label.endswith("Authored by CancerLens AI")


async def test_sg03_no_matches_is_insufficient_never_contradicted(harness_factory):
    h = harness_factory(
        cancer_info=CancerInfoMock(search_items=[]),
        baseten=BasetenMock(verify_payload={"overall_summary": "x", "verdicts": [_verdict(code="CONTRADICTED")]}),
    )
    env = await run_evaluate_investigator(EvaluateRequest(claim_text="sugar causes breast cancer"), h.container)
    assert env.retrieval_state is RetrievalState.SEARCH_EXECUTED_NO_MATCHES
    assert env.overall_outcome_code is OutcomeCode.INSUFFICIENT_EVIDENCE
    assert "CORPUS_COVERAGE_GAP" in env.limitations_and_gaps_note
    assert env.pipeline_state is PipelineState.DISPLAYABLE
    assert h.baseten.count("claim_verification") == 0  # the model never judged an empty evidence set
    assert h.baseten.count("plan") == 3 and env.telemetry.hops_executed == 3  # bounded <= 3 hops


async def test_tool_failure_is_not_reported_as_gap(harness_factory):
    h = harness_factory(cancer_info=CancerInfoMock(fail_status=503))
    env = await run_evaluate_investigator(EvaluateRequest(claim_text="sugar causes breast cancer"), h.container)
    assert env.retrieval_state is RetrievalState.TOOL_FAILED
    assert env.overall_outcome_code is OutcomeCode.INSUFFICIENT_EVIDENCE
    assert "CORPUS_COVERAGE_GAP" not in env.limitations_and_gaps_note
    assert h.baseten.count("plan") == 1  # no retry storm on a failing service


async def test_sg08_unknown_fact_id_is_downgraded(harness_factory):
    h = harness_factory(
        cancer_info=CancerInfoMock(search_items=[make_item("f1")]),
        baseten=BasetenMock(verify_payload={"overall_summary": "Ungrounded summary",
                                            "verdicts": [_verdict(facts=("f1", "f999"))]}),
    )
    env = await run_evaluate_investigator(EvaluateRequest(claim_text="sugar causes breast cancer"), h.container)
    verdict = env.atomic_claim_verdicts[0]
    assert verdict.outcome_code is OutcomeCode.INSUFFICIENT_EVIDENCE and verdict.stage4_downgraded
    assert "f999" in verdict.stage4_downgrade_reason and verdict.cited_fact_ids == ["f1"]
    assert env.overall_outcome_code is OutcomeCode.INSUFFICIENT_EVIDENCE
    assert "Ungrounded summary" not in env.ai_plain_language_summary


async def test_sg08_quotes_verified_or_downgraded(harness_factory):
    good = "synthetic verbatim excerpt for f1"
    h = harness_factory(cancer_info=CancerInfoMock(search_items=[make_item("f1")]),
                        baseten=BasetenMock(verify_payload={"overall_summary": "s", "verdicts": [_verdict(quote=good)]}))
    env = await run_evaluate_investigator(EvaluateRequest(claim_text="sugar causes breast cancer"), h.container)
    assert env.atomic_claim_verdicts[0].verbatim_quote_verified is True

    h2 = harness_factory(cancer_info=CancerInfoMock(search_items=[make_item("f1")]),
                         baseten=BasetenMock(verify_payload={"overall_summary": "s",
                                                             "verdicts": [_verdict(quote="an invented quotation here")]}))
    env2 = await run_evaluate_investigator(EvaluateRequest(claim_text="sugar causes breast cancer"), h2.container)
    assert env2.atomic_claim_verdicts[0].stage4_downgraded is True


async def test_compound_claims_and_missing_verdict(harness_factory):
    h = harness_factory(
        cancer_info=CancerInfoMock(search_items=[make_item("f1")]),
        baseten=BasetenMock(claims=["sugar causes breast cancer", "vitamin C cures breast cancer"],
                            verify_payload={"overall_summary": "s", "verdicts": [_verdict(1, "CONTRADICTED")]}),
    )
    env = await run_evaluate_investigator(
        EvaluateRequest(claim_text="sugar causes breast cancer and vitamin C cures breast cancer"), h.container)
    codes = [v.outcome_code for v in env.atomic_claim_verdicts]
    assert codes == [OutcomeCode.CONTRADICTED, OutcomeCode.INSUFFICIENT_EVIDENCE]
    assert env.overall_outcome_code is OutcomeCode.MIXED_OR_CONTEXT_DEPENDENT
    assert h.baseten.payloads[-1]["max_tokens"] == 2048  # multi-claim verification budget


async def test_sg06_model_intent_cannot_flip_mode(harness_factory):
    h = harness_factory(cancer_info=CancerInfoMock(search_items=[make_item("f1")]),
                        baseten=BasetenMock(intent="cancer_information"))  # T3 behaviour
    env = await run_evaluate_investigator(EvaluateRequest(claim_text="sugar causes breast cancer"), h.container)
    assert env.resolved_mode is LensMode.EVALUATE and env.atomic_claim_verdicts


async def test_clinical_question_is_refused_without_any_call(harness_factory):
    h = harness_factory()
    env = await run_evaluate_investigator(EvaluateRequest(claim_text="I found a lump, do I have cancer?"), h.container)
    assert env.overall_outcome_code is OutcomeCode.OUT_OF_SCOPE_CLINICAL
    assert env.retrieval_state is RetrievalState.TOOL_NOT_EXECUTED
    assert h.baseten.payloads == [] and h.cancer_info.calls == []


async def test_model_flagged_clinical_intent_refuses(harness_factory):
    h = harness_factory(baseten=BasetenMock(intent="personal_clinical_question"))
    env = await run_evaluate_investigator(EvaluateRequest(claim_text="Is this treatment right for my aunt"), h.container)
    assert env.overall_outcome_code is OutcomeCode.OUT_OF_SCOPE_CLINICAL and h.cancer_info.calls == []


# ------------------------------------------------------------------ Learn
async def test_learn_happy_path_meta_store_false_and_clause6(harness_factory):
    synthesis = {"overview_summary": "AI overview.", "category_explanations": [
        {"category_slug": "risk-factors", "ai_plain_language_explanation": "AI card text.", "cited_fact_ids": ["f1"]}]}
    h = harness_factory(cancer_info=CancerInfoMock(search_items=[make_item("f1"), make_item("f2", ai_processing_allowed=False)]),
                        meta=MetaMock(text="```json\n" + json.dumps(synthesis) + "\n```"))
    env = await run_learn_pipeline(LearnRequest(cancer_id="breast", category_slug="risk-factors",
                                                user_question="what raises risk?"), h.container)
    assert env.resolved_mode is LensMode.LEARN and env.pipeline_state is PipelineState.DISPLAYABLE
    assert env.ai_plain_language_summary == "AI overview."
    card = env.learn_category_cards[0]
    assert card.cited_fact_ids == ["f1"] and card.coverage_status == "PARTIAL"  # f2 not AI-processable
    payload = h.meta.payloads[0]
    assert payload["store"] is False and payload["reasoning"] == {"effort": "low"}
    assert "f2" not in payload["input"] and "f1" in payload["input"]
    assert {i.fact_id for i in env.evidence_items} == {"f1", "f2"}
    assert env.telemetry.primary_provider == "meta_model_api"


async def test_learn_no_matches_is_gap_without_llm(harness_factory):
    h = harness_factory(cancer_info=CancerInfoMock(search_items=[]))
    env = await run_learn_pipeline(LearnRequest(cancer_id="breast", category_slug="support"), h.container)
    assert env.overall_outcome_code is OutcomeCode.INSUFFICIENT_EVIDENCE
    assert env.learn_category_cards[0].coverage_status == "COVERAGE_GAP"
    assert h.meta.payloads == []


async def test_learn_degrades_to_facts_only_when_live_disabled(harness_factory):
    h = harness_factory(settings=make_settings(LIVE_LLM_CALLS_ENABLED=False),
                        cancer_info=CancerInfoMock(search_items=[make_item("f1")]))
    env = await run_learn_pipeline(LearnRequest(cancer_id="breast"), h.container)
    assert env.pipeline_state is PipelineState.DISPLAYABLE and h.meta.payloads == []
    assert "disabled" in env.ai_plain_language_summary and env.evidence_items[0].fact_id == "f1"
    assert env.telemetry.primary_provider == "none"


async def test_learn_card_with_invented_citation_is_withheld(harness_factory):
    synthesis = {"overview_summary": "AI overview.", "category_explanations": [
        {"category_slug": "risk-factors", "ai_plain_language_explanation": "Ungrounded text.", "cited_fact_ids": ["f404"]}]}
    h = harness_factory(cancer_info=CancerInfoMock(search_items=[make_item("f1")]), meta=MetaMock(text=json.dumps(synthesis)))
    env = await run_learn_pipeline(LearnRequest(cancer_id="breast"), h.container)
    card = env.learn_category_cards[0]
    assert "withheld" in card.ai_plain_language_explanation and card.cited_fact_ids == []


async def test_learn_humanizes_slug_fallback_query(harness_factory):
    # No typed question: the fallback query is built from slugs, but upstream
    # full-text search never matches hyphenated slugs ("lung-cancer overview"
    # returns 0 live; "lung cancer overview" returns the record). Humanize it.
    h = harness_factory(cancer_info=CancerInfoMock(search_items=[make_item("f1")]))
    await run_learn_pipeline(LearnRequest(cancer_id="lung-cancer", category_slug="risk-factors"), h.container)
    assert h.cancer_info.calls[-1].url.params["q"] == "lung cancer risk factors"


async def test_learn_applies_only_approved_mapping(harness_factory):
    h = harness_factory(cancer_info=CancerInfoMock(search_items=[]))
    mid = h.container.store.record_candidate_query_mapping(
        lay_phrase="chemo brain", learned_medical_query="cancer-related cognitive impairment",
        cancer_id="breast", category_slug=None, verified_fact_ids=["f1"])
    await run_learn_pipeline(LearnRequest(cancer_id="breast", user_question="chemo brain"), h.container)
    assert h.cancer_info.calls[-1].url.params["q"] == "chemo brain"
    h.container.store.set_query_mapping_review_status(mid, "APPROVED")
    env = await run_learn_pipeline(LearnRequest(cancer_id="breast", user_question="Chemo brain"), h.container)
    assert h.cancer_info.calls[-1].url.params["q"] == "cancer-related cognitive impairment"
    assert env.telemetry.learned_query_mapping_applied == "chemo brain"


# ------------------------------------------------------------------ Routes (HO-3)
@pytest.fixture
def api(harness_factory):
    def build(**kwargs):
        h = harness_factory(**kwargs)
        app = create_app(h.container.settings, container=h.container)
        app.state.container = h.container
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
        return h, client

    return build


async def test_routes_errors_and_extraction_gates(api):
    h, client = api()
    r = await client.post("/api/v1/evaluate", json={"claim_text": "sugar causes cancer", "source_modality": "IMAGE_OCR",
                                                     "user_confirmed_extraction": False})
    assert r.status_code == 422 and r.json()["error_code"] == "EXTRACTION_NOT_CONFIRMED"
    r = await client.post("/api/v1/learn", json={"cancer_id": "breast", "resolved_mode": "EVALUATE"})
    assert r.status_code == 422
    r = await client.post("/api/v1/extract/url", json={"url": "https://example.org/post"})
    assert r.status_code == 501 and r.json()["error_code"] == "CAPABILITY_NOT_AVAILABLE"
    r = await client.post("/api/v1/extract/image", files={"file": ("a.png", b"\x89PNG....", "image/png")})
    # Stage 2 (D3/SEC-03): the image guard is now live, so spoofed magic bytes
    # deterministically return 422 instead of Stage 1's blanket 501.
    assert r.status_code == 422 and r.json()["error_code"] == "INVALID_REQUEST"
    r = await client.get("/api/v1/health/budget")
    body = r.json()
    assert r.status_code == 200 and {p["provider_name"] for p in body["pools"]} == {"meta_model_api", "baseten_model_api"}
    assert all(p["spent_usd"] == 0 for p in body["pools"])
    await client.aclose()


async def test_route_budget_breaker_returns_429(api):
    h, client = api(settings=make_settings(BASETEN_BUDGET_CAP_USD=0.0001))
    r = await client.post("/api/v1/evaluate", json={"claim_text": "sugar causes breast cancer"})
    assert r.status_code == 429 and r.json()["error_code"] == "BUDGET_CIRCUIT_OPEN"
    assert h.baseten.payloads == []
    await client.aclose()


async def test_route_live_disabled_returns_503(api):
    h, client = api(settings=make_settings(LIVE_LLM_CALLS_ENABLED=False))
    r = await client.post("/api/v1/evaluate", json={"claim_text": "sugar causes breast cancer"})
    assert r.status_code == 503 and r.json()["error_code"] == "LIVE_LLM_CALLS_DISABLED"
    await client.aclose()


async def test_cancers_route_maps_failure(api):
    h, client = api(cancer_info=CancerInfoMock(fail_status=500))
    r = await client.get("/api/v1/cancers")
    assert r.status_code == 200 and r.json() == {"retrieval_state": "TOOL_FAILED", "cancers": []}
    await client.aclose()


async def test_saved_results_roundtrip_revalidation_and_revocation(api):
    ci = CancerInfoMock(search_items=[make_item("f1")], facts={"f1": make_item("f1")})
    h, client = api(cancer_info=ci)
    env = (await client.post("/api/v1/evaluate", json={"claim_text": "sugar causes breast cancer"})).json()
    created = await client.post("/api/v1/saved-results", json={"result_envelope": env})
    assert created.status_code == 201
    sid, token = created.json()["saved_result_id"], created.json()["capability_token"]
    stored = h.container.store.conn.execute("SELECT result_envelope_json FROM saved_results").fetchone()[0]
    assert json.loads(stored)["evidence_items"] == []  # no medical corpus on disk
    assert (await client.get(f"/api/v1/saved-results/{sid}", headers={"X-Capability-Token": "x" * 20})).status_code == 404
    view = await client.get(f"/api/v1/saved-results/{sid}", headers={"X-Capability-Token": token})
    assert view.status_code == 200 and view.json()["revalidated_against_cancer_info_api"] is True
    assert view.json()["result_envelope"]["evidence_items"][0]["fact_id"] == "f1"
    ci.facts.clear()  # source withdrawn upstream
    h.container.cancer_info.clear_cache()
    gone = await client.get(f"/api/v1/saved-results/{sid}", headers={"X-Capability-Token": token})
    assert gone.status_code == 410 and gone.json()["error_code"] == "SAVED_RESULT_INVALIDATED"
    await client.aclose()


async def test_double_check_route(api):
    ci = CancerInfoMock(facts={"f1": make_item("f1")})
    h, client = api(cancer_info=ci)
    r = await client.post("/api/v1/evaluate/double-check", json={
        "request_id": "req_x", "claim_text": "sugar causes breast cancer", "cited_fact_ids": ["f1"],
        "primary_outcome_code": "SUPPORTED"})
    body = r.json()
    assert r.status_code == 200 and body["is_consistent"] is True
    assert body["recheck_envelope"]["pipeline_state"] == "DISPLAYABLE"
    await client.aclose()


async def test_input_modality_text_needs_no_confirmation():
    assert EvaluateRequest(claim_text="abc def", source_modality=InputModality.TEXT, user_confirmed_extraction=False)
