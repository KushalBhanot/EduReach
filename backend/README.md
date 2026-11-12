# EduReach API

FastAPI service that the EduReach app calls instead of calling Gemini from the phone. Runs on Cloud Run and calls Gemini/Gemma through Vertex AI using the service account. There is no API key in the app.

Math and Science answers for grades 6 to 10 are grounded in three OpenStax textbooks stored in Postgres with pgvector. Each answer cites the sections it used, or says that it isn't from the textbook.

```
question ─▶ scope check (subject, grade) ─▶ embed (gemini-embedding-001, 768-d)
         ─▶ top-5 chunks by cosine similarity, filtered by subject and grade band (pgvector HNSW)
         ─▶ Gemini with numbered passages [S1]..[S5] ─▶ citations parsed into `sources`
         ─▶ `grounding`: cited | insufficient | out_of_scope | unavailable
```

| Route | Purpose |
|---|---|
| `GET /health` | Liveness (`/healthz` also works locally; Cloud Run reserves paths ending in `z`) |
| `POST /v1/ask` | Tutor answer for `{subject, grade, language, tier, history, question, deepThinking, clientRequestId}`. Returns `sources[]` and `grounding` |
| `POST /v1/quiz` | 3 MCQs from an explanation, via Gemini structured output |

Tiers map to model chains in [app/models.py](app/models.py). The first model serves the tier; on 404/429/5xx the next model takes over and the response says `usedFallback: true`.

Every request writes one JSON log line (Cloud Logging parses it): `request_id`, `route`, `status`, `latency_ms`, `generate_ms`, `model`, `used_fallback`, `failed_attempts`, `prompt_tokens`, `output_tokens` (incl. thinking), `thought_tokens`, `output_tokens_per_sec`, `cost_usd`, `rag_used`, `grounding`, `rag_embed_ms`, `rag_search_ms`, `rag_top_score`, `rag_passages`, `rag_cited`.

## Corpus and ingestion

| Book | Subject | Grades | License |
|---|---|---|---|
| OpenStax Prealgebra 2e | Math | 6 to 8 | CC BY-NC-SA 4.0 |
| OpenStax Elementary Algebra 2e | Math | 8 to 10 | CC BY-NC-SA 4.0 |
| OpenStax Concepts of Biology | Science | 6 to 10 | CC BY-NC-SA 4.0 |

All three are NonCommercial-ShareAlike. EduReach is a free, non-commercial student project and every answer links back to the source page. If EduReach ever charges money, these books must be swapped for CC BY ones. The license is read from each book's metadata at ingest time; a mismatch with `ingest/sources.py` stops the ingest. Grades 1 to 5 and English have no book, so those questions skip retrieval and return `grounding: "out_of_scope"`.

- `ingest/parse.py` turns OpenStax CNXML into sections. It keeps the teaching text and worked examples, drops exercise sets and quizzes, and converts MathML to plain text.
- `ingest/chunk.py` splits on the book's own headings, then packs paragraphs up to about 280 words with one paragraph of overlap. Each chunk is embedded with a breadcrumb header (book > chapter > section > heading).
- `ingest/load.py` is idempotent. Chunk IDs hash the content, so re-running on unchanged books inserts nothing, edited text replaces only its own chunks, and `--remove BOOK` deletes a book with its chunks. Embeddings are cached on disk, so rebuilding the database costs nothing.

## Local development (no GCP account needed)

Postgres with pgvector:

```bash
docker run -d --name edureach-pg -e POSTGRES_PASSWORD=dev -e POSTGRES_DB=edureach -p 5433:5432 pgvector/pgvector:pg17
```

Fetch the book sources (sparse clone, text only, about 50 MB):

```bash
mkdir -p data/raw && cd data/raw && for r in osbooks-prealgebra-bundle osbooks-biology-bundle; do git clone --depth 1 --filter=blob:none --sparse https://github.com/openstax/$r.git && (cd $r && git sparse-checkout set --no-cone 'collections/*' 'META-INF/*' '/modules/*/index.cnxml'); done
```

Before GCP is set up, the backend can use the Gemini Developer API with a key in `GEMINI_API_KEY`. That key lives only in your shell, never in the app.

```bash
export GEMINI_API_KEY=... DATABASE_URL=postgresql://postgres:dev@localhost:5433/edureach
```

```bash
uv run python -m ingest.load
```

The free tier allows only a few thousand embedding tokens per minute, so a full ingest takes about two hours. On Vertex, set `EMBED_BATCH=100` and it takes a couple of minutes.

## Evaluation

```bash
uv run python -m eval.retrieval
```

```bash
uv run python -m eval.answers
```

`eval/questions.jsonl` has 62 questions: 44 answerable, 6 in Hindi, Spanish or French, 10 in-scope questions the books don't cover, and 2 outside every book. Each answerable question lists the section(s) that answer it. `eval.retrieval` reports hit@k and MRR for vector, keyword and hybrid search, plus the similarity gap between covered and uncovered questions. `eval.answers` runs every question through `/v1/ask` with and without retrieval, then reports grounding outcomes, citation precision, latency per stage, tokens and cost. It also writes a side-by-side sheet for human review. Results are in [docs/results.md](../docs/results.md).

Database integration tests run against a scratch database:

```bash
docker exec edureach-pg createdb -U postgres edureach_test
```

```bash
TEST_DATABASE_URL=postgresql://postgres:dev@localhost:5433/edureach_test uv run pytest -q
```

## Local

```bash
uv sync
```

```bash
uv run pytest -q
```

Vertex calls need Application Default Credentials (one-time):

```bash
gcloud auth application-default login
```

Check which models your project can call:

```bash
uv run python -m scripts.hello_vertex --project YOUR_PROJECT_ID
```

Run the API:

```bash
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID uv run uvicorn app.main:app --reload --port 8080
```

Point the app at it by adding `EXPO_PUBLIC_API_BASE_URL=http://localhost:8080` to `.env.local` (Android emulator: `http://10.0.2.2:8080`). Without that variable the app keeps calling Gemini directly, as in v1.

## Config

| Env var | Default | |
|---|---|---|
| `GOOGLE_CLOUD_PROJECT` | (required for Vertex) | Cloud Run does **not** set this for you |
| `GOOGLE_CLOUD_LOCATION` | `global` | Gemini 3.x and Gemma MaaS are served from the global endpoint |
| `RATE_LIMIT_PER_MIN` | `20` | Per device id (`X-Device-Id`) or IP, per instance |
| `DATABASE_URL` | (unset: no retrieval) | Postgres with pgvector. On Cloud Run, a Secret Manager secret with a `/cloudsql/` socket host |
| `DEFAULT_THINKING_LEVEL` | `LOW` | Gemini thinking level when Deep Thinking is off (`MINIMAL`, `LOW`, ...) |
| `GEMINI_API_KEY` | (unset) | Local development only: use the Gemini Developer API instead of Vertex |
| `EMBED_BATCH` | `20` | Texts per embedding call during ingest |

## Deploy (Cloud Run)

The full runbook with Cloud SQL, Secret Manager and the ingest is [deploy/GCP_SETUP.md](deploy/GCP_SETUP.md). The minimal version without retrieval:

One-time: a service account that can only call Vertex AI.

```bash
gcloud iam service-accounts create edureach-api --display-name "EduReach API"
```

```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID --member serviceAccount:edureach-api@YOUR_PROJECT_ID.iam.gserviceaccount.com --role roles/aiplatform.user
```

Build from source (Cloud Build uses the Dockerfile) and deploy:

```bash
gcloud run deploy edureach-api --source . --region us-central1 --service-account edureach-api@YOUR_PROJECT_ID.iam.gserviceaccount.com --allow-unauthenticated --min-instances 0 --max-instances 2 --set-env-vars GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
```

Query the request logs:

```bash
gcloud logging read 'resource.type="cloud_run_revision" AND jsonPayload.message="request"' --limit 20 --format json
```

## Limits (be honest about these)

- The endpoint is unauthenticated. Rate limiting, `max-instances=2` and a billing budget cap the damage; that is not auth. Firebase App Check would be the real fix.
- Rate limiting and `clientRequestId` dedup are in memory, so they apply per instance and reset on cold start.
