"""The ONE live client for Cancer Info API (single source of truth for medical content).

- SG-09: certifi-verified TLS; plain http is allowed only for loopback dev hosts.
- SG-03: ``search_evidence`` returns an explicit 4-state ``RetrievalState``. Zero matches is
  ``SEARCH_EXECUTED_NO_MATCHES`` (a coverage gap), never a contradiction.
- Ephemeral 5-minute in-memory ``TTLCache`` for successful, cacheable reads. Nothing is
  written to disk.

Stage 2 (live-verified 2 Nov 2026 against ``https://cancerinfo-api.onrender.com``):
``GET /v1/search`` (``q``, ``category``, ``country``, ``source``, ``audience``, ``page``,
``limit``) returns ``{"data": {"results": [SearchResultItem...]}, "meta": ...}`` and
``GET /v1/cancers/{cancer}/{category}`` returns ``{"data": {"cancer": ..., "records":
[ContentRecordOut...]}}`` with nested ``cancer`` / ``sources`` / ``jurisdiction`` objects.
``GET /v1/facts?ids=a,b`` (live-verified 4 Nov 2026) returns ``FactsResponseOut``
``{"data": [SearchResultItem...], "meta": ...}`` with up to 50 IDs per call.
``_coerce_record_to_evidence_item`` maps those nested shapes onto the flat
``CancerInfoEvidenceItem`` contract; flat Stage 1 dicts pass through untouched.
Truthfulness (SG-08 / Gate 2): ``observed_source_date`` stays None when absent,
``ai_processing_allowed`` is True only on an explicit reusable/cleared signal, and
``canonical_url`` / ``attribution_text`` are preserved exactly.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

import httpx
from cachetools import TTLCache
from pydantic import ValidationError

from ..config import ConfigurationError, Settings, create_verified_ssl_context, validate_api_key
from ..schemas.enums import RetrievalState
from ..schemas.envelope import CancerInfoEvidenceItem

logger = logging.getLogger("cancerlens.cancerinfo")

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
_LIST_KEYS = ("items", "results", "data", "evidence", "facts", "cancers")
_ITEM_FIELDS = frozenset(CancerInfoEvidenceItem.model_fields)
MAX_SEARCH_LIMIT = 50
MAX_FACT_IDS_PER_CALL = 50


class CancerInfoAPIError(RuntimeError):
    """Cancer Info API unreachable, errored, or returned a body that breaks the contract."""


def _extract_list(body: Any, preferred_key: str | None = None) -> list[Any]:
    if isinstance(body, list):
        return body
    if isinstance(body, dict):
        keys = ((preferred_key,) if preferred_key else ()) + _LIST_KEYS
        for key in keys:
            value = body.get(key)
            if isinstance(value, list):
                return value
    raise CancerInfoAPIError("Response body is not a list or a recognised list wrapper.")


_ELIGIBLE_LICENSES = frozenset({"eligible", "cleared", "approved", "public_domain", "public-domain"})
_BLOCKED_LICENSE_HINTS = ("restrict", "block", "quarantin", "revok", "ineligible", "denied", "embargo")


def _split_datetime(value: Any) -> tuple[str | None, str | None]:
    """Return (datetime_iso, date_iso) from a live timestamp string, else (None, None). Never raises."""
    if not isinstance(value, str) or not value.strip():
        return None, None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None, None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    normalized = parsed.astimezone(timezone.utc)
    return normalized.isoformat(), normalized.date().isoformat()


def _live_ai_allowed(primary: dict[str, Any], record: dict[str, Any], context: dict[str, Any]) -> bool:
    """Clause 6 gate: True only on an explicit reusable/cleared signal. Fail closed."""
    for holder in (record, context):
        explicit = holder.get("ai_processing_allowed")
        if isinstance(explicit, bool):
            return explicit
    licenses = [
        str(primary.get("license_status") or "").strip().lower(),
        str(primary.get("publication_status") or "").strip().lower(),
    ]
    licenses = [lic for lic in licenses if lic]
    if any(any(hint in lic for hint in _BLOCKED_LICENSE_HINTS) for lic in licenses):
        return False
    if primary.get("noncommercial_redistribution_allowed") is False:
        return False
    approved = primary.get("approved_publication_content_types")
    if isinstance(approved, list) and not approved:
        return False
    return bool(licenses) and all(lic in _ELIGIBLE_LICENSES for lic in licenses)


def _retrieval_datetimes(primary: dict[str, Any], context: dict[str, Any]) -> tuple[str, str]:
    """(retrieved_at_iso, reviewed_date_iso). retrieved falls back to the envelope's
    generated_at, then to now (our own fetch time, which is factual); reviewed falls
    back to the retrieved date. Only the *observed source* date may stay None."""
    retrieved_iso, retrieved_date = _split_datetime(primary.get("retrieved_at"))
    if retrieved_iso is None:
        retrieved_iso, retrieved_date = _split_datetime(context.get("generated_at"))
    if retrieved_iso is None or retrieved_date is None:
        now = datetime.now(timezone.utc)
        retrieved_iso, retrieved_date = now.isoformat(), now.date().isoformat()
    _reviewed_iso, reviewed_date = _split_datetime(primary.get("last_verified_at"))
    return retrieved_iso, reviewed_date or retrieved_date


def _coerce_content_record(
    record: dict[str, Any], cancer: Any, context: dict[str, Any]
) -> dict[str, Any]:
    """Map one live ContentRecordOut (+ primary source) to flat evidence fields."""
    sources = record.get("sources")
    primary = sources[0] if isinstance(sources, list) and sources and isinstance(sources[0], dict) else {}
    content = record.get("content")
    fact_id = record.get("id")
    if not isinstance(content, str) or not content.strip():
        return {}
    if not isinstance(fact_id, (str, int)) or not str(fact_id).strip():
        return {}
    fact_id = str(fact_id).strip()
    cancer = cancer if isinstance(cancer, dict) else {}
    cancer_id = str(
        cancer.get("slug") or cancer.get("id") or context.get("cancer_id") or record.get("cancer_id") or "unspecified"
    )
    category = str(record.get("category") or context.get("category") or "unspecified")
    jurisdiction = record.get("jurisdiction")
    jurisdiction_code = (
        jurisdiction.get("country") if isinstance(jurisdiction, dict) and jurisdiction.get("country") else "GLOBAL"
    )
    _observed_iso, observed_date = _split_datetime(primary.get("source_updated_at"))
    retrieved_iso, reviewed_date = _retrieval_datetimes(primary, context)
    attribution = primary.get("attribution_text")
    if not isinstance(attribution, str) or not attribution.strip():
        parts = []
        org = primary.get("organization") or primary.get("source_name") or ""
        url = primary.get("url") or ""
        if org:
            parts.append(f"Source: {org}.")
        if url:
            parts.append(str(url).strip())
        attribution = " ".join(parts)
    else:
        attribution = attribution.strip()
    source_id = str(primary.get("source_id") or "unknown")
    return {
        "fact_id": fact_id,
        "document_id": str(primary.get("document_title") or primary.get("source_id") or fact_id),
        "source_id": source_id,
        "origin_source_id": source_id,
        "organization_name": str(primary.get("organization") or primary.get("source_name") or "Unknown organization"),
        "permission_reference": primary.get("license_status") or primary.get("publication_status"),
        "source_title": str(primary.get("document_title") or primary.get("source_name") or f"{cancer_id} {category}"),
        "canonical_url": str(primary.get("url") or ""),
        "cancer_id": cancer_id,
        "subtype_id": None,
        "category_slug": category,
        "structured_fact_or_summary": content.strip(),
        "limited_verbatim_excerpt": primary.get("quote_snippet")
        if isinstance(primary.get("quote_snippet"), str)
        else None,
        "study_design_scope": str(record.get("content_type") or "unspecified").strip().lower() or "unspecified",
        "population_scope": str(record.get("audience") or "unspecified").strip().lower() or "unspecified",
        "jurisdiction_code": str(jurisdiction_code),
        "observed_source_date": observed_date,
        "retrieved_at_utc": retrieved_iso,
        "reviewed_at_date": reviewed_date,
        "attribution_text": attribution,
        "ai_processing_allowed": _live_ai_allowed(primary, record, context),
    }


def _coerce_consensus_item(
    item: dict[str, Any], cancer: Any, context: dict[str, Any]
) -> dict[str, Any]:
    """Map one live ConsensusItemOut (+ first corroborating source) to evidence fields."""
    corroborated = item.get("corroborated_by")
    primary = (
        corroborated[0]
        if isinstance(corroborated, list) and corroborated and isinstance(corroborated[0], dict)
        else {}
    )
    text = item.get("clinical_detail") or item.get("fact_key")
    fact_id = item.get("id")
    if not isinstance(text, str) or not text.strip():
        return {}
    if not isinstance(fact_id, (str, int)) or not str(fact_id).strip():
        return {}
    fact_id = str(fact_id).strip()
    cancer = cancer if isinstance(cancer, dict) else {}
    cancer_id = str(
        cancer.get("slug") or cancer.get("id") or context.get("cancer_id") or item.get("cancer_id") or "unspecified"
    )
    retrieved_iso, reviewed_date = _retrieval_datetimes(primary, context)
    attribution = primary.get("attribution_text")
    if not isinstance(attribution, str) or not attribution.strip():
        parts = []
        org = primary.get("organization") or ""
        url = primary.get("url") or ""
        if org:
            parts.append(f"Source: {org}.")
        if url:
            parts.append(str(url).strip())
        attribution = " ".join(parts)
    else:
        attribution = attribution.strip()
    source_id = str(primary.get("source_id") or "unknown")
    return {
        "fact_id": fact_id,
        "document_id": str(primary.get("document_title") or primary.get("source_id") or fact_id),
        "source_id": source_id,
        "origin_source_id": source_id,
        "organization_name": str(primary.get("organization") or "Unknown organization"),
        "permission_reference": primary.get("publication_status"),
        "source_title": str(primary.get("document_title") or f"{cancer_id} consensus"),
        "canonical_url": str(primary.get("url") or ""),
        "cancer_id": cancer_id,
        "subtype_id": None,
        "category_slug": str(context.get("category") or item.get("category") or "unspecified"),
        "structured_fact_or_summary": text.strip(),
        "limited_verbatim_excerpt": primary.get("quote") if isinstance(primary.get("quote"), str) else None,
        "study_design_scope": "consensus",
        "population_scope": "unspecified",
        "jurisdiction_code": str(primary.get("country_code") or "GLOBAL"),
        "observed_source_date": None,
        "retrieved_at_utc": retrieved_iso,
        "reviewed_at_date": reviewed_date,
        "attribution_text": attribution,
        "ai_processing_allowed": _live_ai_allowed(primary, item, context),
    }


def _coerce_search_result(item: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Map one live SearchResultItem (record or consensus branch) to evidence fields."""
    local = dict(context)
    if item.get("category"):
        local["category"] = item["category"]
    record = item.get("record")
    if isinstance(record, dict):
        return _coerce_content_record(record, item.get("cancer"), local)
    consensus = item.get("consensus_item")
    if isinstance(consensus, dict):
        return _coerce_consensus_item(consensus, item.get("cancer"), local)
    return {}


def _coerce_record_to_evidence_item(record: dict, context: dict | None = None) -> dict:
    """Map one live nested record to flat evidence fields (Stage 1 flat dicts pass through).

    ``context`` carries envelope-level hints (``generated_at``, ``cancer``, ``category``,
    ``cancer_id``). Returns {} when the record carries no mappable fact, which the
    caller counts as a rejection (same as any other contract failure).
    """
    ctx = context or {}
    if not isinstance(record, dict):
        return {}
    if "fact_id" in record and "structured_fact_or_summary" in record:
        return dict(record)
    if "match_type" in record or "record" in record or "consensus_item" in record:
        return _coerce_search_result(record, ctx)
    if "content" in record:
        cancer = ctx.get("cancer")
        return _coerce_content_record(record, cancer if isinstance(cancer, dict) else {}, ctx)
    return {}


def _extract_evidence_records(body: Any) -> tuple[list[Any], dict[str, Any]]:
    """Split a response body into (records, context).

    Live shapes: ``/v1/search`` ``data.results`` (taxonomy-only matches without a
    record/consensus branch are dropped here, so they read as a coverage gap rather
    than a contract failure), category-route ``data.records`` with ``data.cancer``
    context, and ``/v1/facts`` ``FactsResponseOut`` where ``data`` is directly the
    ``SearchResultItem`` list. Every other shape falls back to the Stage 1
    list-wrapper logic.
    """
    if isinstance(body, dict):
        data = body.get("data")
        meta = body.get("meta")
        context: dict[str, Any] = {}
        if isinstance(meta, dict) and meta.get("generated_at"):
            context["generated_at"] = meta["generated_at"]
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)], context
        if isinstance(data, dict):
            results = data.get("results")
            if isinstance(results, list):
                kept = [
                    item
                    for item in results
                    if isinstance(item, dict)
                    and (isinstance(item.get("record"), dict) or isinstance(item.get("consensus_item"), dict))
                ]
                return kept, context
            records = data.get("records")
            if isinstance(records, list):
                if isinstance(data.get("cancer"), dict):
                    context["cancer"] = data["cancer"]
                if data.get("category"):
                    context["category"] = data["category"]
                return [item for item in records if isinstance(item, dict)], context
    return _extract_list(body), {}


def _parse_items(records: list[Any], context: dict[str, Any] | None = None) -> list[CancerInfoEvidenceItem]:
    """Coerce each record (live nested or flat Stage 1) then validate. Unknown keys are
    dropped; invalid records rejected."""
    ctx = context or {}
    items: list[CancerInfoEvidenceItem] = []
    rejected = 0
    dropped_keys: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            rejected += 1
            continue
        coerced = _coerce_record_to_evidence_item(record, ctx)
        dropped_keys.update(set(coerced) - _ITEM_FIELDS)
        try:
            items.append(CancerInfoEvidenceItem.model_validate({k: v for k, v in coerced.items() if k in _ITEM_FIELDS}))
        except ValidationError:
            rejected += 1
    if dropped_keys:
        logger.info("Cancer Info API returned fields outside the contract (ignored): %s", sorted(dropped_keys))
    if rejected:
        logger.warning("Rejected %d of %d Cancer Info API records that failed the contract.", rejected, len(records))
    if records and not items:
        raise CancerInfoAPIError("No Cancer Info API record satisfied the CancerInfoEvidenceItem contract.")
    return items


def _is_cacheable(response: httpx.Response) -> bool:
    cache_control = response.headers.get("cache-control", "").lower()
    return "no-store" not in cache_control and "private" not in cache_control


_CANCER_ALIASES: tuple[tuple[str, str], ...] = (
    ("non-small cell", "lung-cancer"),
    ("small cell", "lung-cancer"),
    ("nsclc", "lung-cancer"),
    ("sclc", "lung-cancer"),
    ("lung", "lung-cancer"),
    ("breast", "breast-cancer"),
    ("her2", "breast-cancer"),
    ("tnbc", "breast-cancer"),
    ("triple-negative", "breast-cancer"),
    ("colorectal", "colorectal-cancer"),
    ("colon", "colorectal-cancer"),
    ("bowel", "colorectal-cancer"),
    ("rectal", "colorectal-cancer"),
    ("ovarian", "ovarian-cancer"),
    ("ovary", "ovarian-cancer"),
    ("pancreatic", "pancreatic-cancer"),
    ("pancreas", "pancreatic-cancer"),
    ("prostate", "prostate-cancer"),
    ("cervical", "cervical-cancer"),
    ("cervix", "cervical-cancer"),
    ("bladder", "bladder-cancer"),
    ("kidney", "kidney-cancer"),
    ("renal", "kidney-cancer"),
    ("liver", "liver-cancer"),
    ("hepatic", "liver-cancer"),
    ("stomach", "stomach-cancer"),
    ("gastric", "stomach-cancer"),
    ("thyroid", "thyroid-cancer"),
    ("vaginal", "vaginal-cancer"),
    ("uterine", "uterine-corpus-cancer"),
    ("endometrial", "uterine-corpus-cancer"),
    ("melanoma", "melanoma-of-skin"),
    ("mesothelioma", "mesothelioma"),
    ("non-hodgkin", "non-hodgkin-lymphoma"),
    ("hodgkin", "hodgkin-lymphoma"),
    ("leukemia", "leukaemia"),
    ("leukaemia", "leukaemia"),
    ("oesophageal", "oesophageal-cancer"),
    ("esophageal", "oesophageal-cancer"),
    ("brain", "brain-cns-cancer"),
    ("glioblastoma", "brain-cns-cancer"),
    ("salivary", "salivary-gland-cancer"),
    ("penile", "penile-cancer"),
    ("oral", "lip-oral-cavity-cancer"),
)

_TOPIC_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("immunotherapy", "immunotherapy"),
    ("chemotherapy", "chemotherapy"),
    ("radiation", "radiation_therapy"),
    ("targeted therapy", "targeted_therapy"),
    ("hormone therapy", "hormone_therapy"),
    ("clinical trial", "clinical_trials"),
    ("biomarker", "biomarkers"),
    ("genetic", "genetics"),
    ("brca", "genetics"),
    ("side effect", "side_effects"),
    ("supportive care", "living_with_cancer"),
    ("risk factor", "risk-factors"),
    ("screening", "screening"),
    ("symptom", "symptoms"),
    ("treatment", "treatment"),
    ("diagnos", "diagnosis"),
    ("prevent", "prevention"),
    ("prognos", "prognosis"),
    ("survival", "prognosis"),
    ("staging", "staging"),
    ("stage", "staging"),
    ("overview", "overview"),
)

_CATEGORY_DB_ALIASES: dict[str, tuple[str, ...]] = {
    "risk-factors": ("risk-factors", "risk_factors", "causes"),
    "side-effects": ("side-effects", "side_effects"),
    "supportive-care": ("supportive-care", "living_with_cancer", "follow_up"),
    "diagnosis": ("diagnosis", "diagnostic_tests"),
    "treatment": ("treatment", "chemotherapy", "immunotherapy", "targeted_therapy", "surgery", "radiation_therapy"),
}


def infer_cancer_slug(text: str | None) -> str | None:
    """Return a canonical Cancer Info API cancer slug if ``text`` names or aliases one."""
    if not text or not text.strip():
        return None
    lowered = text.lower()
    for phrase, slug in _CANCER_ALIASES:
        if re.search(rf"\b{re.escape(phrase)}", lowered):
            return slug
    return None


def infer_category_slug(text: str | None) -> str | None:
    """Return a canonical category slug if ``text`` names one explicitly."""
    if not text or not text.strip():
        return None
    lowered = text.lower()
    for phrase, cat in _TOPIC_KEYWORDS:
        if phrase in lowered:
            return cat
    return None


def strip_parenthetical_noise(text: str) -> str:
    """Strip UI display parentheticals like '(Non-Small Cell & Small Cell)' or '(HER2+ & TNBC)'."""
    cleaned = re.sub(r"\s*\([^)]*\)", "", text or "")
    return " ".join(cleaned.split()).strip()


def _is_live_search_envelope(body: Any) -> bool:
    return (
        isinstance(body, dict)
        and isinstance(body.get("data"), dict)
        and isinstance(body["data"].get("results"), list)
    )


def _build_fallback_searches(
    query: str, cancer_id: str | None, category_slug: str | None
) -> list[tuple[str, str | None]]:
    """Ordered (q, category) fallbacks when a live /v1/search substring query returns 0 records."""
    seen: set[tuple[str, str | None]] = {(query.lower(), category_slug)}
    candidates: list[tuple[str, str | None]] = []

    def add(q_val: str | None, cat_val: str | None) -> None:
        if not q_val or not q_val.strip():
            return
        norm_q = " ".join(q_val.split()).strip()
        pair = (norm_q.lower(), cat_val)
        if len(norm_q) >= 2 and pair not in seen:
            seen.add(pair)
            candidates.append((norm_q, cat_val))

    stripped = strip_parenthetical_noise(query)
    if stripped and stripped.lower() != query.lower():
        add(stripped, category_slug)

    inferred_cancer = infer_cancer_slug(query) or (
        cancer_id if cancer_id and "-" in cancer_id else infer_cancer_slug(cancer_id)
    )
    cancer_words = inferred_cancer.replace("-", " ") if inferred_cancer else None
    inferred_cat = infer_category_slug(query)

    if category_slug:
        for alt_cat in _CATEGORY_DB_ALIASES.get(category_slug, (category_slug, category_slug.replace("-", "_"))):
            if cancer_words:
                add(cancer_words, alt_cat)
            add(stripped or query, alt_cat)
    else:
        if cancer_words and inferred_cat:
            add(f"{cancer_words} {inferred_cat.replace('_', ' ').replace('-', ' ')}", inferred_cat)
            add(cancer_words, inferred_cat)
        if inferred_cat:
            add(inferred_cat.replace("_", " ").replace("-", " "), None)
        if cancer_words:
            add(cancer_words, None)

    return candidates


class CancerInfoAPIClient:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        base_url = settings.CANCER_INFO_API_BASE_URL.rstrip("/")
        parts = urlsplit(base_url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise ConfigurationError("CANCER_INFO_API_BASE_URL must be an absolute http(s) URL.")
        if parts.scheme == "http" and parts.hostname not in _LOOPBACK_HOSTS:
            raise ConfigurationError("CANCER_INFO_API_BASE_URL must use https unless it points at loopback.")

        headers = {"Accept": "application/json", "User-Agent": "CancerLens/0.2 (stage2)"}
        raw_key = settings.CANCER_INFO_API_KEY.strip()
        if raw_key:
            key = validate_api_key(raw_key, "Cancer Info API")
            headers["Authorization"] = f"Bearer {key}"
            if settings.CANCER_INFO_API_SEND_X_API_KEY:
                headers["X-API-Key"] = key

        self._settings = settings
        self._client = httpx.AsyncClient(
            base_url=base_url,
            verify=create_verified_ssl_context(),
            timeout=settings.CANCER_INFO_API_TIMEOUT_SECONDS,
            headers=headers,
            follow_redirects=False,
            transport=transport,
        )
        self._cache: TTLCache = TTLCache(maxsize=256, ttl=settings.CANCER_INFO_CACHE_TTL_SECONDS)

    async def aclose(self) -> None:
        await self._client.aclose()

    def clear_cache(self) -> None:
        self._cache.clear()

    async def _get_json(self, path: str, params: dict[str, Any]) -> tuple[Any, bool]:
        try:
            response = await self._client.get(path, params=params)
        except httpx.HTTPError as exc:
            raise CancerInfoAPIError(f"Cancer Info API request failed: {type(exc).__name__}") from exc
        if response.status_code != 200:
            raise CancerInfoAPIError(f"Cancer Info API returned HTTP {response.status_code}.")
        try:
            return response.json(), _is_cacheable(response)
        except ValueError as exc:
            raise CancerInfoAPIError("Cancer Info API returned a non-JSON body.") from exc

    @staticmethod
    def _cache_key(endpoint: str, params: dict[str, Any]) -> tuple:
        return (endpoint, tuple(sorted((k, str(v)) for k, v in params.items() if v is not None)))

    async def list_cancers(self) -> list[dict[str, Any]]:
        """25-cancer taxonomy as returned by Cancer Info API. Raises CancerInfoAPIError on failure."""
        path = self._settings.CANCER_INFO_API_CANCERS_PATH
        params = {"limit": MAX_SEARCH_LIMIT}
        key = self._cache_key(path, params)
        if key in self._cache:
            return self._cache[key]
        body, cacheable = await self._get_json(path, params)
        cancers = [entry for entry in _extract_list(body, "cancers") if isinstance(entry, dict)]
        if cacheable:
            self._cache[key] = cancers
        return cancers

    async def search_evidence(
        self,
        query: str,
        cancer_id: str | None = None,
        subtype_id: str | None = None,
        category_slug: str | None = None,
        limit: int = 12,
    ) -> tuple[RetrievalState, list[CancerInfoEvidenceItem]]:
        """SG-03 mapping: error -> TOOL_FAILED, empty 200 -> NO_MATCHES, non-empty 200 -> WITH_MATCHES."""
        path = self._settings.CANCER_INFO_API_SEARCH_PATH
        requested_limit = max(1, min(int(limit), MAX_SEARCH_LIMIT))
        clean_q = " ".join(query.split())[:500]
        params: dict[str, Any] = {
            "q": clean_q,
            "cancer_id": cancer_id,
            "subtype_id": subtype_id,
            "category_slug": category_slug,
            "category": category_slug,  # live /v1/search alias (unknown params are ignored live)
            "limit": MAX_SEARCH_LIMIT,
        }
        params = {k: v for k, v in params.items() if v not in (None, "")}
        key = self._cache_key(path, {**params, "_req_limit": requested_limit})
        if key in self._cache:
            return self._cache[key]

        target_cancer = infer_cancer_slug(clean_q) or (
            cancer_id if cancer_id and "-" in cancer_id else None
        )

        def _filter_for_target_cancer(
            parsed: list[CancerInfoEvidenceItem], is_live: bool
        ) -> list[CancerInfoEvidenceItem]:
            if not is_live or not parsed or not target_cancer:
                return parsed
            matched = [i for i in parsed if i.cancer_id == target_cancer]
            if matched:
                return matched
            if category_slug:
                return []
            return parsed

        try:
            body, cacheable = await self._get_json(path, params)
            is_live = _is_live_search_envelope(body)
            records, context = _extract_evidence_records(body)
            items = _filter_for_target_cancer(_parse_items(records, context), is_live)
            if not items and is_live:
                for fb_q, fb_cat in _build_fallback_searches(clean_q, cancer_id, category_slug):
                    fb_params: dict[str, Any] = {
                        "q": fb_q[:500],
                        "cancer_id": target_cancer or cancer_id,
                        "subtype_id": subtype_id,
                        "category_slug": fb_cat,
                        "category": fb_cat,
                        "limit": MAX_SEARCH_LIMIT,
                    }
                    fb_params = {k: v for k, v in fb_params.items() if v not in (None, "")}
                    fb_body, fb_cacheable = await self._get_json(path, fb_params)
                    cacheable = cacheable and fb_cacheable
                    fb_records, fb_ctx = _extract_evidence_records(fb_body)
                    items = _filter_for_target_cancer(
                        _parse_items(fb_records, fb_ctx), _is_live_search_envelope(fb_body)
                    )
                    if items:
                        break
        except CancerInfoAPIError as exc:
            logger.warning("search_evidence -> TOOL_FAILED (%s)", exc)
            return RetrievalState.TOOL_FAILED, []

        items = items[:requested_limit]
        result = (
            (RetrievalState.SEARCH_EXECUTED_WITH_MATCHES, items)
            if items
            else (RetrievalState.SEARCH_EXECUTED_NO_MATCHES, [])
        )
        if cacheable:
            self._cache[key] = result
        return result

    async def get_facts_by_ids(self, fact_ids: list[str]) -> list[CancerInfoEvidenceItem]:
        """Fetch specific facts (Stage-4 re-verification, double-checks). Raises CancerInfoAPIError on failure.

        Only facts Cancer Info API still returns come back; a missing ID means withdrawn or unknown.
        Live-verified 4 Nov 2026: ``GET /v1/facts?ids=a,b`` returns ``FactsResponseOut``
        (``{"data": [SearchResultItem...]}``); unknown IDs come back as an empty list.
        The path stays configurable for future API versions.
        """
        unique_ids = list(dict.fromkeys(fid.strip() for fid in fact_ids if fid and fid.strip()))
        if not unique_ids:
            return []
        if len(unique_ids) > MAX_FACT_IDS_PER_CALL:
            raise ValueError(f"At most {MAX_FACT_IDS_PER_CALL} fact_ids per call.")
        path = self._settings.CANCER_INFO_API_FACTS_PATH
        params = {"ids": ",".join(unique_ids)}
        key = self._cache_key(path, params)
        if key in self._cache:
            return self._cache[key]
        body, cacheable = await self._get_json(path, params)
        requested = set(unique_ids)
        records, context = _extract_evidence_records(body)
        items = [item for item in _parse_items(records, context) if item.fact_id in requested]
        if cacheable:
            self._cache[key] = items
        return items
