"""Stage 1 unit checks: config (SG-09), contracts (SG-06), store (SG-05, Gate 7), json utils (SG-02/04/05/07),
Cancer Info API client (SG-03) and provider payloads. All offline, $0.00."""

from __future__ import annotations

import json
import re
import ssl
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from app.clients.cancerinfo_client import CancerInfoAPIClient
from app.config import ConfigurationError, create_verified_ssl_context, validate_api_key
from app.db.operational_store import OPERATIONAL_TABLES, BudgetExceededError, OperationalStore
from app.providers.governance import LiveCallsDisabledError
from app.providers.json_utils import (
    IncompleteGenerationError,
    ModelOutputValidationError,
    clean_and_validate_json,
    ensure_complete_generation,
    extract_non_additive_usage,
    purge_pending_tool_prose,
)
from app.providers.meta_client import parse_responses_output
from app.schemas import EvaluateRequest, LearnRequest, LensMode, RetrievalState
from app.schemas.envelope import ContextDimensionComparison

from .conftest import META_RECEIPT_BODY, BasetenMock, CancerInfoMock, MetaMock, make_item, make_settings

APP_DIR = Path(__file__).resolve().parents[1] / "app"


# ------------------------------------------------------------------ hard rules (Section 5 items 1-3)
def test_no_fixture_client_or_gpu_model_code_in_app():
    banned = re.compile(r"FixtureCancerInfoAPIClient|\btruss\b|medcpt|deberta|torch", re.IGNORECASE)
    offenders = [str(p) for p in APP_DIR.rglob("*.py") if banned.search(p.read_text(encoding="utf-8"))]
    assert offenders == []
    clients = [p for p in APP_DIR.rglob("*.py") if re.search(r"^class \w*CancerInfo\w*Client\b", p.read_text(), re.M)]
    assert [p.name for p in clients] == ["cancerinfo_client.py"]


def test_openapi_export_has_all_routes(tmp_path):
    from scripts.export_openapi import export

    schema = json.loads(export(tmp_path / "openapi.json").read_text())
    assert schema["openapi"].startswith("3.1")
    expected = {
        "/api/v1/cancers", "/api/v1/learn", "/api/v1/evaluate", "/api/v1/evaluate/double-check",
        "/api/v1/extract/image", "/api/v1/extract/url", "/api/v1/saved-results",
        "/api/v1/saved-results/{saved_result_id}", "/api/v1/health/budget",
    }
    assert expected <= set(schema["paths"])
    envelope = schema["components"]["schemas"]["ResultEnvelope"]
    assert envelope["additionalProperties"] is False
    assert {"ai_plain_language_summary", "evidence_items", "compliance_banner"} <= set(envelope["properties"])


def test_operational_db_has_only_operational_strict_tables(tmp_path):
    store = OperationalStore(tmp_path / "cancerlens_app.db")
    store.initialize()
    assert store.list_user_tables() == OPERATIONAL_TABLES
    ddl = {r["name"]: r["sql"] for r in store.conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")}
    for table in OPERATIONAL_TABLES - {"claim_memory_fts"}:
        assert ddl[table].rstrip().endswith("STRICT"), table
    assert store.conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    store.close()


# ------------------------------------------------------------------ SG-09
@pytest.mark.parametrize("bad", ["", "   ", "echo", "your_key_here", "xxx", "TODO", "$BASETEN_API_KEY",
                                 "short_key_123", "a valid looking key with spaces inside"])
def test_validate_api_key_rejects_bad_keys(bad):
    with pytest.raises(ConfigurationError) as exc:
        validate_api_key(bad, "Baseten Model API")
    assert bad.strip() == "" or bad not in str(exc.value)  # never echo the key


def test_validate_api_key_strips_whitespace():
    assert validate_api_key("  abcdefghijklmnopqrstuvwxyz123\n", "Meta") == "abcdefghijklmnopqrstuvwxyz123"


def test_ssl_context_verifies_certificates():
    ctx = create_verified_ssl_context()
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname is True


def test_cancer_info_base_url_must_be_https_unless_loopback():
    with pytest.raises(ConfigurationError):
        CancerInfoAPIClient(make_settings(CANCER_INFO_API_BASE_URL="http://cancer-info.example.com"))


# ------------------------------------------------------------------ SG-06 contracts
def test_request_models_lock_mode():
    assert LearnRequest(cancer_id="breast").resolved_mode is LensMode.LEARN
    assert EvaluateRequest(claim_text="sugar causes cancer").resolved_mode is LensMode.EVALUATE
    with pytest.raises(ValidationError):
        LearnRequest(cancer_id="breast", resolved_mode="EVALUATE")
    with pytest.raises(ValidationError):
        EvaluateRequest(claim_text="sugar causes cancer", resolved_mode="LEARN")
    with pytest.raises(ValidationError):
        EvaluateRequest(claim_text="sugar causes cancer", unexpected_field=1)


# ------------------------------------------------------------------ SG-02 / SG-04 / SG-05 / SG-07
def test_sg02_purge_pending_tool_prose():
    assert purge_pending_tool_prose("tool_calls", [{"id": "1"}], "Premature verdict") is None
    assert purge_pending_tool_prose("stop", [{"id": "1"}], "Premature verdict") is None
    assert purge_pending_tool_prose("tool_calls", None, "Premature verdict") is None
    assert purge_pending_tool_prose("stop", [], "Final answer") == "Final answer"


def test_sg04_length_or_empty_raises():
    with pytest.raises(IncompleteGenerationError):
        ensure_complete_generation("length", None, reasoning_tokens=509)
    with pytest.raises(IncompleteGenerationError):
        ensure_complete_generation("stop", None, reasoning_tokens=221)
    with pytest.raises(IncompleteGenerationError):
        ensure_complete_generation("stop", "   ")
    assert ensure_complete_generation("stop", " ok ") == "ok"


def test_sg07_strips_markdown_fences():
    obj = {"dimension_name": "study_design", "claim_assumes": "a", "evidence_actually_shows": "b", "is_mismatch": True}
    for raw in (
        "```json\n" + json.dumps(obj) + "\n```",
        "```\n" + json.dumps(obj) + "\n```",
        "  " + json.dumps(obj) + "  ",
        "Here is the result:\n```json\n" + json.dumps(obj) + "\n```\nThanks",
    ):
        assert clean_and_validate_json(raw, ContextDimensionComparison).is_mismatch is True
    with pytest.raises(ModelOutputValidationError):
        clean_and_validate_json('```json\n{"dimension_name": "nope"}\n```', ContextDimensionComparison)
    with pytest.raises(IncompleteGenerationError):
        clean_and_validate_json(None, ContextDimensionComparison)


def test_sg05_usage_is_non_additive():
    # Baseten T2 telemetry: 199 prompt / 256 completion (221 reasoning) / 455 total
    assert extract_non_additive_usage({"prompt_tokens": 199, "completion_tokens": 256,
                                       "completion_tokens_details": {"reasoning_tokens": 221}}) == (199, 256, 221)
    # Meta 29 Oct receipt: 15 input / 261 output (245 reasoning) / 276 total
    assert extract_non_additive_usage(META_RECEIPT_BODY["usage"]) == (15, 261, 245)
    assert extract_non_additive_usage(None) == (0, 0, 0)


def test_sg05_ledger_never_adds_reasoning_tokens():
    store = OperationalStore(":memory:")
    store.initialize()
    store.record_budget_entry(request_id="r1", pipeline_stage="INPUT_PARSED", provider_name="baseten_model_api",
                              model_id="m", input_tokens=199, output_tokens=256, reasoning_tokens_subset=221,
                              finish_reason="stop", estimated_cost_usd=0.0013368, latency_ms=10)
    pool = store.get_pool_totals()["baseten_model_api"]
    assert pool["total_tokens"] == 455  # not 676
    assert pool["output_tokens"] == 256 and pool["reasoning_tokens_subset"] == 221
    with pytest.raises(Exception):
        store.record_budget_entry(request_id="r", pipeline_stage="x", provider_name="openai", model_id="m",
                                  input_tokens=1, output_tokens=1, reasoning_tokens_subset=0, finish_reason="stop",
                                  estimated_cost_usd=0, latency_ms=1)
    store.close()


def test_budget_circuit_breaker_and_reservations():
    store = OperationalStore(":memory:")
    store.initialize()
    rid = store.reserve_budget("meta_model_api", 60.0, cap_usd=115.0)
    with pytest.raises(BudgetExceededError):
        store.reserve_budget("meta_model_api", 60.0, cap_usd=115.0)  # in-flight reservation counts
    store.release_budget(rid)
    store.reserve_budget("meta_model_api", 60.0, cap_usd=115.0)
    store.close()


# ------------------------------------------------------------------ Gate 7 review gates
def test_review_gates_only_surface_approved_rows():
    store = OperationalStore(":memory:")
    store.initialize()
    mid = store.record_candidate_query_mapping(lay_phrase="Chemo brain", learned_medical_query="cancer-related cognitive impairment",
                                               cancer_id="breast", category_slug="side-effects", verified_fact_ids=["f1"])
    assert store.lookup_approved_query_mapping("chemo   brain!") is None
    store.set_query_mapping_review_status(mid, "APPROVED")
    assert store.lookup_approved_query_mapping("chemo brain")["learned_medical_query"] == "cancer-related cognitive impairment"

    cid = store.record_candidate_claim_memory(
        canonical_claim_text="sugar directly causes breast cancer", cancer_id="breast", subtype_id=None,
        category_slug="risk-factors", primary_outcome_code="CONTRADICTED", outcome_label="x", nuance_warning_note="n",
        cited_document_ids=["d1"], cited_fact_ids=["f1"], cancer_info_api_version_hash="h", pii_sanitized_verified=True)
    assert store.search_approved_similar_claims_fts("does sugar cause breast cancer", "breast") == []
    store.set_claim_memory_review_status(cid, "APPROVED")
    assert [r["claim_memory_id"] for r in store.search_approved_similar_claims_fts("sugar breast cancer", "breast")] == [cid]
    store.set_claim_memory_review_status(cid, "REJECTED")
    assert store.search_approved_similar_claims_fts("sugar breast cancer", None) == []
    assert store.search_approved_similar_claims_fts('"; DROP TABLE x; -- NEAR(', None) == []  # FTS syntax is neutralised
    with pytest.raises(ValueError):
        store.record_candidate_claim_memory(
            canonical_claim_text="unsanitized claim text here", cancer_id="breast", subtype_id=None,
            category_slug="c", primary_outcome_code="SUPPORTED", outcome_label="x", nuance_warning_note="n",
            cited_document_ids=[], cited_fact_ids=[], cancer_info_api_version_hash="h", pii_sanitized_verified=False)
    store.close()


def test_saved_results_token_and_expiry():
    store = OperationalStore(":memory:")
    store.initialize()
    sid, token, _ = store.create_saved_result(resolved_mode="LEARN", cancer_id="breast", subtype_id=None, category_slug=None,
                                              query_or_claim_summary="q", result_envelope_json="{}", cited_document_ids=[])
    assert store.get_saved_result_by_token(sid, "wrong-token-value-123") is None
    assert store.get_saved_result_by_token(sid, token)["is_public"] == 0
    raw = store.conn.execute("SELECT capability_token_hash FROM saved_results").fetchone()[0]
    assert raw != token  # only the hash is stored
    store.conn.execute("UPDATE saved_results SET expires_at_utc = '2000-01-01T00:00:00Z'")
    assert store.get_saved_result_by_token(sid, token) is None
    sid2, token2, _ = store.create_saved_result(resolved_mode="EVALUATE", cancer_id=None, subtype_id=None, category_slug=None,
                                                query_or_claim_summary="q", result_envelope_json="{}", cited_document_ids=[])
    assert store.delete_saved_result(sid2, token2) and not store.delete_saved_result(sid2, token2)
    store.close()


# ------------------------------------------------------------------ SG-03 client
async def _client(mock: CancerInfoMock, **settings) -> CancerInfoAPIClient:
    return CancerInfoAPIClient(make_settings(**settings), transport=httpx.MockTransport(mock.handler))


async def test_sg03_four_state_mapping():
    mock = CancerInfoMock()
    client = await _client(mock)
    assert await client.search_evidence("anything") == (RetrievalState.SEARCH_EXECUTED_NO_MATCHES, [])
    mock.search_items = [make_item("f1")]
    client.clear_cache()
    state, items = await client.search_evidence("anything")
    assert state is RetrievalState.SEARCH_EXECUTED_WITH_MATCHES and items[0].fact_id == "f1"
    mock.fail_status = 500
    client.clear_cache()
    assert await client.search_evidence("anything") == (RetrievalState.TOOL_FAILED, [])
    await client.aclose()


async def test_sg03_transport_error_and_contract_mismatch_are_tool_failed():
    def boom(request):
        raise httpx.ConnectError("refused")

    client = CancerInfoAPIClient(make_settings(), transport=httpx.MockTransport(boom))
    assert (await client.search_evidence("q"))[0] is RetrievalState.TOOL_FAILED
    await client.aclose()
    mock = CancerInfoMock(search_items=[{"id": "wrong-shape"}])
    client = await _client(mock)
    assert (await client.search_evidence("q"))[0] is RetrievalState.TOOL_FAILED
    await client.aclose()


async def test_client_cache_auth_headers_and_extra_fields():
    mock = CancerInfoMock(search_items=[make_item("f1", new_api_field="ignored")])
    client = await _client(mock, CANCER_INFO_API_KEY="ci_test_key_abcdefghijkl", CANCER_INFO_API_SEND_X_API_KEY=True)
    first = await client.search_evidence("Sugar  risk", cancer_id="breast")
    second = await client.search_evidence("Sugar risk", cancer_id="breast")
    assert first == second and len(mock.calls) == 1  # 5-minute TTL cache hit
    request = mock.calls[0]
    assert request.headers["authorization"] == "Bearer ci_test_key_abcdefghijkl"
    assert request.headers["x-api-key"] == "ci_test_key_abcdefghijkl"
    assert request.url.params["cancer_id"] == "breast"
    await client.aclose()


async def test_get_facts_by_ids_returns_only_requested():
    mock = CancerInfoMock(facts={"f1": make_item("f1"), "f2": make_item("f2")})
    client = await _client(mock)
    items = await client.get_facts_by_ids(["f1", "missing", "f1"])
    assert [i.fact_id for i in items] == ["f1"]
    await client.aclose()


async def test_get_facts_by_ids_parses_live_facts_response_shape():
    """Live /v1/facts (verified 4 Nov 2026) returns FactsResponseOut: {"data":
    [SearchResultItem...], "meta": {"generated_at": ...}}. The client must map the
    nested record branch and keep the envelope generated_at as retrieved_at_utc."""
    body = {
        "data": [{
            "match_type": "content_record",
            "category": "symptoms",
            "cancer": {"slug": "ovarian-cancer", "canonical_name": "Ovarian cancer"},
            "record": {
                "id": "8e88ae54-5b2f-5272-8c91-b0a8906868c2",
                "category": "symptoms",
                "content": "Synthetic symptom fact used only for offline tests.",
                "audience": "patient",
                "content_type": "reviewed_excerpt",
                "sources": [{
                    "source_id": "test-source",
                    "organization": "Synthetic Test Organization",
                    "url": "https://example.org/source/symptoms",
                    "license_status": "eligible",
                }],
            },
        }],
        "meta": {"generated_at": "2026-11-04T10:00:00Z"},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/facts"
        return httpx.Response(200, json=body)

    client = CancerInfoAPIClient(make_settings(), transport=httpx.MockTransport(handler))
    items = await client.get_facts_by_ids(["8e88ae54-5b2f-5272-8c91-b0a8906868c2"])
    assert [i.fact_id for i in items] == ["8e88ae54-5b2f-5272-8c91-b0a8906868c2"]
    assert items[0].cancer_id == "ovarian-cancer"
    assert items[0].retrieved_at_utc == datetime(2026, 11, 4, 10, 0, 0, tzinfo=timezone.utc)
    await client.aclose()


# ------------------------------------------------------------------ provider payloads
async def test_baseten_payload_and_t1_length_rejection(harness_factory):
    h = harness_factory(baseten=BasetenMock(normalize_finish_reason="length"))
    with pytest.raises(IncompleteGenerationError):
        await h.container.baseten.normalize_and_split_claims("I saw a post", request_id="r1")
    payload = h.baseten.payloads[0]
    assert payload["model"] == "meta-models/muse-spark-open-1026"
    assert payload["reasoning_effort"] == "low" and payload["max_tokens"] == 1024
    ledger = h.container.store.get_pool_totals()["baseten_model_api"]
    assert ledger["calls"] == 1 and ledger["total_tokens"] == 189 + 512  # usage still billed


async def test_baseten_t4_tool_call_prose_is_purged(harness_factory):
    h = harness_factory()
    turn = await h.container.baseten._chat(
        request_id="r", pipeline_stage="t", messages=[{"role": "user", "content": "x"}], max_tokens=2048,
        tools=[{"type": "function", "function": {"name": "search_admitted_evidence", "parameters": {}}}],
        tool_choice="required")
    assert turn.content is None and turn.finish_reason == "tool_calls"
    planned = await h.container.baseten.plan_evidence_search_tool_call(["c"], "breast cancer", 0, request_id="r")
    assert planned[0].search_query == "sugar consumption breast cancer risk"
    assert h.baseten.payloads[-1]["tool_choice"] == "required"


async def test_meta_payload_store_false_and_receipt_parsing(harness_factory):
    h = harness_factory()
    result = await h.container.meta.generate_text(request_id="r", pipeline_stage="s", instructions="i", input_text="q")
    assert result.text == "The capital of France is Paris!"
    payload = h.meta.payloads[0]
    assert payload["store"] is False and payload["reasoning"] == {"effort": "low"}
    assert payload["model"] == "muse-spark-1.3" and payload["max_output_tokens"] >= 1024
    pool = h.container.store.get_pool_totals()["meta_model_api"]
    assert pool["total_tokens"] == 276 and abs(pool["spent_usd"] - (15 * 1.0 + 261 * 4.0) / 1e6) < 1e-12
    assert parse_responses_output({"output": [{"type": "function_call", "id": "x"}]}) == (None, [{"type": "function_call", "id": "x"}])


async def test_live_switch_off_blocks_before_network(harness_factory):
    h = harness_factory(settings=make_settings(LIVE_LLM_CALLS_ENABLED=False))
    with pytest.raises(LiveCallsDisabledError):
        await h.container.meta.generate_text(request_id="r", pipeline_stage="s", instructions="i", input_text="q")
    with pytest.raises(LiveCallsDisabledError):
        await h.container.baseten.normalize_and_split_claims("x", request_id="r")
    assert h.meta.payloads == [] and h.baseten.payloads == []


async def test_meta_refuses_without_verified_pricing(harness_factory):
    h = harness_factory(settings=make_settings(META_PRICE_INPUT_PER_MTOK_USD=None))
    with pytest.raises(ConfigurationError):
        await h.container.meta.generate_text(request_id="r", pipeline_stage="s", instructions="i", input_text="q")
    assert h.meta.payloads == []


async def test_meta_rejects_placeholder_key(harness_factory):
    h = harness_factory(settings=make_settings(META_API_KEY="echo"))
    with pytest.raises(ConfigurationError):
        await h.container.meta.generate_text(request_id="r", pipeline_stage="s", instructions="i", input_text="q")
    assert h.meta.payloads == []


# ------------------------------------------------------------------ cached-input pricing & voice removal (1 Nov)
def test_cached_input_tokens_billed_at_cached_rate():
    from app.db.operational_store import compute_non_additive_cost_usd
    from app.providers.json_utils import extract_cached_input_tokens

    usage = {"prompt_tokens": 1000, "completion_tokens": 100, "prompt_tokens_details": {"cached_tokens": 800}}
    assert extract_cached_input_tokens(usage) == 800
    assert extract_cached_input_tokens(META_RECEIPT_BODY["usage"]) == 0
    cost = compute_non_additive_cost_usd(1000, 100, 1.25, 4.25, 800, 0.15)
    assert abs(cost - (200 * 1.25 + 800 * 0.15 + 100 * 4.25) / 1e6) < 1e-15
    # No cached rate configured: cached tokens are billed at the full input rate (conservative)
    assert compute_non_additive_cost_usd(1000, 100, 1.0, 4.0, 800, None) == (1000 * 1.0 + 100 * 4.0) / 1e6


async def test_baseten_ledger_applies_cached_rate(harness_factory):
    def handler(request):
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {
            "content": '{"intent":"claim_verification","cancer_topic":"breast cancer","claims":["c one"]}'}}],
            "usage": {"prompt_tokens": 1000, "completion_tokens": 100,
                      "prompt_tokens_details": {"cached_tokens": 800}}})

    h = harness_factory()
    h.container.baseten._client._transport = httpx.MockTransport(handler)
    await h.container.baseten.normalize_and_split_claims("c one", request_id="r")
    spent = h.container.store.get_pool_totals()["baseten_model_api"]["spent_usd"]
    assert abs(spent - (200 * 1.25 + 800 * 0.15 + 100 * 4.25) / 1e6) < 1e-12


def test_voice_input_removed_from_contract():
    from app.schemas import InputModality

    assert "VOICE_TRANSCRIPT" not in {m.value for m in InputModality}
    with pytest.raises(ValidationError):
        EvaluateRequest(claim_text="some claim", source_modality="VOICE_TRANSCRIPT")


def test_meta_parser_drops_commentary_and_failed_status():
    from app.providers.meta_client import _finish_reason_from_status

    body = {"status": "completed", "output": [
        {"type": "message", "phase": "commentary", "content": [{"type": "output_text", "text": "Searching sources..."}]},
        {"type": "message", "content": [{"type": "output_text", "text": "Final answer."}]},
    ]}
    assert parse_responses_output(body) == ("Final answer.", [])
    assert _finish_reason_from_status({"status": "failed"}) == "status_failed"
    assert _finish_reason_from_status({"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}}) == "length"


async def test_meta_failed_status_is_provider_error(harness_factory):
    from app.providers.governance import ProviderError

    def handler(request):
        return httpx.Response(200, json={"status": "failed", "error": None, "output": [], "usage": {
            "input_tokens": 10, "output_tokens": 0}})

    h = harness_factory()
    h.container.meta._client._transport = httpx.MockTransport(handler)
    with pytest.raises(ProviderError):
        await h.container.meta.generate_text(request_id="r", pipeline_stage="s", instructions="i", input_text="q")
    assert h.container.store.get_pool_totals()["meta_model_api"]["calls"] == 1  # still logged in the ledger
