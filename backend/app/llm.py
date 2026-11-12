"""Calls Gemini/Gemma on Vertex AI with per-tier fallback and usage accounting."""

import os
import re
import time
from dataclasses import dataclass, field

from google import genai
from google.genai import errors, types

from .genai_client import wire_model_id
from .models import MODELS, TIERS, Tier, cost_usd

# Status codes that move on to the next model in the tier's chain:
# 404 = model not enabled/available in this project, 429 = quota, 5xx = overloaded.
FALLBACK_CODES = {404, 429}


class QuotaExhaustedError(Exception):
    """Every model in the chain returned 429."""


class UpstreamError(Exception):
    """Every model in the chain failed, not all with 429."""


@dataclass
class Attempt:
    model: str
    code: int
    message: str


@dataclass
class GenerationResult:
    text: str
    thinking: str | None
    model: str
    used_fallback: bool
    prompt_tokens: int
    output_tokens: int  # candidates + thoughts (both billed as output)
    thought_tokens: int
    latency_ms: float  # the successful call only
    cost_usd: float
    failed_attempts: list[Attempt] = field(default_factory=list)

    @property
    def output_tokens_per_sec(self) -> float:
        return self.output_tokens / (self.latency_ms / 1000) if self.latency_ms else 0.0


_CHANNEL_RE = re.compile(r"<\|channel>thought([\s\S]*?)<channel\|>", re.IGNORECASE)
_THINK_RE = re.compile(r"<think>([\s\S]*?)</think>", re.IGNORECASE)


def split_inline_thinking(raw: str) -> tuple[str, str | None]:
    """Gemma 4 can return its reasoning inline as <|channel>thought ... <channel|>."""
    for pattern in (_CHANNEL_RE, _THINK_RE):
        match = pattern.search(raw)
        if match:
            return pattern.sub("", raw).strip(), match.group(1).strip()
    return raw.strip(), None


def _config(
    model_id: str,
    system: str | None,
    deep_thinking: bool,
    response_schema: object | None,
) -> types.GenerateContentConfig:
    spec = MODELS[model_id]
    kwargs: dict = {
        "system_instruction": system,
        "max_output_tokens": 8192 if deep_thinking else 2048,
    }
    if spec.temperature is not None:
        kwargs["temperature"] = spec.temperature
    # Gemma rejected thinkingConfig in v1, so only Gemini gets it.
    if spec.family == "gemini":
        # Default level is a cost/latency vs quality setting, measured in
        # docs/results.md. Deep Thinking always uses HIGH.
        default_level = types.ThinkingLevel[os.environ.get("DEFAULT_THINKING_LEVEL", "LOW").upper()]
        kwargs["thinking_config"] = types.ThinkingConfig(
            thinking_level=types.ThinkingLevel.HIGH if deep_thinking else default_level,
            include_thoughts=deep_thinking,
        )
    if response_schema is not None:
        kwargs["response_mime_type"] = "application/json"
        kwargs["response_schema"] = response_schema
    return types.GenerateContentConfig(**kwargs)


def _parse(response: types.GenerateContentResponse) -> tuple[str, str | None]:
    parts = []
    if response.candidates and response.candidates[0].content:
        parts = response.candidates[0].content.parts or []
    answer = "".join(p.text or "" for p in parts if not p.thought)
    thinking = "".join(p.text or "" for p in parts if p.thought)
    if not answer.strip():
        raise ValueError("empty response")
    if thinking.strip():
        return answer.strip(), thinking.strip()
    return split_inline_thinking(answer)


async def generate(
    client: genai.Client,
    tier: Tier,
    contents: list[types.Content],
    *,
    system: str | None = None,
    deep_thinking: bool = False,
    response_schema: object | None = None,
) -> GenerationResult:
    chain = TIERS[tier]
    failed: list[Attempt] = []
    for model_id in chain:
        start = time.perf_counter()
        try:
            response = await client.aio.models.generate_content(
                model=wire_model_id(model_id),
                contents=contents,
                config=_config(model_id, system, deep_thinking, response_schema),
            )
            text, thinking = _parse(response)
        except errors.APIError as e:
            failed.append(Attempt(model_id, e.code, str(e.message or e)[:300]))
            if e.code in FALLBACK_CODES or e.code >= 500:
                continue
            raise UpstreamError(f"{model_id} returned {e.code}") from e
        except ValueError as e:
            failed.append(Attempt(model_id, 0, str(e)))
            continue
        latency_ms = (time.perf_counter() - start) * 1000

        usage = response.usage_metadata
        prompt_tokens = (usage.prompt_token_count if usage else 0) or 0
        thought_tokens = (usage.thoughts_token_count if usage else 0) or 0
        output_tokens = ((usage.candidates_token_count if usage else 0) or 0) + thought_tokens
        return GenerationResult(
            text=text,
            thinking=thinking,
            model=model_id,
            used_fallback=model_id != chain[0],
            prompt_tokens=prompt_tokens,
            output_tokens=output_tokens,
            thought_tokens=thought_tokens,
            latency_ms=latency_ms,
            cost_usd=cost_usd(model_id, prompt_tokens, output_tokens),
            failed_attempts=failed,
        )

    if failed and all(a.code == 429 for a in failed):
        raise QuotaExhaustedError(tier)
    raise UpstreamError(f"all models failed for tier {tier}: {failed}")
