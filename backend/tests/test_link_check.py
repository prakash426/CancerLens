"""Tests for source-link verification (dead outbound links render unlinked, never dropped).

Only definitive death signals (redirect loops, DNS/connect failures, 404/410)
hide a hyperlink. Everything ambiguous keeps the link visible. All fetching
runs on httpx.MockTransport; the shared harness resolves every synthetic URL.
"""

from __future__ import annotations

import httpx
import pytest

from app.db.operational_store import OperationalStore
from app.guards.link_check import verify_source_links
from app.investigator.common import apply_link_verdicts
from app.main import create_app

from .conftest import make_item


def _public_resolver(hostname: str) -> list[str]:
    return ["93.184.216.34"]


def _status_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response({"ok": 200, "missing": 404, "gone": 410, "error": 500}.get(request.url.path.strip("/"), 403))


async def test_status_verdicts_only_bury_404_and_410():
    verdicts = await verify_source_links(
        [f"https://example.org/{slug}" for slug in ("ok", "missing", "gone", "error", "forbidden")],
        transport=httpx.MockTransport(_status_handler),
        resolver=_public_resolver,
    )
    assert verdicts == {
        "https://example.org/ok": True,
        "https://example.org/missing": False,
        "https://example.org/gone": False,
        "https://example.org/error": True,  # transient 5xx: benefit of the doubt
        "https://example.org/forbidden": True,  # bot-wall 403: benefit of the doubt
    }


async def test_redirect_loop_is_dead():
    def loop(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": str(request.url)})

    verdicts = await verify_source_links(
        ["https://example.org/loop"],
        transport=httpx.MockTransport(loop),
        resolver=_public_resolver,
    )
    assert verdicts == {"https://example.org/loop": False}


async def test_connect_error_is_dead_but_timeout_is_alive():
    def flaky(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/down":
            raise httpx.ConnectError("refused")
        raise httpx.TimeoutException("slow", request=request)

    verdicts = await verify_source_links(
        ["https://example.org/down", "https://example.org/slow"],
        transport=httpx.MockTransport(flaky),
        resolver=_public_resolver,
    )
    assert verdicts == {"https://example.org/down": False, "https://example.org/slow": True}


async def test_unverifiable_urls_keep_links_and_are_never_fetched():
    calls: list[httpx.Request] = []

    def counting(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, text="ok")

    verdicts = await verify_source_links(
        ["http://example.org/plain", "https://blocked.example.org/x", "   "],
        transport=httpx.MockTransport(counting),
        resolver=lambda hostname: ["127.0.0.1"] if "blocked" in hostname else ["93.184.216.34"],
    )
    assert verdicts == {"http://example.org/plain": True, "https://blocked.example.org/x": True}
    assert calls == []  # guard-skipped URLs are never fetched


async def test_store_verdict_roundtrip_and_expiry():
    store = OperationalStore(":memory:")
    store.initialize()
    try:
        assert store.get_link_verdict("https://example.org/x") is None
        assert store.get_link_verdict("  ") is None
        store.set_link_verdict("https://example.org/x", False)
        assert store.get_link_verdict("https://example.org/x") is False
        store.set_link_verdict("https://example.org/x", True)
        assert store.get_link_verdict("https://example.org/x") is True
        store.conn.execute(
            "UPDATE link_verification_cache SET checked_at_utc = '2020-01-01T00:00:00Z' WHERE url = ?",
            ("https://example.org/x",),
        )
        assert store.get_link_verdict("https://example.org/x") is None  # stale verdicts expire
    finally:
        store.close()


@pytest.fixture
def link_api(harness_factory):
    def build(mock, link_handler):
        h = harness_factory(cancer_info=mock)
        h.container.link_check_transport = httpx.MockTransport(link_handler)
        app = create_app(h.container.settings, container=h.container)
        app.state.container = h.container
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
        return h, client

    return build


async def test_learn_marks_dead_links_and_caches_verdicts(link_api):
    from .conftest import CancerInfoMock

    def links(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404 if request.url.path == "/dead" else 200, text="target")

    mock = CancerInfoMock(
        search_items=[
            make_item("f-ok", cancer_id="lung-cancer", category_slug="symptoms",
                      canonical_url="https://example.org/ok"),
            make_item("f-dead", cancer_id="lung-cancer", category_slug="symptoms",
                      canonical_url="https://example.org/dead"),
        ]
    )
    h, client = link_api(mock, links)
    r = await client.post("/api/v1/learn", json={"cancer_id": "lung-cancer", "category_slug": "symptoms"})
    assert r.status_code == 200
    body = r.json()
    assert body["retrieval_state"] == "SEARCH_EXECUTED_WITH_MATCHES"
    flags = {i["canonical_url"]: i["link_ok"] for i in body["evidence_items"]}
    assert flags == {"https://example.org/ok": True, "https://example.org/dead": False}
    assert h.container.store.get_link_verdict("https://example.org/dead") is False
    await client.aclose()


async def test_apply_link_verdicts_cache_only_never_touches_network(harness_factory):
    from app.schemas.envelope import CancerInfoEvidenceItem

    h = harness_factory()
    h.container.link_check_transport = None  # would raise if any fetch were attempted
    h.container.store.set_link_verdict("https://example.org/dead", False)
    items = [
        CancerInfoEvidenceItem.model_validate(make_item("f1", canonical_url="https://example.org/dead")),
        CancerInfoEvidenceItem.model_validate(make_item("f2", canonical_url="https://example.org/new")),
    ]
    out = await apply_link_verdicts(h.container, items, check_live=False)
    assert [i.link_ok for i in out] == [False, True]
    assert all(i.link_ok for i in items)  # frozen originals untouched


async def test_apply_link_verdicts_never_raises(harness_factory, monkeypatch):
    from app.schemas.envelope import CancerInfoEvidenceItem

    h = harness_factory()
    monkeypatch.setattr(h.container.store, "get_link_verdict", lambda url: (_ for _ in ()).throw(RuntimeError("db down")))
    items = [CancerInfoEvidenceItem.model_validate(make_item("f1"))]
    assert await apply_link_verdicts(h.container, items) is items
