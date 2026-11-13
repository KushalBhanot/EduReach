"""EduReach API.

Auth to Vertex AI uses Application Default Credentials: your gcloud login
locally, the Cloud Run service account in production. There is no API key in
the app. (Before GCP is set up, GEMINI_API_KEY in the backend's environment
switches to the Gemini Developer API; see app/genai_client.py.)

With DATABASE_URL set, /v1/ask retrieves textbook passages from
Postgres/pgvector and returns cited sources (app/rag.py).
"""

import ipaddress
import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google import genai
from google.auth.exceptions import DefaultCredentialsError
from google.genai import types
from pydantic import TypeAdapter, ValidationError

from . import llm, rag
from .db import database_url
from .genai_client import make_client
from .guards import IdempotencyCache, RateLimiter
from .models import QUIZ_TIER
from .observability import log_event, trace_field
from .prompts import build_quiz_prompt, build_system_prompt
from .schemas import (
    AskRequest,
    AskResponse,
    LLMQuizItem,
    QuizQuestion,
    QuizRequest,
    QuizResponse,
    Source,
    Turn,
)

# Older turns are dropped before calling the model: they cost input tokens on
# every request and rarely change a tutoring answer.
MAX_HISTORY_TURNS = 20


def to_contents(history: list[Turn], question: str) -> list[types.Content]:
    """`question` is the final user turn as sent to the model (with sources, if any)."""
    turns = history[-MAX_HISTORY_TURNS:]
    contents = [
        types.Content(
            role="model" if t.role == "assistant" else "user",
            parts=[types.Part(text=t.content)],
        )
        for t in turns
    ]
    contents.append(types.Content(role="user", parts=[types.Part(text=question)]))
    return contents


def error(status: int, code: str, request_id: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": code, "requestId": request_id})


def create_app(
    client: genai.Client | None = None,
    retriever: rag.Retriever | None = None,
) -> FastAPI:
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    limiter = RateLimiter(int(os.environ.get("RATE_LIMIT_PER_MIN", "20")))
    # Ceiling on model calls per instance per hour, whoever sends them: with
    # max-instances=1 this bounds what an abusive client can spend.
    hourly = RateLimiter(int(os.environ.get("MAX_MODEL_CALLS_PER_HOUR", "300")), window_s=3600)
    idempotency = IdempotencyCache()
    pool = None
    if retriever is None and (url := database_url()):
        pool = rag.make_pool(url)
        retriever = rag.Retriever(pool)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if pool is not None:
            await pool.open(wait=False)
        yield
        if pool is not None:
            await pool.close()

    app = FastAPI(title="EduReach API", version="2.1.0", lifespan=lifespan)
    # Native apps don't need CORS; this keeps `expo start --web` working.
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    def get_client() -> genai.Client:
        nonlocal client
        if client is None:
            client = make_client()
        return client

    @app.middleware("http")
    async def request_log(request: Request, call_next):
        request.state.request_id = uuid.uuid4().hex
        request.state.log = {}
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except DefaultCredentialsError:
            # No gcloud login locally, or no service account on Cloud Run.
            request.state.log["error"] = "no Google credentials (run: gcloud auth application-default login)"
            response = error(503, "backend_misconfigured", request.state.request_id)
        except Exception as e:
            request.state.log["error"] = f"{type(e).__name__}: {e}"[:500]
            response = error(500, "internal_error", request.state.request_id)
        if request.url.path not in ("/health", "/healthz"):
            log_event(
                "request",
                severity="ERROR" if response.status_code >= 500 else "INFO",
                request_id=request.state.request_id,
                route=request.url.path,
                status=response.status_code,
                latency_ms=round((time.perf_counter() - start) * 1000, 1),
                **request.state.log,
                **trace_field(project, request.headers.get("x-cloud-trace-context")),
            )
        return response

    # Proxies append the address they saw to the RIGHT of X-Forwarded-For; anything to
    # the left can be sent by the client. So the caller is the entry TRUSTED_PROXY_HOPS
    # from the right (Cloud Run's front end appends one; verified live, see GCP_SETUP.md).
    # 0 ignores the header (local runs with no proxy).
    trusted_hops = int(os.environ.get("TRUSTED_PROXY_HOPS", "1"))
    log_forwarded = os.environ.get("LOG_FORWARDED") == "1"  # temporary diagnostics only

    def caller_ip(request: Request) -> str:
        entries = [x.strip() for x in request.headers.get("x-forwarded-for", "").split(",") if x.strip()]
        if log_forwarded:
            request.state.log["xff_entries"] = entries
        if trusted_hops > 0 and len(entries) >= trusted_hops:
            return entries[-trusted_hops]
        return request.client.host if request.client else "unknown"

    def rate_key(request: Request) -> str:
        """Caller IP. The device header is chosen by the client, so it can't be the limit key.

        IPv6 callers are grouped by /64: one subscriber usually controls a whole /64, so
        limiting single addresses would let them rotate past the limit.
        """
        ip = caller_ip(request)
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return "ip:" + ip
        if addr.version == 6:
            return "ip6:" + str(ipaddress.ip_network(f"{addr}/64", strict=False))
        return "ip:" + str(addr)

    def allowed(request: Request) -> str | None:
        if not limiter.allow(rate_key(request)):
            return "rate_limited"
        if not hourly.allow("all"):
            request.state.log["hourly_cap_hit"] = True
            return "busy"
        return None

    def client_key(request: Request) -> str:
        device = request.headers.get("x-device-id")
        if device:
            return "device:" + device[:64]
        return "ip:" + (request.client.host if request.client else "unknown")

    def record(request: Request, result: llm.GenerationResult, **extra) -> None:
        request.state.log.update(
            model=result.model,
            used_fallback=result.used_fallback,
            failed_attempts=[a.__dict__ for a in result.failed_attempts],
            prompt_tokens=result.prompt_tokens,
            output_tokens=result.output_tokens,
            thought_tokens=result.thought_tokens,
            generate_ms=round(result.latency_ms, 1),
            output_tokens_per_sec=round(result.output_tokens_per_sec, 1),
            cost_usd=round(result.cost_usd, 8),
            **extra,
        )

    # Cloud Run's front end reserves paths ending in "z" (e.g. /healthz returns
    # Google's own 404), so /health is the one to use there.
    @app.get("/health")
    @app.get("/healthz")
    async def healthz():
        return {"ok": True}

    @app.post("/v1/ask", response_model=AskResponse, response_model_by_alias=True)
    async def ask(body: AskRequest, request: Request):
        rid = request.state.request_id
        key = client_key(request)
        request.state.log.update(tier=body.tier, subject=body.subject, grade=body.grade,
                                 language=body.language, deep_thinking=body.deep_thinking,
                                 rag_used=False, grounding="none")

        cache_key = f"{key}:{body.client_request_id}" if body.client_request_id else None
        if cache_key and (cached := idempotency.get(cache_key)) is not None:
            request.state.log["idempotent_replay"] = True
            return cached

        if (blocked := allowed(request)) is not None:
            return error(429, blocked, rid)

        retrieval, grounding = None, "none"
        model_question = body.question
        if retriever is not None:
            try:
                retrieval = await retriever.search(
                    get_client(),
                    rag.retrieval_query(body.question, [(t.role, t.content) for t in body.history]),
                    body.subject,
                    body.grade,
                )
            except Exception as e:  # DB or embedding outage: answer, but say it's unsourced
                request.state.log["rag_error"] = f"{type(e).__name__}: {e}"[:300]
                grounding = "unavailable"
            else:
                request.state.log.update(
                    rag_in_scope=retrieval.in_scope,
                    rag_embed_ms=round(retrieval.embed_ms, 1),
                    rag_search_ms=round(retrieval.search_ms, 1),
                    rag_top_score=retrieval.top_score and round(retrieval.top_score, 4),
                    rag_passages=[p.id for p in retrieval.passages],
                )
                if retrieval.passages:
                    model_question = rag.build_grounded_question(
                        body.question, retrieval.passages, body.subject, body.grade
                    )
                    request.state.log.update(rag_used=True, rag_prompt=rag.RAG_PROMPT_VERSION)
                else:
                    grounding = "out_of_scope"

        try:
            result = await llm.generate(
                get_client(),
                body.tier,
                to_contents(body.history, model_question),
                system=build_system_prompt(body.subject, body.grade, body.language),
                deep_thinking=body.deep_thinking,
            )
        except llm.QuotaExhaustedError:
            return error(429, "quota_exhausted", rid)
        except llm.UpstreamError as e:
            request.state.log["error"] = str(e)
            return error(502, "upstream_error", rid)

        answer, sources = result.text, []
        if retrieval is not None and retrieval.passages:
            g = rag.postprocess(result.text, retrieval.passages)
            answer, grounding = g.text, g.grounding
            # Several chunks can come from one section: cite each section once.
            seen: set[tuple[str, str]] = set()
            for p in g.cited:
                if (p.book, p.section_id) not in seen:
                    seen.add((p.book, p.section_id))
                    sources.append(Source(book=p.book_title, section_id=p.section_id,
                                          title=p.section_title, url=p.url))
            request.state.log["rag_cited"] = [p.id for p in g.cited]
        request.state.log["grounding"] = grounding
        record(request, result)
        response = AskResponse(
            answer=answer,
            thinking=result.thinking,
            actual_model=result.model,
            used_fallback=result.used_fallback,
            sources=sources,
            grounding=grounding,
            request_id=rid,
        )
        if cache_key:
            idempotency.put(cache_key, response)
        return response

    quiz_items = TypeAdapter(list[LLMQuizItem])

    @app.post("/v1/quiz", response_model=QuizResponse, response_model_by_alias=True)
    async def quiz(body: QuizRequest, request: Request):
        rid = request.state.request_id
        if (blocked := allowed(request)) is not None:
            return error(429, blocked, rid)
        prompt = build_quiz_prompt(body.subject, body.grade, body.language, body.explanation)
        try:
            result = await llm.generate(
                get_client(),
                QUIZ_TIER,
                [types.Content(role="user", parts=[types.Part(text=prompt)])],
                response_schema=list[LLMQuizItem],
            )
        except llm.QuotaExhaustedError:
            return error(429, "quota_exhausted", rid)
        except llm.UpstreamError as e:
            request.state.log["error"] = str(e)
            return error(502, "upstream_error", rid)

        # The schema fixes the JSON shape, not the content: drop any item
        # without exactly 4 options or with an out-of-range answer.
        questions: list[QuizQuestion] = []
        try:
            for item in quiz_items.validate_json(result.text):
                try:
                    questions.append(QuizQuestion(**item.model_dump()))
                except ValidationError:
                    continue
        except ValidationError:
            pass
        record(request, result, quiz_questions=len(questions))
        if not questions:
            return error(502, "bad_quiz", rid)
        return QuizResponse(questions=questions[:3], request_id=rid)

    return app


app = create_app()
