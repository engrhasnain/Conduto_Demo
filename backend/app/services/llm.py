"""Thin wrapper around the Anthropic SDK.

The SDK is imported on first use: without an API key it is never needed, and skipping it keeps cold starts fast.
"""
import json
import logging
from typing import TYPE_CHECKING

from ..config import ANTHROPIC_MODEL

if TYPE_CHECKING:
    import anthropic

log = logging.getLogger("conduto.llm")

# Models that support server-side refusal fallbacks; the API re-runs a declined
# request on a fallback model inside the same call.
FALLBACK_MODELS = {"claude-opus-5", "claude-fable-5-1"}

_client: "anthropic.Anthropic | None" = None


class LLMError(RuntimeError):
    pass


def client() -> "anthropic.Anthropic":
    import anthropic

    global _client
    if _client is None:
        _client = anthropic.Anthropic(max_retries=2, timeout=120.0)
    return _client


def create(**params):
    params.setdefault("model", ANTHROPIC_MODEL)
    if params["model"] in FALLBACK_MODELS:
        resp = client().beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **params)
    else:
        resp = client().messages.create(**params)
    if resp.stop_reason == "refusal":
        raise LLMError("The model declined this request.")
    return resp


def extract_json(system: str, content, schema: dict, max_tokens: int = 8000, effort: str = "low") -> dict:
    """Single call with a JSON-schema constrained response."""
    import anthropic

    try:
        resp = create(
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": content}],
            output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        )
    except anthropic.APIConnectionError as e:
        raise LLMError(f"Cannot reach the Claude API: {e}") from e
    except anthropic.RateLimitError as e:
        raise LLMError("Claude API rate limit reached, try again shortly.") from e
    except anthropic.APIStatusError as e:
        raise LLMError(f"Claude API error {e.status_code}: {e.message}") from e
    if resp.stop_reason == "max_tokens":
        raise LLMError("The response was cut off (max_tokens).")
    text = next((b.text for b in resp.content if b.type == "text"), "")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise LLMError("The model returned invalid JSON.") from e
