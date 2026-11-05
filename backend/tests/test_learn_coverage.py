"""Tests for GET /api/v1/learn/coverage (per-category data availability probe).

The probe must predict exactly what a real /learn category click retrieves:
same query builder, same filters, same limit, so a probe warms the client
cache for the follow-up click. All upstream I/O runs on httpx.MockTransport.
"""

from __future__ import annotations

import httpx
import pytest

from app.main import create_app

from .conftest import make_item


class _CategoryMock:
    """Serve one synthetic record per covered category; empty list otherwise."""

    def __init__(self, covered: set[str], fail_status: int | None = None):
        self.covered = covered
        self.fail_status = fail_status
        self.calls: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        if self.fail_status:
            return httpx.Response(self.fail_status, json={"error": "synthetic"})
        if request.url.path == "/v1/search":
            cat = request.url.params.get("category") or request.url.params.get("category_slug")
            if cat in self.covered:
                return httpx.Response(
                    200, json={"items": [make_item(f"f-{cat}", cancer_id="lung-cancer", category_slug=cat)]}
                )
            return httpx.Response(200, json={"items": []})
        return httpx.Response(404)


@pytest.fixture
def cov_api(harness_factory):
    def build(mock):
        h = harness_factory(cancer_info=mock)
        app = create_app(h.container.settings, container=h.container)
        app.state.container = h.container
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
        return h, client

    return build


def _coverage_params(slugs):
    return [("category_slug", slug) for slug in slugs]


async def test_coverage_marks_covered_and_empty_slugs(cov_api):
    _h, client = cov_api(_CategoryMock({"symptoms"}))
    r = await client.get(
        "/api/v1/learn/coverage",
        params=[("cancer_id", "lung-cancer"), *_coverage_params(["symptoms", "prevention"])],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["cancer_id"] == "lung-cancer"
    assert body["retrieval_state"] == "SEARCH_EXECUTED_WITH_MATCHES"
    assert {c["category_slug"]: c["has_data"] for c in body["categories"]} == {
        "symptoms": True,
        "prevention": False,
    }
    await client.aclose()


async def test_coverage_all_empty_reports_no_matches(cov_api):
    _h, client = cov_api(_CategoryMock(set()))
    r = await client.get(
        "/api/v1/learn/coverage",
        params=[("cancer_id", "lung-cancer"), *_coverage_params(["symptoms", "prevention"])],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["retrieval_state"] == "SEARCH_EXECUTED_NO_MATCHES"
    assert all(c["has_data"] is False for c in body["categories"])
    await client.aclose()


async def test_coverage_upstream_outage_keeps_categories_visible(cov_api):
    """TOOL_FAILED is unknown, not empty: buttons stay (benefit of the doubt)."""
    _h, client = cov_api(_CategoryMock(set(), fail_status=500))
    r = await client.get(
        "/api/v1/learn/coverage",
        params=[("cancer_id", "lung-cancer"), *_coverage_params(["symptoms", "prevention"])],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["retrieval_state"] == "TOOL_FAILED"
    assert all(c["has_data"] is True for c in body["categories"])
    await client.aclose()


async def test_coverage_matches_real_learn_clicks_and_warms_cache(cov_api):
    """Probe verdicts agree with /learn retrieval, and the click reuses the probe cache."""
    mock = _CategoryMock({"symptoms"})
    _h, client = cov_api(mock)
    cov = await client.get(
        "/api/v1/learn/coverage",
        params=[("cancer_id", "lung-cancer"), *_coverage_params(["symptoms", "prevention"])],
    )
    assert cov.status_code == 200
    search_calls_after_probe = len(mock.calls)

    hit = await client.post(
        "/api/v1/learn", json={"cancer_id": "lung-cancer", "category_slug": "symptoms"}
    )
    assert hit.status_code == 200
    assert hit.json()["retrieval_state"] == "SEARCH_EXECUTED_WITH_MATCHES"
    assert len(mock.calls) == search_calls_after_probe  # cache hit: no new upstream call

    miss = await client.post(
        "/api/v1/learn", json={"cancer_id": "lung-cancer", "category_slug": "prevention"}
    )
    assert miss.status_code == 200
    assert miss.json()["retrieval_state"] == "SEARCH_EXECUTED_NO_MATCHES"
    await client.aclose()


async def test_coverage_requires_slugs_and_caps_fan_out(cov_api):
    _h, client = cov_api(_CategoryMock(set()))
    r = await client.get("/api/v1/learn/coverage", params=[("cancer_id", "lung-cancer")])
    assert r.status_code == 422
    r = await client.get(
        "/api/v1/learn/coverage",
        params=[("cancer_id", "lung-cancer"), *_coverage_params([f"cat-{i}" for i in range(26)])],
    )
    assert r.status_code == 422
    await client.aclose()
