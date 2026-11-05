"""Stage 2 offline checks: guards (SEC-03/SEC-04/SG-10), extract routes,
Stage-4 verifier (SG-08/Gate 5) and the live Cancer Info API record adapter (D1).

All offline, $0.00: DNS is injected, HTTP fetches use httpx.MockTransport, and
the suite-wide socket block in conftest.py stays in force.
"""

from __future__ import annotations

import socket
import struct
import zlib

import httpx
import pytest

from app.clients.cancerinfo_client import (
    CancerInfoAPIClient,
    _coerce_record_to_evidence_item,
    _extract_evidence_records,
)
from app.guards.clinical_boundary import check_clinical_boundary
from app.guards.image_upload_guard import MAX_DIMENSION, MAX_IMAGE_BYTES, guard_image_upload
from app.guards.pii_sanitizer import sanitize_pii
from app.guards.ssrf_url_guard import guard_public_url
from app.investigator import hooks
from app.main import create_app
from app.schemas import OutcomeCode
from app.schemas.envelope import (
    AtomicClaimVerdict,
    CancerInfoEvidenceItem,
    ResultEnvelope,
    TelemetrySnapshot,
)
from app.schemas.enums import LensMode, PipelineState, RetrievalState
from app.verifiers import stage4_verifier as stage4_module

from .conftest import CancerInfoMock, MetaMock, five_d, make_item, make_settings


# ------------------------------------------------------------------ SEC-03 clinical boundary


@pytest.mark.parametrize(
    "text",
    [
        "Do I have cancer?",
        "I found a hard lump in my breast and have night sweats, what is it?",
        "Does my biopsy mean stage 3?",
        "Does my pathology report indicate cancer?",
        "Does my CT scan show a tumor?",
        "Does my MRI mean I need surgery?",
        "Does my PET scan suggest metastasis?",
        "Does my mammogram look bad?",
        "Does my PSA level mean stage 3?",
        "Should I take pembrolizumab or skip chemo?",
        "How many mg of tamoxifen should I take?",
        "Can I stop my radiation therapy early?",
        "What dose of chemo should I get?",
        "Is this mole cancerous?",
        "Does this lump look malignant?",
        "Can you interpret this scan for me?",
        "What does my blood test show?",
        "What stage am I?",
        "Is this treatment right for my aunt?",
        "Should she stop taking tamoxifen?",
    ],
)
def test_clinical_boundary_refuses_personal_questions(text):
    is_out, reason = check_clinical_boundary(text)
    assert is_out is True and isinstance(reason, str) and reason


@pytest.mark.parametrize(
    "text",
    [
        "What are the common symptoms of non-small cell lung cancer?",
        "How does immunotherapy work for breast cancer?",
        "Does eating sugar directly cause breast cancer?",
        "What is the difference between stage II and stage III colorectal cancer?",
        "I read that sugar causes breast cancer and vitamin C cures breast cancer.",
        "What are the screening options for colorectal cancer?",
        "chemo brain",
        "Tell me about mammography screening guidelines.",
    ],
)
def test_clinical_boundary_allows_general_education(text):
    assert check_clinical_boundary(text) == (False, None)


# ------------------------------------------------------------------ SG-10 PII sanitizer


@pytest.mark.parametrize(
    ("raw", "expected_fragment", "forbidden"),
    [
        ("Contact jane.doe@example.com for details", "[EMAIL]", "jane.doe@example.com"),
        ("Call +1 (555) 123-4567 today", "[PHONE]", "555"),
        ("Call 555-123-4567 today", "[PHONE]", "555-123-4567"),
        ("Call +44 20 7946 0958 today", "[PHONE]", "7946"),
        ("SSN 123-45-6789 on file", "[ID]", "123-45-6789"),
        ("MRN: ABC-12345 reviewed", "[ID]", "ABC-12345"),
        ("Patient ID 987654 noted", "[ID]", "987654"),
        ("Policy number P-998877 confirmed", "[ID]", "P-998877"),
        ("Accession ACC-2026-001 logged", "[ID]", "ACC-2026-001"),
        ("DOB: 01/02/1970 recorded", "[DOB]", "01/02/1970"),
        ("born on January 5, 1970 here", "[DOB]", "January"),
        ("My name is John Doe and I read a claim", "[REDACTED_PERSON]", "John Doe"),
        ("I am a 54-year-old female named Jane, asking", "[REDACTED_PERSON]", "Jane"),
    ],
)
def test_pii_tokens_replaced(raw, expected_fragment, forbidden):
    cleaned = sanitize_pii(raw)
    assert expected_fragment in cleaned and forbidden not in cleaned


@pytest.mark.parametrize(
    "text",
    [
        "Diagnosed in 2026 with stage II disease",
        "Trial NCT01234567 showed no benefit",
        "Non-small cell lung cancer immunotherapy options",
        "sugar causes breast cancer",
        "",
    ],
)
def test_pii_preserves_clinical_text_years_and_trial_ids(text):
    assert sanitize_pii(text) == text


# ------------------------------------------------------------------ SEC-03 image guard

_PNG_SIG = b"\x89PNG\r\n\x1a\n"


def _png_chunk(ctype: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + ctype + payload + struct.pack(">I", zlib.crc32(ctype + payload) & 0xFFFFFFFF)


def make_png(
    width: int = 8,
    height: int = 6,
    extra_chunks: tuple[tuple[bytes, bytes], ...] = (),
    tiny_idat: bool = False,
) -> bytes:
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    out = bytearray(_PNG_SIG + _png_chunk(b"IHDR", ihdr))
    for ctype, payload in extra_chunks:
        out += _png_chunk(ctype, payload)
    if tiny_idat:  # structurally valid chunk; the guard never decodes pixels
        out += _png_chunk(b"IDAT", zlib.compress(b"\x00\x01\x02"))
    else:
        row = b"\x00" + bytes([7, 8, 9]) * width
        out += _png_chunk(b"IDAT", zlib.compress(row * height))
    out += _png_chunk(b"IEND", b"")
    return bytes(out)


def make_jpeg(width: int = 16, height: int = 12, app1: bool = True, com: bool = True) -> bytes:
    out = bytearray(b"\xff\xd8")
    out += b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00" + bytes(9)
    if app1:
        exif = b"Exif\x00\x00" + bytes(20)
        out += b"\xff\xe1" + struct.pack(">H", len(exif) + 2) + exif
    out += b"\xff\xdb" + struct.pack(">H", 4) + b"\x00\x01"
    sof = bytes([8]) + struct.pack(">HH", height, width) + b"\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01"
    out += b"\xff\xc0" + struct.pack(">H", len(sof) + 2) + sof
    if com:
        out += b"\xff\xfe" + struct.pack(">H", 2 + len(b"COM-MARKER-PAYLOAD")) + b"COM-MARKER-PAYLOAD"
    out += b"\xff\xda" + struct.pack(">H", 8) + b"\x01\x01\x00\x00\x3f\x00"
    out += b"\xff\x00\x11\x22" + b"\xff\xd9"
    return bytes(out)


def _webp_file(chunks: bytes) -> bytes:
    body = b"WEBP" + chunks
    return b"RIFF" + struct.pack("<I", len(body)) + body


def make_webp_vp8x(width: int = 20, height: int = 10, exif: bool = True, xmp: bool = True) -> bytes:
    payload = bytes([0x10, 0, 0, 0]) + (width - 1).to_bytes(3, "little") + (height - 1).to_bytes(3, "little")
    chunks = b"VP8X" + struct.pack("<I", 10) + payload
    if exif:
        chunks += b"EXIF" + struct.pack("<I", 6) + b"Exif\x00\x00"
    if xmp:
        chunks += b"XMP " + struct.pack("<I", 4) + b"<x/>"
    return _webp_file(chunks)


def make_webp_vp8(width: int = 20, height: int = 10) -> bytes:
    payload = bytes([0, 0, 0]) + b"\x9d\x01\x2a" + struct.pack("<HH", width, height) + bytes(10)
    return _webp_file(b"VP8 " + struct.pack("<I", len(payload)) + payload)


def make_webp_vp8l(width: int = 20, height: int = 10) -> bytes:
    bits = ((width - 1) & 0x3FFF) | (((height - 1) & 0x3FFF) << 14)
    payload = b"\x2f" + struct.pack("<I", bits) + bytes(6)
    return _webp_file(b"VP8L" + struct.pack("<I", len(payload)) + payload + (b"\x00" if len(payload) % 2 else b""))


def test_image_guard_accepts_png_jpeg_webp():
    assert guard_image_upload(make_png(), "image/png")[:8] == _PNG_SIG
    assert guard_image_upload(make_jpeg(), "image/jpeg")[:2] == b"\xff\xd8"
    for blob in (make_webp_vp8x(), make_webp_vp8(), make_webp_vp8l()):
        assert guard_image_upload(blob, "image/webp")[:4] == b"RIFF"
    assert guard_image_upload(make_png(), None)  # content-type is optional


def test_image_guard_strips_metadata_and_stays_valid():
    jpeg = guard_image_upload(make_jpeg(), "image/jpeg")
    assert b"Exif" not in jpeg and b"COM-MARKER-PAYLOAD" not in jpeg and b"JFIF" in jpeg
    assert guard_image_upload(jpeg, "image/jpeg") == jpeg  # idempotent

    png = guard_image_upload(make_png(extra_chunks=((b"tEXt", b"Comment\x00hi"), (b"eXIf", b"\x00" * 8))), "image/png")
    assert b"tEXt" not in png and b"eXIf" not in png and b"IDAT" in png
    assert guard_image_upload(png, "image/png") == png

    webp = guard_image_upload(make_webp_vp8x(), "image/webp")
    assert b"EXIF" not in webp and b"XMP " not in webp and b"VP8X" in webp
    assert guard_image_upload(webp, "image/webp") == webp


@pytest.mark.parametrize(
    "blob",
    [
        b"",
        b"%PDF-1.4 spoofed content",
        b"MZ\x90\x00 executable renamed to png",
        b"\x89PNG....",
        _PNG_SIG + b"\x00\x00",  # truncated IHDR
        b"\xff\xd8\xff\xe0",  # truncated JPEG segment
        b"RIFF\x64\x00\x00\x00WEBP",  # RIFF size mismatch
    ],
)
def test_image_guard_rejects_bad_magic_and_truncated(blob):
    with pytest.raises(ValueError):
        guard_image_upload(blob, None)


def test_image_guard_rejects_content_type_mismatch():
    with pytest.raises(ValueError):
        guard_image_upload(make_png(), "image/jpeg")
    with pytest.raises(ValueError):
        guard_image_upload(make_png(), "application/pdf")


def test_image_guard_rejects_oversize_and_overdimension():
    with pytest.raises(ValueError):
        guard_image_upload(_PNG_SIG + bytes(MAX_IMAGE_BYTES), "image/png")
    with pytest.raises(ValueError):
        guard_image_upload(make_png(width=MAX_DIMENSION + 1, tiny_idat=True), "image/png")
    with pytest.raises(ValueError):
        guard_image_upload(make_jpeg(height=MAX_DIMENSION + 1), "image/jpeg")
    with pytest.raises(ValueError):
        guard_image_upload(make_webp_vp8x(width=MAX_DIMENSION + 1), "image/webp")
    assert guard_image_upload(make_png(width=MAX_DIMENSION, height=MAX_DIMENSION, tiny_idat=True), "image/png")


# ------------------------------------------------------------------ SEC-04 SSRF guard


def _ips(*ips: str):
    return lambda hostname: list(ips)


def _addrs(*ips: str):
    def resolve(hostname: str):
        out = []
        for ip in ips:
            family = socket.AF_INET6 if ":" in ip else socket.AF_INET
            out.append((family, socket.SOCK_STREAM, 6, "", (ip, 443)))
        return out

    return resolve


def _failing_resolver(hostname: str):
    raise socket.gaierror("no such host")


@pytest.mark.parametrize(
    ("url", "resolver"),
    [
        ("http://example.com/", None),
        ("https://example.com:8443/", None),
        ("https://user:pass@example.com/", None),
        ("https://example.com:/", None),
        ("https://localhost/", None),
        ("https://localhost:443/", None),
        ("https://foo.local/", None),
        ("https://x.internal/", None),
        ("https://127.0.0.1/", _ips("127.0.0.1")),
        ("https://[::1]/", _ips("::1")),
        ("https://example.com/", _ips("10.1.2.3")),
        ("https://example.com/", _ips("172.16.5.4")),
        ("https://example.com/", _ips("192.168.1.1")),
        ("https://example.com/", _ips("169.254.169.254")),
        ("https://example.com/", _ips("100.64.0.1")),
        ("https://example.com/", _ips("::1")),
        ("https://example.com/", _ips("fe80::1")),
        ("https://example.com/", _ips("::ffff:127.0.0.1")),
        ("https://example.com/", _ips("0.0.0.0")),
        ("https://example.com/", _ips("224.0.0.1")),
        ("https://example.com/", _ips("93.184.216.34", "10.0.0.9")),
        ("https://example.com/", _failing_resolver),
        ("https://example.com/", _ips()),
        ("", None),
        ("not a url", None),
    ],
)
def test_ssrf_guard_rejects(url, resolver):
    with pytest.raises(ValueError):
        guard_public_url(url, resolver=resolver)


@pytest.mark.parametrize("resolver", [_ips("93.184.216.34"), _addrs("93.184.216.34")])
def test_ssrf_guard_allows_public_host_both_resolver_shapes(resolver):
    assert guard_public_url("https://example.com/a?b=c#frag", resolver=resolver) == "https://example.com/a?b=c"


def test_ssrf_guard_allows_public_literals():
    assert guard_public_url("https://93.184.216.34/x", resolver=_ips("93.184.216.34"))
    assert guard_public_url("https://[2606:4700:4700::1111]/", resolver=_ips("2606:4700:4700::1111"))


# ------------------------------------------------------------------ extract routes


@pytest.fixture
def ext_api(harness_factory):
    def build(**kwargs):
        h = harness_factory(**kwargs)
        app = create_app(h.container.settings, container=h.container)
        app.state.container = h.container
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
        return h, app, client

    return build


def _host_resolver(mapping: dict[str, list[str]]):
    def resolve(hostname: str):
        if hostname not in mapping:
            raise socket.gaierror(f"blocked: {hostname}")
        return list(mapping[hostname])

    return resolve


_MOCK_HTML = """<html><head><title>Screening guide</title><style>.x{display:none}</style>
<script>alert('tracker')</script></head><body><nav>Home About Contact</nav>
<h1>Breast cancer screening saves lives</h1>
<p>Write to jane@example.com or call +1 (555) 123-4567 for the leaflet.</p>
<footer>Copyright footer</footer><noscript>enable js</noscript></body></html>"""

_PUBLIC_IP = "93.184.216.34"


async def test_extract_url_disabled_returns_501(ext_api):
    _h, _app, client = ext_api()
    r = await client.post("/api/v1/extract/url", json={"url": "https://example.com/post"})
    assert r.status_code == 501 and r.json()["error_code"] == "CAPABILITY_NOT_AVAILABLE"
    await client.aclose()


async def test_extract_url_happy_path_strips_chrome_and_scrubs_pii(ext_api):
    _h, app, client = ext_api(settings=make_settings(URL_EXTRACTION_ENABLED=True))
    app.state.url_guard_resolver = _host_resolver({"example.com": [_PUBLIC_IP]})

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "example.com"
        return httpx.Response(200, headers={"content-type": "text/html; charset=utf-8"}, text=_MOCK_HTML)

    app.state.url_fetch_transport = httpx.MockTransport(handler)
    r = await client.post("/api/v1/extract/url", json={"url": "https://example.com/post#frag"})
    assert r.status_code == 200
    body = r.json()
    assert body["requires_user_confirmation"] is True
    assert body["modality"] == "URL_EXTRACT"
    assert "Breast cancer screening saves lives" in body["extracted_text"]
    assert "[EMAIL]" in body["extracted_text"] and "jane@example.com" not in body["extracted_text"]
    assert "[PHONE]" in body["extracted_text"] and "555" not in body["extracted_text"]
    for chrome in ("alert(", "Home About Contact", "Copyright footer", "enable js", ".x{display"):
        assert chrome not in body["extracted_text"]
    assert body["warnings"] and len(body["extracted_text"]) <= 3000
    await client.aclose()


async def test_extract_url_rejects_private_target_and_redirect_to_private(ext_api):
    _h, app, client = ext_api(settings=make_settings(URL_EXTRACTION_ENABLED=True))
    app.state.url_guard_resolver = _host_resolver({"example.com": [_PUBLIC_IP], "evil.example": ["10.9.9.9"]})

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/start":
            return httpx.Response(302, headers={"location": "https://evil.example/x"})
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<p>ok</p>")

    app.state.url_fetch_transport = httpx.MockTransport(handler)
    r = await client.post("/api/v1/extract/url", json={"url": "https://example.com/start"})
    assert r.status_code == 422 and r.json()["error_code"] == "INVALID_REQUEST"
    r = await client.post("/api/v1/extract/url", json={"url": "https://evil.example/x"})
    assert r.status_code == 422
    r = await client.post("/api/v1/extract/url", json={"url": "http://example.com/"})
    assert r.status_code == 422
    await client.aclose()


async def test_extract_url_follows_public_redirect_and_caps_loops(ext_api):
    _h, app, client = ext_api(settings=make_settings(URL_EXTRACTION_ENABLED=True))
    app.state.url_guard_resolver = _host_resolver({"example.com": [_PUBLIC_IP]})

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/a":
            return httpx.Response(302, headers={"location": "/b"})
        if request.url.path == "/loop":
            return httpx.Response(302, headers={"location": "/loop"})
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<p>final page text</p>")

    app.state.url_fetch_transport = httpx.MockTransport(handler)
    r = await client.post("/api/v1/extract/url", json={"url": "https://example.com/a"})
    assert r.status_code == 200 and "final page text" in r.json()["extracted_text"]
    r = await client.post("/api/v1/extract/url", json={"url": "https://example.com/loop"})
    assert r.status_code == 422
    await client.aclose()


async def test_extract_url_rejects_non_text_content(ext_api):
    _h, app, client = ext_api(settings=make_settings(URL_EXTRACTION_ENABLED=True))
    app.state.url_guard_resolver = _host_resolver({"example.com": [_PUBLIC_IP]})
    app.state.url_fetch_transport = httpx.MockTransport(
        lambda request: httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"%PDF-binary")
    )
    r = await client.post("/api/v1/extract/url", json={"url": "https://example.com/file.pdf"})
    assert r.status_code == 422
    await client.aclose()


async def test_extract_image_valid_returns_transcribed_text(ext_api):
    h, _app, client = ext_api()
    r = await client.post("/api/v1/extract/image", files={"file": ("shot.png", make_png(), "image/png")})
    assert r.status_code == 200
    body = r.json()
    assert body["modality"] == "IMAGE_OCR"
    assert body["extracted_text"] == "The capital of France is Paris!"
    assert body["requires_user_confirmation"] is True
    payload = h.meta.payloads[0]
    assert payload["store"] is False and payload["reasoning"] == {"effort": "low"}
    content = payload["input"][0]["content"]
    assert content[0]["type"] == "input_text"
    assert content[1]["type"] == "input_image"
    assert content[1]["image_url"].startswith("data:image/png;base64,")
    await client.aclose()


async def test_extract_image_live_disabled_returns_503(ext_api):
    _h, _app, client = ext_api(settings=make_settings(LIVE_LLM_CALLS_ENABLED=False))
    r = await client.post("/api/v1/extract/image", files={"file": ("shot.png", make_png(), "image/png")})
    assert r.status_code == 503 and r.json()["error_code"] == "LIVE_LLM_CALLS_DISABLED"
    await client.aclose()


async def test_extract_image_scrubs_pii(ext_api):
    _h, _app, client = ext_api(meta=MetaMock(text="Call Jane at jane@example.com about the claim."))
    r = await client.post("/api/v1/extract/image", files={"file": ("shot.png", make_png(), "image/png")})
    assert r.status_code == 200
    assert "jane@example.com" not in r.json()["extracted_text"]
    await client.aclose()


async def test_extract_image_invalid_returns_422(ext_api):
    _h, _app, client = ext_api()
    bad = [
        ("evil.png", b"%PDF-1.4 renamed", "image/png"),
        ("huge.png", _PNG_SIG + bytes(MAX_IMAGE_BYTES), "image/png"),
        ("wide.png", make_png(width=MAX_DIMENSION + 1, tiny_idat=True), "image/png"),
    ]
    for name, blob, ctype in bad:
        r = await client.post("/api/v1/extract/image", files={"file": (name, blob, ctype)})
        assert r.status_code == 422, name
    await client.aclose()


# ------------------------------------------------------------------ SG-08 Stage-4 verifier


def _telemetry() -> TelemetrySnapshot:
    return TelemetrySnapshot(
        request_id="req_stage2",
        pipeline_state=PipelineState.DISPLAYABLE,
        retrieval_state=RetrievalState.SEARCH_EXECUTED_WITH_MATCHES,
        primary_provider="baseten_model_api",
        primary_model="m",
        total_latency_ms=3,
        hops_executed=1,
        meta_pool_spent_usd=0.0,
        meta_pool_remaining_usd=150.0,
        baseten_pool_spent_usd=0.0,
        baseten_pool_remaining_usd=100.0,
    )


def _verdict(sid="s1", code=OutcomeCode.SUPPORTED, facts=("f1",), docs=("doc-f1",)) -> AtomicClaimVerdict:
    return AtomicClaimVerdict(
        subclaim_id=sid,
        atomic_claim_text="synthetic claim",
        outcome_code=code,
        outcome_label="L",
        ai_plain_language_explanation="E",
        context_comparisons_5d=five_d(),
        cited_fact_ids=list(facts),
        cited_document_ids=list(docs),
    )


def _envelope(*, verdicts=(), items=(), mode=LensMode.EVALUATE) -> ResultEnvelope:
    return ResultEnvelope(
        request_id="req_stage2",
        resolved_mode=mode,
        pipeline_state=PipelineState.ASSESSMENT_VALIDATED,
        retrieval_state=RetrievalState.SEARCH_EXECUTED_WITH_MATCHES,
        interpreted_query_or_claim="t",
        overall_outcome_code=OutcomeCode.SUPPORTED,
        overall_outcome_label="L",
        ai_plain_language_summary="S",
        atomic_claim_verdicts=list(verdicts),
        evidence_items=list(items),
        limitations_and_gaps_note="limits.",
        telemetry=_telemetry(),
    )


def _item(fid: str = "f1", **overrides) -> CancerInfoEvidenceItem:
    return CancerInfoEvidenceItem.model_validate(make_item(fid, **overrides))


def test_stage4_downgrades_unknown_ids_and_empty_citations():
    run = hooks.run_stage4_verifier
    env = run(_envelope(verdicts=[_verdict(facts=("f1", "f999"))]), [_item("f1")])
    verdict = env.atomic_claim_verdicts[0]
    assert verdict.outcome_code is OutcomeCode.INSUFFICIENT_EVIDENCE and verdict.stage4_downgraded
    assert "f999" in (verdict.stage4_downgrade_reason or "") and verdict.cited_fact_ids == ["f1"]
    assert env.overall_outcome_code is OutcomeCode.INSUFFICIENT_EVIDENCE

    env = run(_envelope(verdicts=[_verdict(docs=("doc-nope",))]), [_item("f1")])
    assert env.atomic_claim_verdicts[0].stage4_downgraded is True

    env = run(_envelope(verdicts=[_verdict(facts=(), docs=())]), [_item("f1")])
    assert env.atomic_claim_verdicts[0].outcome_code is OutcomeCode.INSUFFICIENT_EVIDENCE

    skipped = _verdict(code=OutcomeCode.OUT_OF_SCOPE_CLINICAL, facts=(), docs=())
    env = run(_envelope(verdicts=[skipped]), [_item("f1")])
    assert env.atomic_claim_verdicts[0].stage4_downgraded is False


def test_stage4_quote_exact_smart_punctuation_verifies_paraphrase_downgrades():
    run = hooks.run_stage4_verifier
    excerpt = "Patients’ “first-line” therapy — effective."
    item = _item("f1", limited_verbatim_excerpt=excerpt)
    claimed = "Patients' \"first-line\" therapy - effective."
    env = run(_envelope(verdicts=[_verdict()]), [item], {"s1": claimed})
    assert env.atomic_claim_verdicts[0].verbatim_quote_verified is True

    env = run(_envelope(verdicts=[_verdict()]), [item], {"s1": "a completely different wording here"})
    downgraded = env.atomic_claim_verdicts[0]
    assert downgraded.stage4_downgraded is True and downgraded.verbatim_quote_verified is False

    env = run(_envelope(verdicts=[_verdict()]), [item], {"s1": "short"})
    assert env.atomic_claim_verdicts[0].stage4_downgraded is True


def test_stage4_strips_items_missing_attribution_and_preserves_none_dates():
    run = hooks.run_stage4_verifier
    good = _item("f1")
    bad_attr = _item("f2", attribution_text="  ")
    bad_url = _item("f3", canonical_url="")
    env = run(_envelope(items=[good, bad_attr, bad_url]), [good, bad_attr, bad_url])
    assert [i.fact_id for i in env.evidence_items] == ["f1"]
    assert "hidden" in env.limitations_and_gaps_note
    assert env.evidence_items[0].observed_source_date is None


def test_hooks_and_verifier_exports_are_stable():
    import inspect

    from app.guards import clinical_boundary, image_upload_guard, pii_sanitizer, ssrf_url_guard

    assert hooks.check_clinical_boundary is clinical_boundary.check_clinical_boundary
    assert hooks.sanitize_pii is pii_sanitizer.sanitize_pii
    assert hooks.guard_image_upload is image_upload_guard.guard_image_upload
    assert hooks.guard_public_url is ssrf_url_guard.guard_public_url
    assert hooks.run_stage4_verifier is stage4_module.run_stage4_verifier
    assert hooks.normalize_for_quote_match is stage4_module.normalize_for_quote_match
    params = inspect.signature(hooks.guard_public_url).parameters
    assert list(params) == ["url", "resolver"] and params["resolver"].default is None
    assert hooks.CLINICAL_REFUSAL_REASON and hooks.CapabilityNotReadyError


# ------------------------------------------------------------------ D1 live record adapter


def _live_source(**overrides):
    src = {
        "source_id": "nci-us",
        "organization": "National Cancer Institute",
        "source_name": "NCI Comprehensive Cancer Information Database",
        "url": "https://www.cancer.gov/types/breast/symptoms",
        "trust_tier": "Tier 1 - Primary Authoritative",
        "source_updated_at": "2026-09-12T06:23:36.483693Z",
        "retrieved_at": "2026-09-12T06:23:36.483694Z",
        "last_verified_at": "2026-09-12T06:23:36.483694Z",
        "license_status": "ELIGIBLE",
        "attribution_text": "Adapted from National Cancer Institute text. No NCI endorsement is implied.",
        "quote_snippet": "Symptoms include a new lump or thickening.",
        "document_title": "Breast Cancer Symptoms - NCI",
        "publication_status": "ELIGIBLE",
        "reuse_conditions": "Text/data only.",
        "commercial_redistribution_allowed": True,
        "noncommercial_redistribution_allowed": True,
        "approved_publication_content_types": ["STRUCTURED_EXTRACTION"],
        "rights_evidence_url": "https://www.cancer.gov/policies/copyright-reuse",
    }
    src.update(overrides)
    return src


def _live_record(**overrides):
    rec = {
        "id": "rec-0001",
        "category": "symptoms",
        "subcategory": None,
        "content": "Symptoms of breast cancer include a new lump or thickening in the breast or underarm.",
        "content_type": "STRUCTURED_EXTRACTION",
        "jurisdiction": {"scope": "COUNTRY", "country": "US", "region": None},
        "language": "en",
        "audience": "patient",
        "disagreement_status": "CONSISTENT",
        "disagreement_notes": None,
        "version_number": 1,
        "updated_at": "2026-09-12T06:23:36.483307Z",
        "sources": [_live_source()],
    }
    rec.update(overrides)
    return rec


def _live_cancer():
    return {
        "id": "cid-breast",
        "slug": "breast-cancer",
        "canonical_name": "Breast Cancer",
        "anatomical_site": "Breast",
        "aliases": ["Breast Carcinoma"],
    }


def _live_search_item(**overrides):
    item = {
        "match_type": "content_record",
        "score": 1.5,
        "cancer": _live_cancer(),
        "category": "symptoms",
        "snippet": "Symptoms of breast cancer include...",
        "consensus_item": None,
        "record": _live_record(),
        "matched_terms": ["breast", "cancer"],
    }
    item.update(overrides)
    return item


def _live_search_body(results):
    return {
        "data": {"query": "breast cancer", "filters_applied": {}, "results": results},
        "meta": {"api_version": "v1", "generated_at": "2026-11-02T22:00:00Z", "result_count": len(results)},
        "pagination": {"page": 1, "limit": 20, "total_records": len(results), "total_pages": 1,
                       "has_next": False, "has_prev": False},
    }


def test_coerce_flat_stage1_dicts_pass_through():
    assert _coerce_record_to_evidence_item(make_item("f1"))["fact_id"] == "f1"
    assert _coerce_record_to_evidence_item({"id": "wrong-shape"}) == {}
    assert _coerce_record_to_evidence_item(None) == {}


def test_coerce_live_content_record_maps_exactly():
    coerced = _coerce_record_to_evidence_item(_live_search_item(), {"generated_at": "2026-11-02T22:00:00Z"})
    item = CancerInfoEvidenceItem.model_validate(coerced)
    assert item.fact_id == "rec-0001"
    assert item.cancer_id == "breast-cancer" and item.category_slug == "symptoms"
    assert item.canonical_url == "https://www.cancer.gov/types/breast/symptoms"
    assert item.attribution_text.startswith("Adapted from National Cancer Institute text.")
    assert item.limited_verbatim_excerpt == "Symptoms include a new lump or thickening."
    assert item.observed_source_date is not None and item.observed_source_date.isoformat() == "2026-09-12"
    assert item.ai_processing_allowed is True
    assert item.study_design_scope == "structured_extraction"
    assert item.population_scope == "patient" and item.jurisdiction_code == "US"


@pytest.mark.parametrize(
    "source_overrides",
    [
        {"license_status": "RESTRICTED"},
        {"publication_status": "QUARANTINED"},
        {"approved_publication_content_types": []},
        {"noncommercial_redistribution_allowed": False},
    ],
)
def test_coerce_restricted_sources_forbid_ai_processing(source_overrides):
    record = _live_record(sources=[_live_source(**source_overrides)])
    assert _coerce_record_to_evidence_item(_live_search_item(record=record))["ai_processing_allowed"] is False


def test_coerce_ai_gate_defaults_and_explicit_flags():
    src = _live_source()
    del src["license_status"]
    del src["publication_status"]
    assert _coerce_record_to_evidence_item(_live_search_item(record=_live_record(sources=[src])))[
        "ai_processing_allowed"
    ] is False
    record = _live_record(sources=[src], ai_processing_allowed=True)
    assert _coerce_record_to_evidence_item(_live_search_item(record=record))["ai_processing_allowed"] is True
    record = _live_record(sources=[_live_source()], ai_processing_allowed=False)
    assert _coerce_record_to_evidence_item(_live_search_item(record=record))["ai_processing_allowed"] is False
    null_date = _live_record(sources=[_live_source(source_updated_at=None)])
    assert CancerInfoEvidenceItem.model_validate(
        _coerce_record_to_evidence_item(_live_search_item(record=null_date))
    ).observed_source_date is None


def test_coerce_consensus_item_branch():
    consensus = {
        "id": "con-7",
        "fact_key": "screening_reduces_mortality",
        "sign": "supports",
        "clinical_detail": "Screening mammography reduces breast cancer mortality in the screened population.",
        "corroboration_count": 2,
        "corroborated_by": [
            {
                "source_id": "nci-us",
                "organization": "National Cancer Institute",
                "url": "https://www.cancer.gov/types/breast/screening",
                "quote": "Screening reduces mortality.",
                "attribution_text": "NCI screening summary.",
                "document_title": "Breast Screening - NCI",
                "publication_status": "ELIGIBLE",
                "country_code": "US",
            }
        ],
    }
    item = CancerInfoEvidenceItem.model_validate(
        _coerce_record_to_evidence_item(
            _live_search_item(match_type="consensus_item", record=None, consensus_item=consensus),
            {"generated_at": "2026-11-02T22:00:00Z"},
        )
    )
    assert item.fact_id == "con-7" and item.study_design_scope == "consensus"
    assert item.ai_processing_allowed is True and item.observed_source_date is None


def test_extract_evidence_records_handles_live_and_legacy_bodies():
    taxonomy_only = _live_search_item(
        match_type="cancer", record=None, consensus_item=None, category=None, snippet=None
    )
    records, ctx = _extract_evidence_records(_live_search_body([taxonomy_only]))
    assert records == [] and ctx["generated_at"].startswith("2026-11-02")

    records, _ctx = _extract_evidence_records(_live_search_body([_live_search_item()]))
    assert len(records) == 1

    category_body = {
        "data": {"cancer": _live_cancer(), "category": "symptoms", "records": [_live_record()]},
        "meta": {"generated_at": "2026-11-02T22:00:00Z"},
    }
    records, ctx = _extract_evidence_records(category_body)
    assert len(records) == 1 and ctx["cancer"]["slug"] == "breast-cancer"
    item = CancerInfoEvidenceItem.model_validate(_coerce_record_to_evidence_item(records[0], ctx))
    assert item.cancer_id == "breast-cancer"

    records, ctx = _extract_evidence_records({"items": [make_item("f1")]})
    assert len(records) == 1 and ctx == {}


async def test_search_evidence_live_shapes_end_to_end():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_live_search_body([_live_search_item()]))

    client = CancerInfoAPIClient(make_settings(), transport=httpx.MockTransport(handler))
    state, items = await client.search_evidence("breast cancer", cancer_id="breast-cancer")
    assert state is RetrievalState.SEARCH_EXECUTED_WITH_MATCHES
    assert items[0].fact_id == "rec-0001" and items[0].cancer_id == "breast-cancer"
    await client.aclose()

    taxonomy_only = _live_search_body(
        [_live_search_item(match_type="cancer", record=None, consensus_item=None, category=None, snippet=None)]
    )
    client = CancerInfoAPIClient(
        make_settings(), transport=httpx.MockTransport(lambda request: httpx.Response(200, json=taxonomy_only))
    )
    state, items = await client.search_evidence("breast cancer")
    assert (state, items) == (RetrievalState.SEARCH_EXECUTED_NO_MATCHES, [])
    await client.aclose()


async def test_search_evidence_sends_live_and_legacy_params():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"items": []})

    client = CancerInfoAPIClient(make_settings(), transport=httpx.MockTransport(handler))
    await client.search_evidence("q", cancer_id="breast", category_slug="symptoms")
    assert seen[0].url.path == "/v1/search"
    assert seen[0].url.params["q"] == "q"
    assert seen[0].url.params["cancer_id"] == "breast"
    assert seen[0].url.params["category"] == "symptoms"
    await client.aclose()


def test_stage2_config_defaults():
    from app.config import Settings

    settings = Settings(_env_file=None)
    assert settings.CANCER_INFO_API_BASE_URL == "https://cancerinfo-api.onrender.com"
    assert settings.CANCER_INFO_API_TIMEOUT_SECONDS == 45.0
    assert settings.CANCER_INFO_API_SEARCH_PATH == "/v1/search"
    assert settings.CORS_ALLOWED_ORIGINS == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]
    assert settings.URL_EXTRACTION_ENABLED is False
    assert settings.LIVE_LLM_CALLS_ENABLED is False


def test_stage2_config_blank_prices_mean_unset(monkeypatch):
    """Fresh-clone flow: blank `KEY=` lines (as shipped in .env.example) load as None."""
    from app.config import Settings

    for name in (
        "META_PRICE_INPUT_PER_MTOK_USD",
        "META_PRICE_OUTPUT_PER_MTOK_USD",
        "META_PRICE_CACHED_INPUT_PER_MTOK_USD",
        "BASETEN_PRICE_INPUT_PER_MTOK_USD",
        "BASETEN_PRICE_CACHED_INPUT_PER_MTOK_USD",
        "BASETEN_PRICE_OUTPUT_PER_MTOK_USD",
    ):
        monkeypatch.setenv(name, "")
    settings = Settings(_env_file=None)
    assert settings.META_PRICE_INPUT_PER_MTOK_USD is None
    assert settings.META_PRICE_OUTPUT_PER_MTOK_USD is None
    assert settings.META_PRICE_CACHED_INPUT_PER_MTOK_USD is None
    assert settings.BASETEN_PRICE_INPUT_PER_MTOK_USD is None
    assert settings.BASETEN_PRICE_CACHED_INPUT_PER_MTOK_USD is None
    assert settings.BASETEN_PRICE_OUTPUT_PER_MTOK_USD is None


# ---------------------------------------- by-ID outage fallback (live /v1/facts verified 4 Nov 2026)


async def test_saved_result_read_falls_back_when_by_id_lookup_fails(ext_api):
    ci = CancerInfoMock(search_items=[make_item("f1")], facts={"f1": make_item("f1")})
    h, app, client = ext_api(cancer_info=ci)
    env = (await client.post("/api/v1/evaluate", json={"claim_text": "sugar causes breast cancer"})).json()
    created = await client.post("/api/v1/saved-results", json={"result_envelope": env})
    assert created.status_code == 201
    sid, token = created.json()["saved_result_id"], created.json()["capability_token"]
    ci.fail_status = 503  # upstream by-ID lookup outage (transient; endpoint itself is live)
    h.container.cancer_info.clear_cache()
    view = await client.get(f"/api/v1/saved-results/{sid}", headers={"X-Capability-Token": token})
    assert view.status_code == 200
    body = view.json()
    assert body["revalidated_against_cancer_info_api"] is False
    assert "unavailable" in body["revalidation_note"].lower()
    assert body["result_envelope"]["evidence_items"] == []  # stored snapshot, nothing invented
    ci.fail_status = None  # outage over: the saved result was kept, revalidation resumes
    h.container.cancer_info.clear_cache()
    recovered = await client.get(f"/api/v1/saved-results/{sid}", headers={"X-Capability-Token": token})
    assert recovered.status_code == 200
    assert recovered.json()["revalidated_against_cancer_info_api"] is True
    await client.aclose()


async def test_double_check_labels_by_id_outage(ext_api):
    ci = CancerInfoMock(facts={"f1": make_item("f1")}, fail_status=503)
    h, app, client = ext_api(cancer_info=ci)
    r = await client.post("/api/v1/evaluate/double-check", json={
        "request_id": "req_x", "claim_text": "sugar causes breast cancer", "cited_fact_ids": ["f1"],
        "primary_outcome_code": "SUPPORTED"})
    assert r.status_code == 503 and r.json()["error_code"] == "CANCER_INFO_API_UNAVAILABLE"
    assert "double-check is unavailable" in r.json()["message"]
    assert "original result stands" in r.json()["message"]
    await client.aclose()
