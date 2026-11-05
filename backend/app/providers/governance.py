"""Shared call governance for both LLM providers (Stage 1 helper module).

Order of checks before any network I/O:
1. ``LIVE_LLM_CALLS_ENABLED`` master switch ($0.00 discipline).
2. SG-09 API key validation.
3. Pricing must be configured (the circuit breaker cannot work without it).
4. Reserve worst-case cost against the pool's pre-submission cap.
After the call, the actual usage is written to ``budget_ledger`` (SG-05) and the reservation released.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from ..config import ConfigurationError, validate_api_key
from ..db.operational_store import OperationalStore, ProviderName, compute_non_additive_cost_usd

logger = logging.getLogger("cancerlens.providers")

# Conservative token estimate for budgeting only (never used for billing).
_CHARS_PER_TOKEN_ESTIMATE = 3


class LiveCallsDisabledError(RuntimeError):
    """LIVE_LLM_CALLS_ENABLED is false: the call was refused before any network I/O."""


class ProviderError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)


@dataclass(frozen=True)
class ProviderPolicy:
    provider_name: ProviderName
    display_name: str
    model_id: str
    live_enabled: bool
    raw_api_key: str
    price_input_per_mtok: float | None
    price_output_per_mtok: float | None
    budget_cap_usd: float
    price_cached_input_per_mtok: float | None = None


def estimate_input_tokens(*texts: str) -> int:
    return sum(len(t) for t in texts) // _CHARS_PER_TOKEN_ESTIMATE + 64


class CallGovernor:
    def __init__(self, policy: ProviderPolicy, store: OperationalStore):
        self.policy = policy
        self.store = store

    @property
    def pricing_configured(self) -> bool:
        return self.policy.price_input_per_mtok is not None and self.policy.price_output_per_mtok is not None

    def preflight(self, estimated_input_tokens: int, max_output_tokens: int) -> tuple[str, str]:
        """Return (validated_api_key, reservation_id) or raise before any network call."""
        if not self.policy.live_enabled:
            raise LiveCallsDisabledError(
                f"{self.policy.display_name}: live LLM calls are disabled (LIVE_LLM_CALLS_ENABLED=false)."
            )
        api_key = validate_api_key(self.policy.raw_api_key, self.policy.display_name)
        if not self.pricing_configured:
            raise ConfigurationError(
                f"{self.policy.display_name}: per-token pricing is not configured; refusing live call."
            )
        worst_case = self.cost(estimated_input_tokens, max_output_tokens)
        reservation_id = self.store.reserve_budget(self.policy.provider_name, worst_case, self.policy.budget_cap_usd)
        return api_key, reservation_id

    def cost(self, input_tokens: int, output_tokens: int, cached_input_tokens: int = 0) -> float:
        """Reservations call this with cached_input_tokens=0, so the worst case assumes no cache hits."""
        return compute_non_additive_cost_usd(
            input_tokens,
            output_tokens,
            float(self.policy.price_input_per_mtok or 0.0),
            float(self.policy.price_output_per_mtok or 0.0),
            cached_input_tokens,
            self.policy.price_cached_input_per_mtok,
        )

    def settle(
        self,
        *,
        reservation_id: str,
        request_id: str,
        pipeline_stage: str,
        input_tokens: int,
        output_tokens: int,
        reasoning_tokens_subset: int,
        finish_reason: str,
        started_at: float,
        cost_override_usd: float | None = None,
        cached_input_tokens: int = 0,
    ) -> None:
        """Write the ledger row (SG-05: cost from input + output only) and release the reservation."""
        try:
            cost = (
                cost_override_usd
                if cost_override_usd is not None
                else self.cost(input_tokens, output_tokens, cached_input_tokens)
            )
            self.store.record_budget_entry(
                request_id=request_id,
                pipeline_stage=pipeline_stage,
                provider_name=self.policy.provider_name,
                model_id=self.policy.model_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                reasoning_tokens_subset=reasoning_tokens_subset,
                finish_reason=finish_reason,
                estimated_cost_usd=cost,
                latency_ms=int((time.monotonic() - started_at) * 1000),
                is_live_call=True,
            )
        finally:
            self.store.release_budget(reservation_id)
