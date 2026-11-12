"""Model tiers, fallback chains and token prices.

The app only ever sends a tier name. Which model serves that tier lives here,
so a model retirement (like Gemini 2.5 on 2026-10-20) is a backend deploy,
not an app release.
"""

from dataclasses import dataclass
from typing import Literal

Tier = Literal["fast", "smart", "expert"]


@dataclass(frozen=True)
class ModelSpec:
    id: str
    family: Literal["gemini", "gemma"]
    # USD per 1M tokens. Thinking tokens are billed as output.
    input_per_m: float
    output_per_m: float
    # Gemini 3 models are tuned for the default temperature (1.0); Google
    # advises not lowering it. Gemma 4 errored above 0.4 in v1.
    temperature: float | None


# Prices checked 2026-10-24 against public pricing pages and third-party
# trackers. Re-check on the Vertex pricing page before quoting cost numbers.
MODELS: dict[str, ModelSpec] = {
    spec.id: spec
    for spec in [
        ModelSpec("gemini-3.1-flash-lite", "gemini", 0.25, 1.50, None),
        ModelSpec("gemini-3.5-flash-lite", "gemini", 0.30, 2.50, None),
        # Introductory price through 2026-12-31, then reportedly $1.50 / $7.50.
        ModelSpec("gemini-3.8-flash", "gemini", 0.75, 3.75, None),
        # Experimental MaaS launch; sources disagree on price, this is the higher one.
        ModelSpec("gemma-4-26b-a4b-it-maas", "gemma", 0.15, 0.60, 0.4),
    ]
}

# First entry serves the tier; later entries are fallbacks on 404/429/5xx.
TIERS: dict[Tier, list[str]] = {
    "fast": ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite"],
    "smart": ["gemma-4-26b-a4b-it-maas", "gemini-3.1-flash-lite"],
    "expert": ["gemini-3.8-flash", "gemini-3.5-flash-lite"],
}

QUIZ_TIER: Tier = "fast"


def cost_usd(model_id: str, prompt_tokens: int, output_tokens: int) -> float:
    """Cost of one call. `output_tokens` must include thinking tokens."""
    spec = MODELS[model_id]
    return (
        prompt_tokens * spec.input_per_m + output_tokens * spec.output_per_m
    ) / 1_000_000
