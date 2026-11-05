"""Runtime settings, TLS context factory and API-key sanity checks (SG-09).

Settings load from ``backend/.env`` then ``backend/.env.local`` (later wins), then the
process environment. No secret is ever logged or echoed by this module.
"""

from __future__ import annotations

import ssl
from functools import lru_cache
from pathlib import Path

import certifi
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]

_PLACEHOLDER_EXACT = frozenset({"echo", "your_key_here", "xxx", "todo"})
_PLACEHOLDER_SUBSTRINGS = ("your_key", "your-api-key", "changeme", "placeholder", "replace_me", "<key>")
MIN_API_KEY_LENGTH = 20


class ConfigurationError(RuntimeError):
    """Raised when configuration is missing or unsafe. Messages never contain secret values."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env", BACKEND_DIR / ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # Master $0.00 switch: no Meta / Baseten network call is made while False.
    LIVE_LLM_CALLS_ENABLED: bool = False

    # Cancer Info API (Layer 1). Stage 2: live-verified 2 Nov 2026 against
    # https://cancerinfo-api.onrender.com/openapi.json plus live /v1/cancers,
    # /v1/search and /v1/cancers/breast-cancer/symptoms responses.
    CANCER_INFO_API_BASE_URL: str = "https://cancerinfo-api.onrender.com"
    CANCER_INFO_API_KEY: str = ""
    CANCER_INFO_API_SEND_X_API_KEY: bool = False
    CANCER_INFO_CACHE_TTL_SECONDS: int = Field(default=300, ge=0, le=3600)
    # 45s so a Render cold start (30-40s spin-up after idle) is not a false TOOL_FAILED.
    CANCER_INFO_API_TIMEOUT_SECONDS: float = Field(default=45.0, gt=0, le=120)
    # Live-verified paths (/v1/search on 2 Nov 2026, /v1/facts?ids= on 4 Nov 2026; the
    # Stage 1 assumed /v1/evidence/search returns HTTP 404). All three stay configurable
    # for the offline harness and future API versions.
    CANCER_INFO_API_CANCERS_PATH: str = "/v1/cancers"
    CANCER_INFO_API_SEARCH_PATH: str = "/v1/search"
    CANCER_INFO_API_FACTS_PATH: str = "/v1/facts"

    # Meta Model API ($150 pool)
    META_API_BASE_URL: str = "https://api.meta.ai/v1"
    META_API_KEY: str = ""
    META_MODEL_ID: str = "muse-spark-1.3"
    META_BUDGET_CAP_USD: float = 115.00
    META_POOL_TOTAL_USD: float = 150.00
    # Responses API max_output_tokens (docs: >= 16, includes reasoning). SG-04 keeps it >= 1024.
    META_MAX_OUTPUT_TOKENS: int = Field(default=2048, ge=1024)
    META_PRICE_INPUT_PER_MTOK_USD: float | None = None  # UNVERIFIED: must be set before live use
    META_PRICE_OUTPUT_PER_MTOK_USD: float | None = None
    META_PRICE_CACHED_INPUT_PER_MTOK_USD: float | None = None  # unset: cached input billed at full input price

    # Baseten Model API ($100 pool)
    BASETEN_API_BASE_URL: str = "https://inference.baseten.co/v1"
    BASETEN_API_KEY: str = ""
    BASETEN_MODEL_ID: str = "meta-models/muse-spark-open-1026"
    BASETEN_BUDGET_CAP_USD: float = 65.00
    BASETEN_POOL_TOTAL_USD: float = 100.00
    # Baseten pricing page 29 Oct 2026; owner confirmed 1 Nov 2026 that the -1026 slug uses the same rates.
    BASETEN_PRICE_INPUT_PER_MTOK_USD: float | None = 1.25
    BASETEN_PRICE_CACHED_INPUT_PER_MTOK_USD: float | None = 0.15
    BASETEN_PRICE_OUTPUT_PER_MTOK_USD: float | None = 4.25

    LLM_TIMEOUT_SECONDS: float = Field(default=60.0, gt=0, le=300)

    # Local operational SQLite
    OPERATIONAL_DB_PATH: str = "./cancerlens_app.db"
    SAVED_RESULT_TTL_DAYS: int = Field(default=30, ge=1, le=30)
    CLAIM_MEMORY_CAPTURE_ENABLED: bool = False

    EVALUATE_MAX_HOPS: int = Field(default=3, ge=1, le=3)
    CORS_ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]

    # Stage 2 launch gate for POST /api/v1/extract/url. Default off so the offline
    # suite stays hermetic (no real DNS/fetch) and the owner enables public-URL
    # fetching explicitly; mirrors the LIVE_LLM_CALLS_ENABLED idiom.
    URL_EXTRACTION_ENABLED: bool = False

    @field_validator(
        "META_PRICE_INPUT_PER_MTOK_USD",
        "META_PRICE_OUTPUT_PER_MTOK_USD",
        "META_PRICE_CACHED_INPUT_PER_MTOK_USD",
        "BASETEN_PRICE_INPUT_PER_MTOK_USD",
        "BASETEN_PRICE_CACHED_INPUT_PER_MTOK_USD",
        "BASETEN_PRICE_OUTPUT_PER_MTOK_USD",
        mode="before",
    )
    @classmethod
    def _blank_price_means_unset(cls, value: object) -> object:
        """A blank price (``KEY=`` in .env.local) means unset, not a crash.

        ``.env.example`` ships the Meta prices blank, so a fresh
        ``cp .env.example .env.local`` must load with those prices as None
        (live calls stay refused until real prices are set).
        """
        if isinstance(value, str) and not value.strip():
            return None
        return value

    def resolved_db_path(self) -> Path:
        """Relative DB paths resolve against ``backend/`` so the file location never depends on CWD."""
        if self.OPERATIONAL_DB_PATH == ":memory:":
            return Path(":memory:")
        path = Path(self.OPERATIONAL_DB_PATH)
        return path if path.is_absolute() else (BACKEND_DIR / path).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def create_verified_ssl_context() -> ssl.SSLContext:
    """SG-09: certifi-backed verification for every outbound httpx client. Never verify=False."""
    return ssl.create_default_context(cafile=certifi.where())


def validate_api_key(raw_key: str | None, provider_name: str) -> str:
    """SG-09: strip whitespace/newlines and reject empty, short or placeholder keys.

    Raises ``ConfigurationError`` naming the provider and the failed rule, never the value.
    """
    key = (raw_key or "").strip()
    if not key:
        raise ConfigurationError(f"{provider_name}: API key is missing.")
    if any(ch.isspace() for ch in key):
        raise ConfigurationError(f"{provider_name}: API key contains internal whitespace.")
    lowered = key.lower()
    if lowered in _PLACEHOLDER_EXACT or any(token in lowered for token in _PLACEHOLDER_SUBSTRINGS):
        raise ConfigurationError(f"{provider_name}: API key is a placeholder value.")
    if key.startswith("$"):
        raise ConfigurationError(f"{provider_name}: API key looks like an unexpanded shell variable.")
    if len(key) < MIN_API_KEY_LENGTH:
        raise ConfigurationError(
            f"{provider_name}: API key is shorter than {MIN_API_KEY_LENGTH} characters."
        )
    return key
