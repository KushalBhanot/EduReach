"""A stand-in for genai.Client: returns scripted responses or raises scripted errors."""

from types import SimpleNamespace

from google.genai import errors, types


def response(text: str, thought: str | None = None, prompt=100, output=20, thoughts=0):
    parts = []
    if thought:
        parts.append(types.Part(text=thought, thought=True))
    parts.append(types.Part(text=text))
    return types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(role="model", parts=parts))],
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=prompt,
            candidates_token_count=output,
            thoughts_token_count=thoughts,
        ),
    )


def api_error(code: int) -> errors.APIError:
    cls = errors.ServerError if code >= 500 else errors.ClientError
    return cls(code, {"error": {"code": code, "message": f"fake {code}"}})


class FakeClient:
    """`script` maps model id -> list of responses/exceptions, consumed in order."""

    def __init__(self, script: dict[str, list]):
        self.script = {k: list(v) for k, v in script.items()}
        self.calls: list[dict] = []
        self.aio = SimpleNamespace(models=SimpleNamespace(generate_content=self._generate))

    async def _generate(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        outcome = self.script[model].pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
