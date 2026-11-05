"""Meta Model API client for Learn Mode synthesis ($150 pool, $115 pre-submission cap).

Endpoint and response shape verified live on 29 Oct 2026 (receipts/2026-10-29-live-meta-text-call.md):
``POST {META_API_BASE_URL}/responses`` with ``model`` + ``input``; text is in
``output[type=message].content[type=output_text].text``; usage in ``usage.input_tokens`` /
``output_tokens`` / ``output_tokens_details.reasoning_tokens``.

Request fields checked against Meta's Responses API docs on 2 Nov 2026
(https://dev.meta.ai/docs/protocols/responses), not yet in a live call:
- ``store``: default ``true``; ``false`` means "the server keeps no copy" (WHO Clause 6).
- ``reasoning.effort``: none|minimal|low|medium|high|xhigh (``none`` is HTTP 400 on Muse Spark).
- ``instructions``: developer-level, current request only.
- ``max_output_tokens``: integer >= 16; covers reasoning + visible output.
Output parsing per the same page: final answers are ``message`` items WITHOUT ``phase``;
items with ``phase: "commentary"`` are interim narration and are discarded (same risk class as
the Baseten T4 defect, SG-02). Status ``failed`` / ``cancelled`` is a provider error.
Structured output (``text.format``) is not used: the docs do not show its exact request shape,
so JSON is requested in the prompt and gated by SG-07 instead.

Image understanding (docs-verified 4 Nov 2026, https://dev.meta.ai/docs/image-understanding):
``muse-spark-1.3`` reads images sent as ``input_image`` content blocks inside a ``user``
message; ``image_url`` is a plain string holding a base64 ``data:`` URL. Used by
``POST /api/v1/extract/image`` for screenshot transcription.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

from ..config import Settings, create_verified_ssl_context
from ..db.operational_store import OperationalStore
from .governance import CallGovernor, ProviderError, ProviderPolicy, estimate_input_tokens
from .json_utils import (
    IncompleteGenerationError,
    clean_and_validate_json,
    ensure_complete_generation,
    extract_cached_input_tokens,
    extract_non_additive_usage,
    purge_pending_tool_prose,
)

logger = logging.getLogger("cancerlens.providers.meta")

T = TypeVar("T", bound=BaseModel)

# Conservative budget-reservation bump for one attached image. The docs do not state
# image input pricing, so the reservation assumes image tokens at the standard input
# rate; the ledger always reconciles to the usage the API actually reports.
IMAGE_INPUT_TOKEN_ALLOWANCE = 1500


@dataclass(frozen=True)
class MetaTextResult:
    text: str
    finish_reason: str
    input_tokens: int
    output_tokens: int
    reasoning_tokens_subset: int


def parse_responses_output(body: dict[str, Any]) -> tuple[str | None, list[dict[str, Any]]]:
    """Extract final assistant text and any function-call items from a /v1/responses body.

    Reasoning items are ignored entirely (never logged or returned, SG-10). Message items marked
    ``phase: "commentary"`` are interim narration, not the answer, and are discarded.
    """
    texts: list[str] = []
    tool_calls: list[dict[str, Any]] = []
    for item in body.get("output") or []:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        if item_type == "message":
            if item.get("phase") == "commentary":
                continue
            for part in item.get("content") or []:
                if isinstance(part, dict) and part.get("type") == "output_text" and isinstance(part.get("text"), str):
                    texts.append(part["text"])
        elif item_type in ("function_call", "tool_call"):
            tool_calls.append({"type": item_type, "id": item.get("id")})
    return ("".join(texts) if texts else None), tool_calls


def _finish_reason_from_status(body: dict[str, Any]) -> str:
    status = body.get("status")
    if status == "completed":
        return "stop"
    if status == "incomplete":
        reason = (body.get("incomplete_details") or {}).get("reason")
        return "length" if reason in ("max_output_tokens", "max_tokens", None) else f"incomplete:{reason}"
    if status in ("failed", "cancelled"):
        return f"status_{status}"
    return str(status or "unknown")


class MetaMuseClient:
    provider_name = "meta_model_api"

    def __init__(self, settings: Settings, store: OperationalStore, transport: httpx.AsyncBaseTransport | None = None):
        self._settings = settings
        self.model_id = settings.META_MODEL_ID
        self.governor = CallGovernor(
            ProviderPolicy(
                provider_name="meta_model_api",
                display_name="Meta Model API",
                model_id=settings.META_MODEL_ID,
                live_enabled=settings.LIVE_LLM_CALLS_ENABLED,
                raw_api_key=settings.META_API_KEY,
                price_input_per_mtok=settings.META_PRICE_INPUT_PER_MTOK_USD,
                price_output_per_mtok=settings.META_PRICE_OUTPUT_PER_MTOK_USD,
                budget_cap_usd=settings.META_BUDGET_CAP_USD,
                price_cached_input_per_mtok=settings.META_PRICE_CACHED_INPUT_PER_MTOK_USD,
            ),
            store,
        )
        self._client = httpx.AsyncClient(
            base_url=settings.META_API_BASE_URL.rstrip("/"),
            verify=create_verified_ssl_context(),
            timeout=settings.LLM_TIMEOUT_SECONDS,
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    def build_payload(
        self, instructions: str, input_text: str, max_output_tokens: int,
        image: tuple[str, str] | None = None,
    ) -> dict[str, Any]:
        """``image`` is (mime_type, base64_bytes) and selects the docs-verified
        multimodal input shape; otherwise the plain-text shape is used."""
        if image is None:
            model_input: Any = input_text
        else:
            mime_type, b64 = image
            model_input = [{
                "type": "message",
                "role": "user",
                "content": [
                    {"type": "input_text", "text": input_text},
                    {"type": "input_image", "image_url": f"data:{mime_type};base64,{b64}"},
                ],
            }]
        return {
            "model": self.model_id,
            "instructions": instructions,
            "input": model_input,
            "store": False,  # WHO Licence 202610792 Clause 6: no retention for model training
            "reasoning": {"effort": "low"},  # SG-04
            "max_output_tokens": max_output_tokens,
        }

    async def generate_text(
        self, *, request_id: str, pipeline_stage: str, instructions: str, input_text: str,
        image: tuple[str, str] | None = None,
    ) -> MetaTextResult:
        max_out = self._settings.META_MAX_OUTPUT_TOKENS
        estimated_in = estimate_input_tokens(instructions, input_text) + (
            IMAGE_INPUT_TOKEN_ALLOWANCE if image is not None else 0
        )
        api_key, reservation_id = self.governor.preflight(estimated_in, max_out)
        started = time.monotonic()
        payload = self.build_payload(instructions, input_text, max_out, image)
        try:
            response = await self._client.post(
                "/responses",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            )
        except httpx.HTTPError as exc:
            # Outcome unknown: conservatively book the worst-case reservation.
            self.governor.settle(
                reservation_id=reservation_id, request_id=request_id, pipeline_stage=pipeline_stage,
                input_tokens=0, output_tokens=0, reasoning_tokens_subset=0,
                finish_reason="uncertain_transport_error", started_at=started,
                cost_override_usd=self.governor.cost(estimated_in, max_out),
            )
            raise ProviderError(f"Meta Model API request failed: {type(exc).__name__}") from exc

        if response.status_code != 200:
            self.governor.settle(
                reservation_id=reservation_id, request_id=request_id, pipeline_stage=pipeline_stage,
                input_tokens=0, output_tokens=0, reasoning_tokens_subset=0,
                finish_reason=f"http_{response.status_code}", started_at=started, cost_override_usd=0.0,
            )
            raise ProviderError(f"Meta Model API returned HTTP {response.status_code}.", status_code=response.status_code)

        try:
            body = response.json()
        except ValueError as exc:
            self.governor.settle(
                reservation_id=reservation_id, request_id=request_id, pipeline_stage=pipeline_stage,
                input_tokens=0, output_tokens=0, reasoning_tokens_subset=0,
                finish_reason="invalid_json_body", started_at=started,
                cost_override_usd=self.governor.cost(estimated_in, max_out),
            )
            raise ProviderError("Meta Model API returned a non-JSON body.") from exc

        input_tokens, output_tokens, reasoning = extract_non_additive_usage(body.get("usage"))
        finish_reason = _finish_reason_from_status(body)
        self.governor.settle(
            reservation_id=reservation_id, request_id=request_id, pipeline_stage=pipeline_stage,
            input_tokens=input_tokens, output_tokens=output_tokens, reasoning_tokens_subset=reasoning,
            finish_reason=finish_reason, started_at=started,
            cached_input_tokens=extract_cached_input_tokens(body.get("usage")),
        )
        if body.get("store") is True:
            logger.warning("Meta Model API echoed store=true although store=false was sent (WHO Clause 6 check).")
        if body.get("error") or finish_reason in ("status_failed", "status_cancelled"):
            raise ProviderError("Meta Model API reported a failed or cancelled response.")

        text, tool_calls = parse_responses_output(body)
        text = purge_pending_tool_prose(finish_reason, tool_calls, text)  # SG-02 applies to Meta too
        if tool_calls:
            raise IncompleteGenerationError("Meta returned a tool call where final text was expected.",
                                            finish_reason=finish_reason, reasoning_tokens=reasoning)
        clean = ensure_complete_generation(finish_reason, text, reasoning)  # SG-04
        return MetaTextResult(clean, finish_reason, input_tokens, output_tokens, reasoning)

    async def generate_structured(
        self, *, request_id: str, pipeline_stage: str, instructions: str, input_text: str, schema_cls: type[T]
    ) -> T:
        result = await self.generate_text(
            request_id=request_id, pipeline_stage=pipeline_stage, instructions=instructions, input_text=input_text
        )
        return clean_and_validate_json(result.text, schema_cls)  # SG-07
