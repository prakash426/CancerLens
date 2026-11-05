"""Offline test harness ($0.00): every HTTP call goes to an httpx.MockTransport; real sockets are blocked.

The evidence records below are SYNTHETIC test data, not medical content, and live only in tests/.
They are served through a mocked HTTP transport to the single real CancerInfoAPIClient.
"""

from __future__ import annotations

import json
import socket
from dataclasses import dataclass, field
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from app.clients.cancerinfo_client import CancerInfoAPIClient
from app.config import Settings
from app.db.operational_store import OperationalStore
from app.investigator.common import ServiceContainer
from app.providers.baseten_client import BasetenClaimVerifierClient
from app.providers.meta_client import MetaMuseClient

FAKE_META_KEY = "meta_test_key_" + "x7" * 10
FAKE_BASETEN_KEY = "bt_test_key_" + "q9" * 10


@pytest.fixture(autouse=True)
def _block_real_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise RuntimeError("Real network access is disabled in the offline test suite ($0.00 rule).")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def make_item(fact_id: str, **overrides: Any) -> dict[str, Any]:
    record = {
        "fact_id": fact_id,
        "document_id": f"doc-{fact_id}",
        "source_id": "test_source",
        "origin_source_id": "test_origin",
        "organization_name": "Synthetic Test Organization",
        "permission_reference": "TEST-PERMISSION-0001",
        "source_title": f"Synthetic source for {fact_id}",
        "canonical_url": f"https://example.org/source/{fact_id}",
        "cancer_id": "breast",
        "subtype_id": None,
        "category_slug": "risk-factors",
        "structured_fact_or_summary": f"Synthetic structured fact {fact_id} used only for offline tests.",
        "limited_verbatim_excerpt": f"Synthetic verbatim excerpt for {fact_id} used only in tests.",
        "study_design_scope": "guideline",
        "population_scope": "human_adult_general",
        "jurisdiction_code": "INTL",
        "observed_source_date": None,
        "retrieved_at_utc": "2026-11-01T06:00:00Z",
        "reviewed_at_date": "2026-10-30",
        "attribution_text": "Synthetic attribution text. Not endorsed by any organization.",
        "ai_processing_allowed": True,
    }
    record.update(overrides)
    return record


@dataclass
class CancerInfoMock:
    search_items: list[dict] = field(default_factory=list)
    facts: dict[str, dict] = field(default_factory=dict)
    cancers: list[dict] = field(default_factory=lambda: [{"cancer_id": "breast", "name": "Breast cancer"}])
    fail_status: int | None = None
    calls: list[httpx.Request] = field(default_factory=list)

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        if self.fail_status:
            return httpx.Response(self.fail_status, json={"error": "synthetic"})
        if request.url.path in ("/v1/evidence/search", "/v1/search"):
            # Stage 2 default is /v1/search (live-verified); the legacy path stays
            # served so the Stage 1 suite passes byte-identical against either default.
            return httpx.Response(200, json={"items": self.search_items})
        if request.url.path == "/v1/facts":
            ids = request.url.params.get("ids", "").split(",")
            return httpx.Response(200, json={"items": [self.facts[i] for i in ids if i in self.facts]})
        if request.url.path == "/v1/cancers":
            return httpx.Response(200, json={"cancers": self.cancers})
        return httpx.Response(404)


def chat_body(content: str | None, finish_reason: str = "stop", tool_calls: list | None = None,
              usage: dict | None = None) -> dict:
    message: dict[str, Any] = {"role": "assistant", "content": content, "reasoning_content": "SECRET-REASONING"}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return {
        "id": "chatcmpl-test",
        "choices": [{"index": 0, "finish_reason": finish_reason, "message": message}],
        "usage": usage or {"prompt_tokens": 199, "completion_tokens": 256, "total_tokens": 455,
                           "completion_tokens_details": {"reasoning_tokens": 221}},
    }


def fenced(obj: Any) -> str:
    return "```json\n" + json.dumps(obj) + "\n```"


def five_d(mismatch_dim: str | None = None) -> list[dict]:
    return [
        {"dimension_name": d, "claim_assumes": f"claim view of {d}", "evidence_actually_shows": f"record view of {d}",
         "is_mismatch": d == mismatch_dim}
        for d in ("cancer_and_subtype", "population_and_stage", "study_design", "endpoint_measured", "caveat_or_dose")
    ]


@dataclass
class BasetenMock:
    """Scripted Baseten responses keyed by turn type. Reproduces T4 (prose + tool call) and T5 (fences)."""

    claims: list[str] = field(default_factory=lambda: ["sugar causes breast cancer"])
    intent: str = "claim_verification"
    verify_payload: dict | None = None
    tool_query: str = "sugar consumption breast cancer risk"
    plan_hops_with_calls: int = 3
    normalize_finish_reason: str = "stop"
    payloads: list[dict] = field(default_factory=list)

    def handler(self, request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        self.payloads.append(payload)
        if payload.get("tools"):
            hop = sum(1 for p in self.payloads if p.get("tools")) - 1
            if hop >= self.plan_hops_with_calls:
                return httpx.Response(200, json=chat_body("I think we are done.", "stop"))
            call = {"id": f"call_{hop}", "type": "function", "function": {
                "name": "search_admitted_evidence",
                "arguments": json.dumps({"cancer_topic": "breast cancer", "search_query": self.tool_query}),
            }}
            return httpx.Response(200, json=chat_body(
                "Premature verdict: no rights-admitted passages were returned, so the claim is false.",
                "tool_calls", [call], {"prompt_tokens": 718, "completion_tokens": 768,
                                       "completion_tokens_details": {"reasoning_tokens": 318}},
            ))
        name = (payload.get("response_format") or {}).get("json_schema", {}).get("name")
        if name == "normalized_claims":
            if self.normalize_finish_reason == "length":
                return httpx.Response(200, json=chat_body(None, "length", usage={
                    "prompt_tokens": 189, "completion_tokens": 512, "completion_tokens_details": {"reasoning_tokens": 509}}))
            return httpx.Response(200, json=chat_body(fenced(
                {"intent": self.intent, "cancer_topic": "breast cancer", "claims": self.claims})))
        if name == "claim_verification":
            body = self.verify_payload or {
                "overall_summary": "AI summary of the synthetic records.",
                "verdicts": [{
                    "subclaim_index": 1, "outcome_code": "SUPPORTED",
                    "ai_plain_language_explanation": "AI explanation grounded in synthetic fact f1.",
                    "context_comparisons_5d": five_d("population_and_stage"),
                    "cited_fact_ids": ["f1"], "cited_document_ids": ["doc-f1"], "quoted_excerpt": None,
                }],
            }
            return httpx.Response(200, json=chat_body(fenced(body), usage={
                "prompt_tokens": 328, "completion_tokens": 119, "completion_tokens_details": {"reasoning_tokens": 76}}))
        return httpx.Response(400, json={"error": "unexpected request in test"})

    def count(self, kind: str) -> int:
        if kind == "plan":
            return sum(1 for p in self.payloads if p.get("tools"))
        return sum(1 for p in self.payloads
                   if (p.get("response_format") or {}).get("json_schema", {}).get("name") == kind)


META_RECEIPT_BODY = {
    "id": "resp_6ae2e2f2c758d7404e6a40f0", "object": "response", "status": "completed", "model": "muse-spark-1.3",
    "error": None, "incomplete_details": None,
    "output": [
        {"type": "reasoning", "id": "rs_x", "summary": [], "status": "completed"},
        {"type": "message", "id": "msg_x", "role": "assistant", "status": "completed",
         "content": [{"type": "output_text", "text": "The capital of France is Paris!", "annotations": [], "logprobs": []}]},
    ],
    "usage": {"input_tokens": 15, "input_tokens_details": {"cached_tokens": 0}, "output_tokens": 261,
              "output_tokens_details": {"reasoning_tokens": 245}, "total_tokens": 276},
    "store": False,
}


@dataclass
class MetaMock:
    text: str | None = None
    payloads: list[dict] = field(default_factory=list)

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.payloads.append(json.loads(request.content))
        body = json.loads(json.dumps(META_RECEIPT_BODY))
        if self.text is not None:
            body["output"][1]["content"][0]["text"] = self.text
        return httpx.Response(200, json=body)


def make_settings(**overrides: Any) -> Settings:
    base = dict(
        _env_file=None,
        LIVE_LLM_CALLS_ENABLED=True,
        CANCER_INFO_API_BASE_URL="http://127.0.0.1:8001",
        META_API_KEY=FAKE_META_KEY,
        BASETEN_API_KEY=FAKE_BASETEN_KEY,
        META_PRICE_INPUT_PER_MTOK_USD=1.0,
        META_PRICE_OUTPUT_PER_MTOK_USD=4.0,
        OPERATIONAL_DB_PATH=":memory:",
    )
    base.update(overrides)
    return Settings(**base)


@dataclass
class Harness:
    container: ServiceContainer
    cancer_info: CancerInfoMock
    baseten: BasetenMock
    meta: MetaMock


@pytest.fixture
async def harness_factory() -> Callable[..., Harness]:
    created: list[ServiceContainer] = []

    def build(settings: Settings | None = None, cancer_info: CancerInfoMock | None = None,
              baseten: BasetenMock | None = None, meta: MetaMock | None = None) -> Harness:
        settings = settings or make_settings()
        ci, bt, mt = cancer_info or CancerInfoMock(), baseten or BasetenMock(), meta or MetaMock()
        store = OperationalStore(":memory:")
        store.initialize()
        container = ServiceContainer(
            settings=settings,
            store=store,
            cancer_info=CancerInfoAPIClient(settings, transport=httpx.MockTransport(ci.handler)),
            meta=MetaMuseClient(settings, store, transport=httpx.MockTransport(mt.handler)),
            baseten=BasetenClaimVerifierClient(settings, store, transport=httpx.MockTransport(bt.handler)),
        )
        created.append(container)
        return Harness(container, ci, bt, mt)

    yield build
    for c in created:
        for client in (c.cancer_info, c.meta, c.baseten):
            await client.aclose()
        c.store.close()
