"""Deterministic model-output gates.

- SG-02 ``purge_pending_tool_prose``: prose emitted alongside a pending tool call is discarded (T4 fix).
- SG-04 ``ensure_complete_generation``: ``finish_reason == "length"`` or empty content is an error (T1 fix).
- SG-05 ``extract_non_additive_usage``: reasoning tokens are a subset of output tokens (T2 finding).
- SG-07 ``clean_and_validate_json``: strip Markdown fences, then strict Pydantic validation (T5 fix).

Error messages never include model content (SG-10).
"""

from __future__ import annotations

import re
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

_FULL_FENCE_RE = re.compile(r"^\s*```[ \t]*(?:json|JSON)?[ \t]*\r?\n?(.*?)\r?\n?[ \t]*```\s*$", re.DOTALL)
_ANY_FENCE_RE = re.compile(r"```[ \t]*(?:json|JSON)?[ \t]*\r?\n(.*?)\r?\n[ \t]*```", re.DOTALL)


class IncompleteGenerationError(RuntimeError):
    """SG-04: the model stopped early (length) or returned no usable content."""

    def __init__(self, message: str, *, finish_reason: str | None = None, reasoning_tokens: int = 0):
        self.finish_reason = finish_reason
        self.reasoning_tokens = reasoning_tokens
        super().__init__(message)


class ModelOutputValidationError(ValueError):
    """SG-07: content was present but is not valid JSON for the expected schema."""


def purge_pending_tool_prose(finish_reason: str | None, tool_calls: list | None, content: str | None) -> str | None:
    """SG-02: a tool request is not a tool result. Discard any prose while a tool call is pending."""
    if finish_reason == "tool_calls" or bool(tool_calls):
        return None
    return content


def ensure_complete_generation(finish_reason: str | None, content: str | None, reasoning_tokens: int = 0) -> str:
    """SG-04: reject truncated or empty final turns; return the stripped content otherwise."""
    if finish_reason == "length":
        raise IncompleteGenerationError(
            "Model output truncated (finish_reason=length).",
            finish_reason=finish_reason,
            reasoning_tokens=reasoning_tokens,
        )
    if content is None or not content.strip():
        detail = " after spending reasoning tokens" if reasoning_tokens > 0 else ""
        raise IncompleteGenerationError(
            f"Model returned empty content{detail}.", finish_reason=finish_reason, reasoning_tokens=reasoning_tokens
        )
    return content.strip()


def strip_markdown_fences(raw_text: str) -> str:
    text = raw_text.strip()
    full = _FULL_FENCE_RE.match(text)
    if full:
        return full.group(1).strip()
    embedded = _ANY_FENCE_RE.search(text)
    if embedded:
        return embedded.group(1).strip()
    return text


def clean_and_validate_json(raw_text: str | None, schema_cls: type[T]) -> T:
    """SG-07: reject empty input, strip code fences, then ``schema_cls.model_validate_json``."""
    if raw_text is None or not raw_text.strip():
        raise IncompleteGenerationError("Model returned empty content; nothing to validate.")
    cleaned = strip_markdown_fences(raw_text)
    try:
        return schema_cls.model_validate_json(cleaned)
    except ValidationError as exc:
        raise ModelOutputValidationError(
            f"Model output failed {schema_cls.__name__} validation ({exc.error_count()} error(s))."
        ) from exc


def _as_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def extract_non_additive_usage(usage_dict: dict | None) -> tuple[int, int, int]:
    """SG-05: return (input_tokens, output_tokens, reasoning_tokens_subset).

    Meta /v1/responses: input_tokens, output_tokens, output_tokens_details.reasoning_tokens.
    Baseten /v1/chat/completions: prompt_tokens, completion_tokens, completion_tokens_details.reasoning_tokens.
    The reasoning count is reported for diagnostics only and is never added to output_tokens.
    """
    if not isinstance(usage_dict, dict):
        return 0, 0, 0
    if "input_tokens" in usage_dict or "output_tokens" in usage_dict:
        details = usage_dict.get("output_tokens_details") or {}
        return (
            _as_int(usage_dict.get("input_tokens")),
            _as_int(usage_dict.get("output_tokens")),
            _as_int(details.get("reasoning_tokens") if isinstance(details, dict) else 0),
        )
    details = usage_dict.get("completion_tokens_details") or {}
    return (
        _as_int(usage_dict.get("prompt_tokens")),
        _as_int(usage_dict.get("completion_tokens")),
        _as_int(details.get("reasoning_tokens") if isinstance(details, dict) else 0),
    )


def extract_cached_input_tokens(usage_dict: dict | None) -> int:
    """Cached prompt tokens (a subset of input tokens), for both provider usage shapes.

    Meta: input_tokens_details.cached_tokens (seen in the 29 Oct receipt).
    Baseten: prompt_tokens_details.cached_tokens (Baseten docs, prompt caching).
    """
    if not isinstance(usage_dict, dict):
        return 0
    details = usage_dict.get("input_tokens_details") or usage_dict.get("prompt_tokens_details") or {}
    return _as_int(details.get("cached_tokens")) if isinstance(details, dict) else 0


def wrap_untrusted(text: str, tag: str = "untrusted_user_input") -> str:
    """SEC-05: delimit untrusted text and neutralise any attempt to close the delimiter early."""
    safe = text.replace(f"</{tag}>", f"<\\/{tag}>").replace(f"<{tag}>", f"<\\{tag}>")
    return f"<{tag}>\n{safe}\n</{tag}>"
