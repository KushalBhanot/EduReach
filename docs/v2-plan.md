# EduReach v2 build plan

**Build window:** Thu Oct 22 to Wed Nov 4, 2026 (14 days)
**Resume update:** Thu Nov 5 · **Apply:** Fri Nov 6 (hard deadline Nov 20)
**Branch:** `edureach-v2`

**Status (Nov 11, late):** RAG is built and running locally against Postgres + pgvector (Days 6 to 10, without GCP). Done: OpenStax ingestion (parse, chunk, idempotent load with a license check), retrieval with citations and abstention in `/v1/ask`, vector/keyword/hybrid search, a 62-question eval set, retrieval and answer eval scripts, and 45 tests including database integration tests. The app shows cited sections and no longer contains the direct-to-Gemini path or any key. Partial results are in `docs/results.md`. Remaining: finish loading 2 of 3 books (free-tier embedding quota), the full eval run, human labels, and the GCP deploy (`backend/deploy/GCP_SETUP.md`, blocked on the trial signup).

**Status (Oct 24):** the code for Days 1–5 that needs no GCP account is written and tested: the backend (`/v1/ask`, `/v1/quiz`, fallback, cost and latency logging, rate limit, dedup; 27 tests), the Dockerfile, the smoke test, and the app's `BackendRepository`. Still blocked on Kushal: GCP account and trial signup, then running the smoke test and the deploy.

## 1. Why v2 exists

The Google Forward Deployed Engineering Intern (Summer 2027) posting has two minimum qualifications that EduReach v1 does not meet:

1. Architecting a production AI system on GCP.
2. A data pipeline that uses a vector database and RAG.

It also lists preferred ones that are cheap to add once the backend exists: LLM metrics (tokens/sec, cost per request), tracing, and an eval pipeline.

v1 is a React Native app that calls the Gemini API directly from the phone. v2 adds a real backend on GCP, grounds answers in open textbooks, and measures quality and cost with numbers Kushal produces himself.

## 2. What changed on Google's side (read this first)

Two things changed in 2026, and they affect both the code and the resume wording:

- **Vertex AI is now called Gemini Enterprise Agent Platform** (announced Apr 22, 2026 at Cloud Next). The APIs, IAM role (`roles/aiplatform.user`) and SDK flag (`vertexai=True`) still use the old name. On the resume, write "Vertex AI" because that is what the job posting and most recruiters search for.
- **Gemini 2.5 Pro, Flash and Flash-Lite were retired on Vertex on Oct 20, 2026.** v1's "Fast" tier uses `gemini-2.5-flash`, so v2 cannot copy that model ID. On Day 1, list the models your project can actually call before choosing tiers.
- **The old `vertexai.generative_models` Python module was removed** (June 2026). Use the `google-genai` SDK: `genai.Client(vertexai=True, project=..., location=...)`. Most blog posts and Stack Overflow answers from 2024–25 still use the old one. If a snippet has `vertexai.init(...)`, it is out of date.

## 3. Architecture

```
 React Native app (Expo)                         GCP project
 ┌──────────────────────────┐        HTTPS       ┌──────────────────────────────────────────┐
 │ ChatScreen → useChat     │ ─────────────────▶ │ Cloud Run: FastAPI (Python)              │
 │   → AIRepository         │  POST /v1/ask      │   ├─ rate limit + request_id             │
 │      BackendRepository   │  POST /v1/quiz     │   ├─ embed query ──────────┐             │
 │ offlineQueue (unchanged) │ ◀───────────────── │   ├─ retrieve top-k ───────┼─▶ Cloud SQL │
 │ no API key in the bundle │  answer + sources  │   │                        │  Postgres + │
 └──────────────────────────┘                    │   │                        │  pgvector   │
                                                 │   ├─ generate ─────────────┼─▶ Vertex AI │
                                                 │   │   (tier → model,       │  Gemini /   │
                                                 │   │    fallback on 429/5xx)│  Gemma MaaS │
                                                 │   └─ JSON log line ──▶ Cloud Logging     │
                                                 │      spans ──────────▶ Cloud Trace       │
                                                 └──────────────────────────────────────────┘
 Offline (laptop, run by hand):
   ingest/  OpenStax source → sections → chunks → embeddings → Cloud SQL
   eval/    questions.jsonl → recall@k, faithfulness → docs/results.md
```

### Key design decisions

| Decision | Choice | Why |
|---|---|---|
| Where the key lives | Nowhere. Cloud Run's **service account** calls Vertex via IAM | Anything in `EXPO_PUBLIC_*` is compiled into the JS bundle. Anyone who unzips the APK can read it. A service account has no secret to leak. |
| App ↔ backend seam | New `BackendRepository` implementing the existing `AIRepository` interface | Your uncommitted refactor (`src/repositories/`, `useChat.ts`) is exactly this seam. `useChat` and the offline queue don't change. |
| What the app sends | The tier (`fast`/`smart`/`expert`), never a model ID | Models can change on the server (like the 2.5 retirement) without an app release. |
| Python SDK | `google-genai` with `vertexai=True` | It's the supported SDK; the legacy one is gone. |
| Vector DB | **pgvector on Cloud SQL for PostgreSQL** | See §5. It's cheap, it's what Google's docs call a vector database, and you learn SQL along the way. |
| Embeddings | `gemini-embedding-001`, `output_dimensionality=768` | pgvector's HNSW index supports at most 2,000 dimensions, and the model's default is 3,072. 768 is plenty for ~10k chunks. |
| Tracing | OpenTelemetry → Cloud Trace exporter, one span per stage (embed, retrieve, generate) | This turns "it's slow" into "retrieval is 40 ms and generation is 1.8 s". |
| Logs | One structured JSON line per request to stdout | Cloud Run sends stdout to Cloud Logging and parses the JSON into fields you can query. You don't need a logging library. |

### API contract

- `GET /healthz` returns `{"ok": true}`
- `POST /v1/ask` takes `{subject, grade, language, tier, history[], question, deepThinking, clientRequestId}` and returns `{answer, thinking, actualModel, usedFallback, sources[], requestId}`
- `POST /v1/quiz` takes `{subject, grade, language, explanation}` and returns `{questions: QuizQuestion[]}`. It uses Gemini **structured output** (`response_schema`) instead of v1's strip-the-fences-and-hope `JSON.parse`.

`clientRequestId` is the offline queue's item id. It lets the backend spot a retried flush and avoid answering (and paying for) the same question twice.

### Model tiers (IDs confirmed on Google's model-versions page, 2026-10-24)

Implemented in `backend/app/models.py`. Fallback happens on 404/429/5xx.

| App tier | Primary | Fallback | Notes |
|---|---|---|---|
| fast | `gemini-3.1-flash-lite` (GA, to May 2027+) | `gemini-3.5-flash-lite` | ~$0.25 in / $1.50 out per 1M tokens |
| smart | `gemma-4-26b-a4b-it-maas` | `gemini-3.1-flash-lite` | Gemma MaaS is **Experimental**, so the fallback matters. Price unconfirmed |
| expert | `gemini-3.8-flash` (GA, to Sep 2027+) | `gemini-3.5-flash-lite` | Intro $0.75 / $3.75 through Dec 31, then reportedly $1.50 / $7.50 |

`gemini-3.5-flash` exists but costs $1.50 / $9.00, more than 3.8 Flash at intro pricing, so it isn't used. The smoke test (`python -m scripts.hello_vertex`) confirms which IDs your project can actually call.

Gemma 4 31B (v1's Expert) does not appear to be offered as a managed API. Self-hosting it on a GPU endpoint costs real money every hour, so don't.

## 4. RAG corpus

- **Source:** OpenStax textbooks. Check every book's license on its own page. Most are **CC BY 4.0**, but some (e.g. Intermediate Algebra 2e) are **CC BY-NC-SA**. Use CC BY books only and record each book's license and URL in `backend/ingest/SOURCES.md`.
- **Candidate books:** *Prealgebra 2e* (≈ grades 6–8), *Elementary Algebra 2e* (≈ grades 8–10), plus one science book (*Concepts of Biology* or the high-school *Physics*). Three books is enough to make a useful set.
- **Honest scope:** OpenStax has nothing for grades 1–5 and no English-language-arts book that fits. So RAG runs for **Math and Science, grades 6–10**. Every other request runs without retrieval, and the log line records `rag_used: false`. Don't claim more than this anywhere.
- **Chunking:** split along the book's own section boundaries first, then into ~300–500-token chunks with a little overlap. Keep `book`, `section_id` (e.g. `2.3`), `section_title`, `subject`, `grade_min`, `grade_max` and `source_url` on every chunk, so answers can cite "OpenStax Prealgebra 2e §2.3".
- **Table sketch (one table):** `chunks(id, book, section_id, section_title, subject, grade_min, grade_max, content, token_count, embedding vector(768), source_url, license)`, with an HNSW index on `embedding` using cosine distance.

## 5. Vector DB options compared

| | **pgvector on Cloud SQL** (pick) | Vertex AI Vector Search | Firestore vector search |
|---|---|---|---|
| Idle cost | ~$8–12/mo (db-f1-micro) + ~$2 storage. Stop the instance when not working and only storage is billed | ~$0.094/node-hour ≈ **$68/mo** for one always-on node, plus index-build charges | $0 within the free quota (default database only) |
| Stores the text too? | Yes, text and vector in the same row | No. It stores IDs and vectors only, so you'd also need a second database for the text | Yes |
| Filtering (subject/grade) | Plain SQL `WHERE` | Filter "restricts", more setup | Pre-filter needs a composite index |
| What it teaches you | SQL, indexes, `EXPLAIN`. You have no SQL on your resume yet | A managed ANN service built for millions of vectors | NoSQL document modeling |
| Fit for ~10k chunks | Good. ~10k × 768 floats ≈ 30 MB | Overkill | Fine |
| Resume signal | "Postgres + pgvector" is widely recognized and appears in Google's own RAG docs | Strong GCP keyword, but too costly for this scale | Weakest "vector database" signal |

**Decision:** pgvector on Cloud SQL. If credits become a problem, Firestore is the fallback. Vector Search is the right tool at millions of vectors. Saying *why* you didn't use it ("cost per month vs corpus size") is a good interview answer in itself.

## 6. Cost estimate

Assumes the $300 GCP free-trial credit (90 days). Prices come from public pricing pages and third-party trackers as of Oct 2026. Check them on Day 1 and correct this table.

| Item | Assumption | Est. cost for the build window |
|---|---|---|
| Cloud Run | Well under the monthly free tier (requests, vCPU-seconds) | ~$0 |
| Artifact Registry | One ~200 MB image, a few versions | <$1 |
| Cloud SQL Postgres | db-f1-micro + 10 GB SSD, running ~2 weeks | ~$5–7 |
| Embedding ingestion | ~2–3M tokens × $0.15/1M, re-embedded ~3× during chunking experiments | ~$1.50 |
| Generation (dev + demo) | ~2,000 requests × ~$0.001 (≈2.5k input + 150 output tokens at Flash-Lite rates) | ~$2 |
| Eval runs | 60 questions × ~3 calls (answer, claim extraction, judge) × ~15 runs | ~$5–8 |
| Logging / Trace | Inside free allotments at this volume | ~$0 |
| **Total** | | **~$15–20** (well inside the credit) |

**Guardrails (Day 1):** a billing budget with alerts at $25 and $50, Cloud Run `--max-instances=2`, and a per-device rate limit in the API. Stop the Cloud SQL instance when you won't work on it for a day or more.

Per-request cost isn't guessed. It's computed from `usage_metadata` (prompt, candidates and **thoughts** token counts; thinking tokens are billed as output) times the price table in the code, logged on every request, and summarized in §8.

## 7. Day-by-day milestones

Each day assumes ~3–4 focused hours around classes. **Done =** what has to be true before you close the laptop.

### Week 1: backend on GCP, key out of the app

| Day | Date | Work | Done = |
|---|---|---|---|
| 1 | Thu Oct 22 | Decide what to do with the uncommitted refactor. Install `gcloud`, create the project, start the trial, set the budget alerts, enable the APIs. Set up local ADC login. Make the `backend/` skeleton with `uv`. Write one 15-line script that calls Gemini through Vertex. List the available models. | Script prints an answer **and** its `usage_metadata`. Real model IDs are written into §3. |
| 2 | Fri Oct 23 | FastAPI `/healthz` + `/v1/ask`. Port `buildSystemPrompt`, the tier → model map and the fallback (429/5xx → next tier) to Python. Pydantic models mirror `AskParams`/`AIResponse`. | `curl` to localhost returns a grade-appropriate answer. Fallback is tested by forcing a bad model ID. |
| 3 | Sat Oct 24 | `/v1/quiz` with `response_schema`. Request-logging middleware: `request_id`, `latency_ms` per stage, tokens, `cost_usd`, `model`, `used_fallback`. `pytest` for the cost function and the prompt builder. | One JSON log line per request with correct cost math. Tests pass. |
| 4 | Sun Oct 25 | Dockerfile. Dedicated service account with only `aiplatform.user` and log writer. Deploy to Cloud Run (`min-instances=0`, `max-instances=2`). Add the rate limit. | Public HTTPS URL answers. Cold-start and warm latency each measured 10× and written down. |
| 5 | Mon Oct 26 | App: `BackendRepository` + `EXPO_PUBLIC_API_BASE_URL` (a URL is fine to be public; a key is not). Delete `EXPO_PUBLIC_GEMMA_API_KEY` usage. **Revoke the old AI Studio key**, since it shipped in v1 builds. Test the offline queue: airplane mode → ask 3 questions → reconnect. | **Milestone A:** app works end to end through Cloud Run. `grep -r "key=" src/` finds nothing. The queue flushes exactly once. |

### Week 2: RAG, eval, metrics

| Day | Date | Work | Done = |
|---|---|---|---|
| 6 | Tue Oct 27 | Pick 3 books, verify licenses, download their source files (CNXML from OpenStax's GitHub book repos, or HTML). Parse into sections and write the chunker. Output `chunks.jsonl`. | Read 20 random chunks by hand. None are cut mid-sentence or are just a figure caption. Chunk count recorded. |
| 7 | Wed Oct 28 | Create the Cloud SQL Postgres instance and enable `vector`. Create the table + HNSW index. Embed with `task_type=RETRIEVAL_DOCUMENT` in batches and insert. | `SELECT count(*)` matches the chunk count. Ingestion time and embedding cost recorded. One hand-run nearest-neighbor query returns sensible sections. |
| 8 | Thu Oct 29 | Retrieval in `/v1/ask`: embed the question (`RETRIEVAL_QUERY`), get top-k filtered by subject and grade band, put the chunks in the prompt with "answer only from these; say so if they don't cover it". Return `sources[]`. Show a small "From OpenStax…" line in `ChatMessage`. OpenTelemetry spans to Cloud Trace. | A Math grade-7 question shows a citation in the app. A trace in Cloud Trace shows the 3 stage spans. |
| 9 | Fri Oct 30 | **Eval set:** 60 questions (30 Math, 30 Science, grades 6–10), each labeled with the gold `section_id`s that answer it, plus 10 questions translated into Hindi/Spanish. Questions and labels are drafted from the books, then Kushal spot-checks the labels against the source. | `backend/eval/questions.jsonl` with 70 rows, labels checked. |
| 10 | Sat Oct 31 | Retrieval eval script: recall@1/3/5 and MRR. Run 2 experiments, e.g. chunk size 300 vs 500, and vector-only vs hybrid (Postgres full-text + vector). | Table of recall@k per variant in `docs/results.md`. Best variant chosen *by the numbers*. |
| 11 | Sun Nov 1 | Faithfulness eval: an LLM judge splits each answer into claims and checks each against the retrieved chunks (use a different model from the one that wrote the answer). **Hand-label 20 answers yourself** and report how often the judge agrees with you. Compare RAG vs no-RAG on the same questions. | Faithfulness % for RAG and no-RAG, plus judge-vs-you agreement (x/20), in `results.md`. |
| 12 | Mon Nov 2 | Load test: 200 requests against Cloud Run. From the logs, compute p50/p95 latency per stage, output tokens/sec, mean and p95 cost per request. Build a Cloud Monitoring dashboard from log-based metrics. Run the multilingual retrieval check. | All §8 numbers are filled in, each with the command that produced it. |
| 13 | Tue Nov 3 | Hardening: DB down → answer without RAG and flag it. Vertex 429 → next tier. Add `clientRequestId` dedup. Update the README architecture section and add a "Results" section. | Kill the DB connection on purpose and the app still answers. README shows the architecture and the numbers. |
| 14 | Wed Nov 4 | Buffer day. Re-run the evals once on the final code, record a 60-second demo, tag `v2.0`. Decide whether to keep Cloud SQL running through interviews (~$10/mo, from credit). | `docs/results.md` is final. Demo link in the README. |
| — | Thu Nov 5 | Resume update with the `kushal-resume` skill: 2 one-line bullets using only measured numbers. | |

**If you fall behind:** cut the hybrid-search experiment (Day 10), the dashboard (Day 12) and the multilingual check, in that order. Never cut the hand-labeled eval set or the judge-agreement check. Those are what make the numbers credible.

## 8. What to measure (feeds the resume bullets)

Record every number in `docs/results.md` with the date, the git commit, and the command that produced it.

| Metric | How | Why it matters |
|---|---|---|
| Retrieval recall@5 (and @1, @3, MRR) | `eval/retrieval.py` over 60 labeled questions | Directly backs the "vector DB + RAG pipeline" qualification |
| Faithfulness, RAG vs no-RAG | LLM judge, claim level, same 60 questions | Shows RAG *helps*, not just that it exists |
| Judge agreement with hand labels | 20 answers you labeled yourself | Tells you whether to trust the faithfulness number at all |
| p50 / p95 end-to-end latency, per stage | Cloud Logging fields from a 200-request load test | Production-system signal |
| Cold start vs warm | 10 requests each after scale-to-zero | An honest trade-off of `min-instances=0` |
| Output tokens/sec | (candidates + thoughts tokens) / generate-stage latency | Named in the preferred qualifications |
| Cost per request (mean, p95) | From `usage_metadata` × price table, logged per request | Named in the preferred qualifications |
| Corpus size, ingestion time and cost | Ingest script output | Context for the bullets ("N sections from 3 books") |
| Multilingual recall@5 | 10 translated questions vs English chunks | Ties back to EduReach's 6-language mission |

**Bullet shapes to aim for** (the numbers are blanks until you've measured them; finalize on Nov 5):

1. *Architected* a FastAPI RAG backend on Cloud Run with Vertex AI Gemini and pgvector over __ OpenStax sections, moving the API key off the client; __ s p95 at $__ per request.
2. *Built* an eval pipeline over __ hand-labeled questions: recall@5 of __%, faithfulness __% → __% vs no-RAG, judge agreement __/20 with hand labels.

## 9. Repo layout (target)

```
backend/
  app/          main.py, prompts.py, models.py (tiers + prices), rag.py, logging.py, tracing.py
  ingest/       parse.py, chunk.py, embed_and_load.py, SOURCES.md
  eval/         questions.jsonl, retrieval.py, faithfulness.py, judge_labels.jsonl
  tests/
  Dockerfile, pyproject.toml, uv.lock
src/repositories/BackendRepository.ts     (new; GemmaRepository stays for reference until Day 5)
docs/v2-plan.md, docs/results.md
```

## 10. Risks

| Risk | Mitigation |
|---|---|
| Model IDs in §3 are wrong or not enabled in the project | Day 1 lists the real models before any code depends on them |
| Cloud Run ↔ Cloud SQL connection trouble | Use Cloud Run's built-in Cloud SQL connection (`--add-cloudsql-instances`) and the Cloud SQL Python Connector. Budget an hour for this on Day 7 |
| Open endpoint gets abused | Rate limit + `max-instances=2` + budget alerts. Real client attestation (Firebase App Check) is a stretch goal, and v2 shouldn't claim it |
| Grade 1–5 and English get no RAG | Documented as scope, logged as `rag_used: false`, and never implied otherwise |
| Overlap with Argus v0 (Nov 6–20), which also has a faithfulness eval | Reuse this judge code in Argus. On the resume, EduReach's bullet is about *retrieval*, Argus's is about *agents* |
| Class load eats days | Cut list in §7. Day 14 is a full buffer |

## 11. Rules for this build

- Claude writes the code; Kushal reviews the diffs and does all git operations (no `git add`/commit/push unless he asks).
- No GCP resource gets created and nothing is installed system-wide (e.g. `brew`) without Kushal saying yes first. Project-local deps (`uv` venv, `yarn`) are normal dev work.
- The 20 hand-labeled faithfulness answers (Day 11) stay a human task: they are the ground truth the judge is measured against.
- No number goes in the README or on the resume unless it's in `docs/results.md` with the command that produced it.
