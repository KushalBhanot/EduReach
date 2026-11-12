"""Day 1 smoke test: call every model in every tier with the config the API uses.

    uv run python -m scripts.hello_vertex --project YOUR_PROJECT_ID

A model that errors (e.g. 404 = not enabled for this project) is reported,
not fatal, so one run shows which tier chains actually work.
"""

import argparse
import asyncio
import time

from google import genai
from google.genai import errors, types

from app.llm import _config
from app.models import MODELS, cost_usd


async def probe(client: genai.Client, model_id: str) -> None:
    contents = [types.Content(role="user", parts=[types.Part(text="What is 7 x 8? One sentence.")])]
    start = time.perf_counter()
    try:
        r = await client.aio.models.generate_content(
            model=model_id, contents=contents, config=_config(model_id, "You are a tutor.", False, None)
        )
    except errors.APIError as e:
        print(f"FAIL {model_id}: {e.code} {str(e.message)[:150]}")
        return
    ms = (time.perf_counter() - start) * 1000
    u = r.usage_metadata
    out = (u.candidates_token_count or 0) + (u.thoughts_token_count or 0)
    print(f"OK   {model_id}: {ms:.0f} ms | in={u.prompt_token_count} out={u.candidates_token_count} "
          f"thoughts={u.thoughts_token_count} | ${cost_usd(model_id, u.prompt_token_count or 0, out):.6f}")
    print(f"     {r.text.strip()[:120]!r}")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--location", default="global")
    args = parser.parse_args()
    client = genai.Client(vertexai=True, project=args.project, location=args.location)
    for model_id in MODELS:
        await probe(client, model_id)


if __name__ == "__main__":
    asyncio.run(main())
