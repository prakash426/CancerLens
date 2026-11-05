"""Local operational SQLite store (``cancerlens_app.db``).

Holds ONLY the six operational tables from DATABASE.md Section 3. Zero medical corpus
tables: Cancer Info API stays the single source of truth for medical content.

Safeguards implemented here:
- SG-05: ``reasoning_tokens_subset`` is stored for diagnostics and never added to
  ``output_tokens``; cost is computed from input + output tokens only.
- Dual-pool circuit breakers ($115 Meta / $65 Baseten by default) with in-flight
  reservations so concurrent requests cannot jointly overshoot a cap.
- SG-10 / TESTING Gate 7: shared claim memory and learned query mappings surface only
  rows with ``review_status = 'APPROVED'``.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
import secrets
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger("cancerlens.db")

ProviderName = Literal["meta_model_api", "baseten_model_api"]
PROVIDERS: tuple[ProviderName, ...] = ("meta_model_api", "baseten_model_api")
ReviewStatus = Literal["PENDING_REVIEW", "APPROVED", "REJECTED"]
REVIEW_STATUSES = ("PENDING_REVIEW", "APPROVED", "REJECTED")

MIN_SQLITE_FOR_STRICT = (3, 37, 0)
SPEC_SQLITE_VERSION = (3, 45, 0)

OPERATIONAL_TABLES = frozenset(
    {
        "claim_memory_library",
        "claim_memory_fts",
        "learned_query_mappings",
        "budget_ledger",
        "saved_results",
        "link_verification_cache",
    }
)
LINK_VERDICT_TTL_HOURS = 24
# SQLite-internal tables that legitimately appear alongside the operational ones.
_INTERNAL_TABLE_PREFIXES = ("sqlite_", "claim_memory_fts_")

_PRAGMAS = (
    "PRAGMA journal_mode = WAL;",
    "PRAGMA synchronous = NORMAL;",
    "PRAGMA foreign_keys = ON;",
)

# DDL copied from DATABASE.md Section 3. Only change: IF NOT EXISTS, so startup is idempotent.
_DDL = """
CREATE TABLE IF NOT EXISTS claim_memory_library (
    claim_memory_id TEXT PRIMARY KEY,
    canonical_claim_hash TEXT NOT NULL UNIQUE,
    canonical_claim_text TEXT NOT NULL CHECK (length(canonical_claim_text) BETWEEN 15 AND 600),
    cancer_id TEXT NOT NULL,
    subtype_id TEXT,
    category_slug TEXT NOT NULL,
    primary_outcome_code TEXT NOT NULL CHECK (
        primary_outcome_code IN ('SUPPORTED', 'MIXED_OR_CONTEXT_DEPENDENT', 'CONTRADICTED', 'INSUFFICIENT_EVIDENCE')
    ),
    outcome_label TEXT NOT NULL,
    nuance_warning_note TEXT NOT NULL,
    cited_document_ids_json TEXT NOT NULL DEFAULT '[]',
    cited_fact_ids_json TEXT NOT NULL DEFAULT '[]',
    cancer_info_api_version_hash TEXT NOT NULL,
    pii_sanitized_verified INTEGER NOT NULL DEFAULT 1 CHECK (pii_sanitized_verified = 1),
    review_status TEXT NOT NULL DEFAULT 'PENDING_REVIEW' CHECK (
        review_status IN ('PENDING_REVIEW', 'APPROVED', 'REJECTED')
    ),
    search_hit_count INTEGER NOT NULL DEFAULT 1,
    created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    last_searched_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
) STRICT;

CREATE VIRTUAL TABLE IF NOT EXISTS claim_memory_fts USING fts5(
    claim_memory_id UNINDEXED,
    cancer_id UNINDEXED,
    category_slug UNINDEXED,
    canonical_claim_text,
    nuance_warning_note,
    tokenize = 'porter unicode61'
);

CREATE TABLE IF NOT EXISTS learned_query_mappings (
    mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    normalized_lay_phrase TEXT NOT NULL UNIQUE,
    learned_medical_query TEXT NOT NULL,
    cancer_id TEXT NOT NULL,
    category_slug TEXT,
    verified_fact_ids_json TEXT NOT NULL CHECK (length(verified_fact_ids_json) > 4),
    review_status TEXT NOT NULL DEFAULT 'PENDING_REVIEW' CHECK (
        review_status IN ('PENDING_REVIEW', 'APPROVED', 'REJECTED')
    ),
    times_applied INTEGER NOT NULL DEFAULT 0,
    hops_saved_per_run INTEGER NOT NULL DEFAULT 1,
    created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
) STRICT;

CREATE TABLE IF NOT EXISTS budget_ledger (
    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL,
    pipeline_stage TEXT NOT NULL,
    provider_name TEXT NOT NULL CHECK (provider_name IN ('meta_model_api', 'baseten_model_api')),
    model_id TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    reasoning_tokens_subset INTEGER NOT NULL DEFAULT 0,
    finish_reason TEXT NOT NULL,
    estimated_cost_usd REAL NOT NULL,
    latency_ms INTEGER NOT NULL,
    is_live_call INTEGER NOT NULL DEFAULT 1 CHECK (is_live_call IN (0, 1)),
    created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
) STRICT;

CREATE TABLE IF NOT EXISTS saved_results (
    saved_result_id TEXT PRIMARY KEY,
    capability_token_hash TEXT NOT NULL UNIQUE,
    resolved_mode TEXT NOT NULL CHECK (resolved_mode IN ('LEARN', 'EVALUATE')),
    cancer_id TEXT,
    subtype_id TEXT,
    category_slug TEXT,
    query_or_claim_summary TEXT NOT NULL,
    result_envelope_json TEXT NOT NULL,
    cited_document_ids_json TEXT NOT NULL DEFAULT '[]',
    is_public INTEGER NOT NULL DEFAULT 0 CHECK (is_public = 0),
    created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    expires_at_utc TEXT NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS link_verification_cache (
    url TEXT PRIMARY KEY,
    is_alive INTEGER NOT NULL CHECK (is_alive IN (0, 1)),
    checked_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
) STRICT;
"""

_TS_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
_FTS_TOKEN_RE = re.compile(r"[\w]+", re.UNICODE)
_FTS_STOPWORDS = frozenset(
    "the and that this with from have has had are was were for not but can will does did you your they them its".split()
)


class OperationalStoreError(RuntimeError):
    pass


class BudgetExceededError(RuntimeError):
    """Pre-submission circuit breaker is open for a provider pool."""

    def __init__(self, provider_name: str, spent_usd: float, requested_usd: float, cap_usd: float):
        self.provider_name = provider_name
        self.spent_usd = spent_usd
        self.requested_usd = requested_usd
        self.cap_usd = cap_usd
        super().__init__(
            f"{provider_name}: circuit breaker open (spent+reserved ${spent_usd:.4f} + "
            f"requested ${requested_usd:.4f} > cap ${cap_usd:.2f})."
        )


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def format_ts(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime(_TS_FORMAT)


def parse_ts(value: str) -> datetime:
    return datetime.strptime(value, _TS_FORMAT).replace(tzinfo=timezone.utc)


def compute_non_additive_cost_usd(
    input_tokens: int,
    output_tokens: int,
    price_input_per_mtok: float,
    price_output_per_mtok: float,
    cached_input_tokens: int = 0,
    price_cached_input_per_mtok: float | None = None,
) -> float:
    """SG-05: bill input + output only. Reasoning tokens are already inside output_tokens.

    ``cached_input_tokens`` is a subset of ``input_tokens`` billed at the cached rate when one is
    configured; without a cached rate it is billed at the full input rate (conservative).
    """
    cached = max(0, min(cached_input_tokens, input_tokens)) if price_cached_input_per_mtok is not None else 0
    return (
        (input_tokens - cached) * price_input_per_mtok
        + cached * (price_cached_input_per_mtok or 0.0)
        + output_tokens * price_output_per_mtok
    ) / 1_000_000


def normalize_lay_phrase(phrase: str) -> str:
    return " ".join(_FTS_TOKEN_RE.findall(phrase.lower()))


def canonical_claim_hash(canonical_claim_text: str) -> str:
    return hashlib.sha256(normalize_lay_phrase(canonical_claim_text).encode("utf-8")).hexdigest()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _build_fts_query(text: str, max_terms: int = 12) -> str | None:
    """Turn free text into a safe FTS5 OR-query of quoted terms (no FTS syntax injection)."""
    terms: list[str] = []
    for token in _FTS_TOKEN_RE.findall(text.lower()):
        if len(token) < 3 or token in _FTS_STOPWORDS or token in terms:
            continue
        terms.append(token)
        if len(terms) >= max_terms:
            break
    if not terms:
        return None
    return " OR ".join(f'"{term}"' for term in terms)


class OperationalStore:
    """Thread-safe wrapper around one SQLite connection. All SQL is parameterized."""

    def __init__(self, db_path: str | Path):
        self._db_path = str(db_path)
        self._lock = threading.RLock()
        self._conn: sqlite3.Connection | None = None
        self._reservations: dict[str, tuple[str, float]] = {}

    # ------------------------------------------------------------------ lifecycle
    def initialize(self) -> None:
        version = sqlite3.sqlite_version_info
        if version < MIN_SQLITE_FOR_STRICT:
            raise OperationalStoreError(
                f"SQLite {sqlite3.sqlite_version} lacks STRICT tables; need >= 3.37 (spec: 3.45+)."
            )
        if version < SPEC_SQLITE_VERSION:
            logger.warning("SQLite %s is below the specified 3.45+.", sqlite3.sqlite_version)
        with self._lock:
            if self._db_path != ":memory:":
                Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self._db_path, check_same_thread=False, isolation_level=None)
            conn.row_factory = sqlite3.Row
            for pragma in _PRAGMAS:
                conn.execute(pragma)
            conn.executescript(_DDL)
            self._conn = conn
        self.assert_only_operational_tables()

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise OperationalStoreError("OperationalStore.initialize() has not been called.")
        return self._conn

    def list_user_tables(self) -> set[str]:
        with self._lock:
            rows = self.conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        return {row["name"] for row in rows if not row["name"].startswith(_INTERNAL_TABLE_PREFIXES)}

    def assert_only_operational_tables(self) -> None:
        unexpected = self.list_user_tables() - OPERATIONAL_TABLES
        if unexpected:
            raise OperationalStoreError(f"Non-operational tables present: {sorted(unexpected)}")

    # ------------------------------------------------------------------ link verdicts
    def get_link_verdict(self, url: str) -> bool | None:
        """Cached source-link aliveness, or None when unknown or older than the TTL."""
        key = (url or "").strip()
        if not key:
            return None
        cutoff = format_ts(utc_now() - timedelta(hours=LINK_VERDICT_TTL_HOURS))
        with self._lock:
            row = self.conn.execute(
                "SELECT is_alive FROM link_verification_cache WHERE url = ? AND checked_at_utc >= ?",
                (key, cutoff),
            ).fetchone()
        return None if row is None else bool(row["is_alive"])

    def set_link_verdict(self, url: str, is_alive: bool) -> None:
        key = (url or "").strip()
        if not key:
            return
        with self._lock:
            self.conn.execute(
                """INSERT INTO link_verification_cache (url, is_alive, checked_at_utc)
                   VALUES (?, ?, ?)
                   ON CONFLICT(url) DO UPDATE SET is_alive = excluded.is_alive,
                                                  checked_at_utc = excluded.checked_at_utc""",
                (key, 1 if is_alive else 0, format_ts(utc_now())),
            )

    # ------------------------------------------------------------------ budget (SG-05)
    def record_budget_entry(
        self,
        *,
        request_id: str,
        pipeline_stage: str,
        provider_name: ProviderName,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        reasoning_tokens_subset: int,
        finish_reason: str,
        estimated_cost_usd: float,
        latency_ms: int,
        is_live_call: bool = True,
    ) -> int:
        if provider_name not in PROVIDERS:
            raise ValueError(f"Unknown provider_name {provider_name!r}")
        if min(input_tokens, output_tokens, reasoning_tokens_subset) < 0 or estimated_cost_usd < 0:
            raise ValueError("Token counts and cost must be non-negative.")
        if reasoning_tokens_subset > output_tokens:
            logger.warning(
                "SG-05 anomaly: reasoning_tokens_subset (%d) > output_tokens (%d); stored as reported, not added.",
                reasoning_tokens_subset,
                output_tokens,
            )
        with self._lock:
            cur = self.conn.execute(
                """INSERT INTO budget_ledger (request_id, pipeline_stage, provider_name, model_id, input_tokens,
                       output_tokens, reasoning_tokens_subset, finish_reason, estimated_cost_usd, latency_ms, is_live_call)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    request_id,
                    pipeline_stage,
                    provider_name,
                    model_id,
                    int(input_tokens),
                    int(output_tokens),
                    int(reasoning_tokens_subset),
                    finish_reason or "unknown",
                    float(estimated_cost_usd),
                    int(latency_ms),
                    1 if is_live_call else 0,
                ),
            )
            return int(cur.lastrowid)

    def get_pool_totals(self) -> dict[str, dict[str, float | int]]:
        """Per-pool totals. ``total_tokens`` = input + output (reasoning is a subset of output)."""
        totals: dict[str, dict[str, float | int]] = {
            name: {
                "spent_usd": 0.0,
                "reserved_usd": 0.0,
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "reasoning_tokens_subset": 0,
                "total_tokens": 0,
            }
            for name in PROVIDERS
        }
        with self._lock:
            rows = self.conn.execute(
                """SELECT provider_name, COUNT(*) AS calls, COALESCE(SUM(estimated_cost_usd), 0.0) AS spent,
                          COALESCE(SUM(input_tokens), 0) AS inp, COALESCE(SUM(output_tokens), 0) AS outp,
                          COALESCE(SUM(reasoning_tokens_subset), 0) AS reas
                   FROM budget_ledger GROUP BY provider_name"""
            ).fetchall()
            for row in rows:
                entry = totals[row["provider_name"]]
                entry.update(
                    spent_usd=float(row["spent"]),
                    calls=int(row["calls"]),
                    input_tokens=int(row["inp"]),
                    output_tokens=int(row["outp"]),
                    reasoning_tokens_subset=int(row["reas"]),
                    total_tokens=int(row["inp"]) + int(row["outp"]),
                )
            for provider, amount in self._reservations.values():
                totals[provider]["reserved_usd"] = float(totals[provider]["reserved_usd"]) + amount
        return totals

    def reserve_budget(self, provider_name: ProviderName, estimated_max_cost_usd: float, cap_usd: float) -> str:
        """Circuit breaker: reserve worst-case spend before dispatch, or raise BudgetExceededError."""
        if provider_name not in PROVIDERS:
            raise ValueError(f"Unknown provider_name {provider_name!r}")
        with self._lock:
            pool = self.get_pool_totals()[provider_name]
            committed = float(pool["spent_usd"]) + float(pool["reserved_usd"])
            if committed + estimated_max_cost_usd > cap_usd:
                raise BudgetExceededError(provider_name, committed, estimated_max_cost_usd, cap_usd)
            reservation_id = uuid.uuid4().hex
            self._reservations[reservation_id] = (provider_name, float(estimated_max_cost_usd))
            return reservation_id

    def release_budget(self, reservation_id: str) -> None:
        with self._lock:
            self._reservations.pop(reservation_id, None)

    def is_circuit_open(self, provider_name: ProviderName, cap_usd: float) -> bool:
        pool = self.get_pool_totals()[provider_name]
        return float(pool["spent_usd"]) + float(pool["reserved_usd"]) >= cap_usd

    # ------------------------------------------------------------------ learned query mappings (Mechanism A)
    def lookup_approved_query_mapping(self, lay_phrase: str) -> dict[str, Any] | None:
        normalized = normalize_lay_phrase(lay_phrase)
        if not normalized:
            return None
        with self._lock:
            row = self.conn.execute(
                """SELECT mapping_id, normalized_lay_phrase, learned_medical_query, cancer_id, category_slug,
                          verified_fact_ids_json
                   FROM learned_query_mappings
                   WHERE normalized_lay_phrase = ? AND review_status = 'APPROVED'""",
                (normalized,),
            ).fetchone()
            if row is None:
                return None
            self.conn.execute(
                "UPDATE learned_query_mappings SET times_applied = times_applied + 1 WHERE mapping_id = ?",
                (row["mapping_id"],),
            )
        result = dict(row)
        result["verified_fact_ids"] = json.loads(result.pop("verified_fact_ids_json"))
        return result

    def record_candidate_query_mapping(
        self,
        *,
        lay_phrase: str,
        learned_medical_query: str,
        cancer_id: str,
        category_slug: str | None,
        verified_fact_ids: list[str],
    ) -> int | None:
        """Insert as PENDING_REVIEW. Never overwrites an existing (possibly reviewed) phrase."""
        normalized = normalize_lay_phrase(lay_phrase)
        if not normalized or not verified_fact_ids:
            raise ValueError("A lay phrase and at least one verified fact_id are required.")
        with self._lock:
            cur = self.conn.execute(
                """INSERT INTO learned_query_mappings
                       (normalized_lay_phrase, learned_medical_query, cancer_id, category_slug, verified_fact_ids_json)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(normalized_lay_phrase) DO NOTHING""",
                (normalized, learned_medical_query.strip(), cancer_id, category_slug, json.dumps(verified_fact_ids)),
            )
            return int(cur.lastrowid) if cur.rowcount else None

    def set_query_mapping_review_status(self, mapping_id: int, status: ReviewStatus) -> bool:
        if status not in REVIEW_STATUSES:
            raise ValueError(f"Invalid review status {status!r}")
        with self._lock:
            cur = self.conn.execute(
                "UPDATE learned_query_mappings SET review_status = ? WHERE mapping_id = ?", (status, mapping_id)
            )
            return cur.rowcount == 1

    # ------------------------------------------------------------------ claim memory (FR-07)
    def record_candidate_claim_memory(
        self,
        *,
        canonical_claim_text: str,
        cancer_id: str,
        subtype_id: str | None,
        category_slug: str,
        primary_outcome_code: str,
        outcome_label: str,
        nuance_warning_note: str,
        cited_document_ids: list[str],
        cited_fact_ids: list[str],
        cancer_info_api_version_hash: str,
        pii_sanitized_verified: bool,
    ) -> str:
        """Insert a PENDING_REVIEW candidate, or bump the hit count of an existing one.

        The caller must have run the PII sanitizer (SG-10); ``pii_sanitized_verified`` must be True.
        An existing row's review_status is never changed here.
        """
        if not pii_sanitized_verified:
            raise ValueError("SG-10: claim text must be PII-sanitized before it is stored.")
        text = canonical_claim_text.strip()
        claim_hash = canonical_claim_hash(text)
        with self._lock:
            existing = self.conn.execute(
                "SELECT claim_memory_id FROM claim_memory_library WHERE canonical_claim_hash = ?", (claim_hash,)
            ).fetchone()
            if existing is not None:
                self.conn.execute(
                    """UPDATE claim_memory_library
                       SET search_hit_count = search_hit_count + 1,
                           last_searched_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
                       WHERE claim_memory_id = ?""",
                    (existing["claim_memory_id"],),
                )
                return str(existing["claim_memory_id"])
            claim_memory_id = uuid.uuid4().hex
            self.conn.execute("BEGIN")
            try:
                self.conn.execute(
                    """INSERT INTO claim_memory_library
                           (claim_memory_id, canonical_claim_hash, canonical_claim_text, cancer_id, subtype_id,
                            category_slug, primary_outcome_code, outcome_label, nuance_warning_note,
                            cited_document_ids_json, cited_fact_ids_json, cancer_info_api_version_hash)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        claim_memory_id,
                        claim_hash,
                        text,
                        cancer_id,
                        subtype_id,
                        category_slug,
                        primary_outcome_code,
                        outcome_label,
                        nuance_warning_note,
                        json.dumps(cited_document_ids),
                        json.dumps(cited_fact_ids),
                        cancer_info_api_version_hash,
                    ),
                )
                self.conn.execute(
                    """INSERT INTO claim_memory_fts
                           (claim_memory_id, cancer_id, category_slug, canonical_claim_text, nuance_warning_note)
                       VALUES (?, ?, ?, ?, ?)""",
                    (claim_memory_id, cancer_id, category_slug, text, nuance_warning_note),
                )
                self.conn.execute("COMMIT")
            except Exception:
                self.conn.execute("ROLLBACK")
                raise
            return claim_memory_id

    def set_claim_memory_review_status(self, claim_memory_id: str, status: ReviewStatus) -> bool:
        if status not in REVIEW_STATUSES:
            raise ValueError(f"Invalid review status {status!r}")
        with self._lock:
            cur = self.conn.execute(
                "UPDATE claim_memory_library SET review_status = ? WHERE claim_memory_id = ?",
                (status, claim_memory_id),
            )
            return cur.rowcount == 1

    def search_approved_similar_claims_fts(
        self, query_text: str, cancer_id: str | None, limit: int = 3
    ) -> list[dict[str, Any]]:
        fts_query = _build_fts_query(query_text)
        if fts_query is None:
            return []
        with self._lock:
            rows = self.conn.execute(
                """SELECT l.claim_memory_id, l.canonical_claim_text, l.cancer_id, l.subtype_id, l.category_slug,
                          l.primary_outcome_code, l.outcome_label, l.nuance_warning_note
                   FROM claim_memory_fts AS f
                   JOIN claim_memory_library AS l ON l.claim_memory_id = f.claim_memory_id
                   WHERE claim_memory_fts MATCH ?
                     AND l.review_status = 'APPROVED'
                     AND (? IS NULL OR l.cancer_id = ?)
                   ORDER BY bm25(claim_memory_fts)
                   LIMIT ?""",
                (fts_query, cancer_id, cancer_id, max(1, min(int(limit), 20))),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_approved_claims_for_category(
        self, cancer_id: str, category_slug: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.conn.execute(
                """SELECT claim_memory_id, canonical_claim_text, primary_outcome_code, outcome_label
                   FROM claim_memory_library
                   WHERE cancer_id = ? AND category_slug = ? AND review_status = 'APPROVED'
                   ORDER BY search_hit_count DESC, created_at_utc DESC
                   LIMIT ?""",
                (cancer_id, category_slug, max(1, min(int(limit), 20))),
            ).fetchall()
        return [dict(row) for row in rows]

    # ------------------------------------------------------------------ saved results (private by default)
    def create_saved_result(
        self,
        *,
        resolved_mode: str,
        cancer_id: str | None,
        subtype_id: str | None,
        category_slug: str | None,
        query_or_claim_summary: str,
        result_envelope_json: str,
        cited_document_ids: list[str],
        ttl_days: int = 30,
    ) -> tuple[str, str, datetime]:
        """Return (saved_result_id, capability_token, expires_at). Only the token's hash is stored."""
        saved_result_id = uuid.uuid4().hex
        token = secrets.token_urlsafe(32)
        expires_at = utc_now() + timedelta(days=ttl_days)
        with self._lock:
            self.conn.execute(
                """INSERT INTO saved_results
                       (saved_result_id, capability_token_hash, resolved_mode, cancer_id, subtype_id, category_slug,
                        query_or_claim_summary, result_envelope_json, cited_document_ids_json, expires_at_utc)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    saved_result_id,
                    _hash_token(token),
                    resolved_mode,
                    cancer_id,
                    subtype_id,
                    category_slug,
                    query_or_claim_summary[:600],
                    result_envelope_json,
                    json.dumps(cited_document_ids),
                    format_ts(expires_at),
                ),
            )
        return saved_result_id, token, expires_at

    def get_saved_result_by_token(self, saved_result_id: str, capability_token: str) -> dict[str, Any] | None:
        """None when missing, wrong token or expired (expired rows are deleted). No existence leak."""
        with self._lock:
            row = self.conn.execute(
                "SELECT * FROM saved_results WHERE saved_result_id = ?", (saved_result_id,)
            ).fetchone()
            if row is None or not hmac.compare_digest(row["capability_token_hash"], _hash_token(capability_token)):
                return None
            if parse_ts(row["expires_at_utc"]) <= utc_now():
                self.conn.execute("DELETE FROM saved_results WHERE saved_result_id = ?", (saved_result_id,))
                return None
        return dict(row)

    def delete_saved_result(self, saved_result_id: str, capability_token: str) -> bool:
        with self._lock:
            row = self.conn.execute(
                "SELECT capability_token_hash FROM saved_results WHERE saved_result_id = ?", (saved_result_id,)
            ).fetchone()
            if row is None or not hmac.compare_digest(row["capability_token_hash"], _hash_token(capability_token)):
                return False
            self.conn.execute("DELETE FROM saved_results WHERE saved_result_id = ?", (saved_result_id,))
            return True

    def purge_expired_saved_results(self) -> int:
        with self._lock:
            cur = self.conn.execute("DELETE FROM saved_results WHERE expires_at_utc <= ?", (format_ts(utc_now()),))
            return cur.rowcount
