# EduReach v2: measured results

Every number here comes from a script in `backend/eval/` and a file in `backend/eval/out/`. Nothing in this file is an estimate unless it says so.

**Run date:** Nov 12, 2026. Corpus, embeddings and generation are the production setup: Vertex AI on GCP project `edureach-api-kb`.

## Setup

| | |
|---|---|
| Corpus | 3 OpenStax books, 2,250 chunks: Prealgebra 2e (569), Elementary Algebra 2e (653), Concepts of Biology (1,028) |
| Embeddings | `gemini-embedding-001`, 768 dimensions, Vertex AI |
| Vector store | Postgres 17 + pgvector, HNSW (cosine). Cloud SQL `db-f1-micro` in production; the evals ran against an identical local copy |
| Generator | `gemini-3.1-flash-lite` ("fast" tier) on Vertex AI |
| Questions | `backend/eval/questions.jsonl`: 44 answerable (29 Math, 15 Science), 6 in Hindi/Spanish/French, 10 in-scope but not covered by the books, 2 with no book for the subject/grade |
| Deployment | FastAPI on Cloud Run (`min-instances=0`, `max-instances=2`), Cloud SQL over the built-in connector, DB URL in Secret Manager, no API key anywhere |

**Caveat on the questions.** Claude wrote the questions and their gold-section labels from the books' section titles, as student-style questions. Kushal has not checked them yet. Questions written with the section list in view are probably easier than real student questions, so hit rates are likely optimistic. The similarity threshold was also chosen on this same set.

## Retrieval (`eval.retrieval`)

A hit means a chunk from a gold section is in the top k. Search is filtered by subject and grade band.

| Mode | Questions | hit@1 | hit@3 | hit@5 | MRR@10 |
|---|---|---|---|---|---|
| Vector (pgvector) | 44 English | 41/44 | 44/44 | 44/44 | 0.962 |
| Keyword (Postgres full-text) | 44 English | 28/44 | 35/44 | 38/44 | 0.742 |
| Hybrid (reciprocal rank fusion) | 44 English | 37/44 | 42/44 | 44/44 | 0.905 |
| Vector | 6 Hindi/Spanish/French | 5/6 | 6/6 | 6/6 | 0.917 |
| Keyword | 6 Hindi/Spanish/French | 0/6 | 0/6 | 1/6 | 0.042 |

Vector search beats keyword search, and fusing them made ranking worse, so production uses vector only. Keyword search can't match a Hindi question against English text; the multilingual embedding model can.

**Abstention threshold.** Best cosine similarity per question: covered questions 0.653 to 0.764 (median 0.715), uncovered questions 0.539 to 0.634 (median 0.579). `MIN_SCORE = 0.60` keeps all 50 covered questions and rejects 9 of 10 uncovered ones. It sits below the covered minimum on purpose, because it was picked on this same set.

## Answers through `/v1/ask` (`eval.answers`)

All 62 questions, each sent once with retrieval and once without (the v1 prompt-only setup). Same model for both.

| Question kind | n | cited | insufficient (model said no source) | out of scope (no retrieval match) |
|---|---|---|---|---|
| Answerable, English | 44 | 44 | 0 | 0 |
| Answerable, Hindi/Spanish/French | 6 | 6 | 0 | 0 |
| In scope but not in the books | 10 | 0 | 1 | 9 |
| No book for subject/grade | 2 | 0 | 0 | 2 |

All 50 cited answers cite at least one gold section. All 12 questions the books can't answer were labelled as not from the textbook, either by the similarity gate or by the model's `NO_SOURCE` signal.

### Thinking level (LOW vs MINIMAL), same 62 questions

| Per request, median / p95 | RAG, LOW | RAG, MINIMAL | Prompt-only, LOW |
|---|---|---|---|
| End-to-end latency | 1.79 s / 3.60 s | 1.42 s / 1.77 s | 1.46 s / 1.73 s |
| Query embedding | 216 ms / 488 ms | 206 ms / 511 ms | |
| Vector search | 25 ms / 41 ms | 23 ms / 44 ms | |
| Generation | 1.51 s / 3.15 s | 1.17 s / 1.37 s | 1.46 s / 1.73 s |
| Prompt tokens | 2,022 / 2,789 | 2,022 / 2,789 | 152 / 163 |
| Output tokens (incl. thinking) | 262 / 833 | 138 / 163 | 254 / 285 |
| Cost per 1,000 requests | $0.88 / $1.89 | $0.71 / $0.93 | $0.42 / $0.47 |
| Cited answers citing a gold section | 50/50 | 49/50 | |

These latency numbers were measured in-process from a laptop calling Vertex AI. Retrieval adds about 0.3 s at the median: about 0.2 s to embed the question plus about 25 ms of vector search. It roughly doubles the cost per answer, because five passages add about 1,900 prompt tokens.

MINIMAL thinking gives the same grounding outcomes, a much tighter latency tail, and about 20% lower cost. The default stays LOW until a person compares answer quality. Switching is one environment variable (`DEFAULT_THINKING_LEVEL`).

Cost is computed from token counts times the price table in `backend/app/models.py`, not from a bill.

## Production (Cloud Run, Nov 12)

| | |
|---|---|
| Warm `/v1/ask`, 10 requests from a laptop | median 2.07 s, min 1.44 s, max 4.04 s |
| First request after deploy (cold start included) | 3.3 s |
| Vector search inside Cloud Run (request log) | 16 to 25 ms |
| Ingest into Cloud SQL | 2,250 chunks in about 13 s from the embedding cache. A second run inserted 0 and retired 0 |
| One-time embedding of the corpus | about 467k tokens, estimated $0.07 |

Each request writes one JSON log line to Cloud Logging, with grounding, retrieved and cited chunk IDs, per-stage latency, tokens, model and cost.

## Human grading (Nov 12, Kushal)

20 answers from the LOW run, chosen before grading to span Math and Science, grades 6 to 10, three languages, and questions the books don't cover. 19 were graded. The Spanish one was skipped because the grader doesn't read Spanish. Grades are in `backend/eval/human_grades.jsonl`; the sheet with the cited passages is `backend/eval/out/grading_sheet.md`.

| Measure | Result |
|---|---|
| RAG answer correct and right for the grade | 19/19 |
| Cited passages actually support the answer | 16/16 cited answers (one, q16 sales tax, only partly) |

Which answer was better, RAG or prompt-only:

| Questions | n | RAG better | About the same | Prompt-only better |
|---|---|---|---|---|
| Math | 10 | 1 | 7 | 2 |
| Science | 6 | 3 | 2 | 1 |
| Not covered by the books | 3 | 1 | 2 | 0 |

For the "not covered" rows, neither run had passages (grounding `out_of_scope`), so both answers came from the same prompt-only path. Any preference there is sampling noise, not a RAG effect.

What the notes say:
- **Science: RAG helps.** Answers read like the textbook: more precise terms, and not "too childish" (q42). One exception: the grade-9 DNA replication answer (q34) was harder to follow than the prompt-only one, because Concepts of Biology is a college-level text and the answer kept its density.
- **Math: mostly a wash.** The model already knows grade 6 to 10 math well. Twice, the RAG answer followed the book's procedure and dropped what a student needs most: the mixture-problem answer described the setup without writing the two equations (q28), and the factoring answer used the book's less familiar layout (q20).
- **Grounding works.** No cited answer claimed something its passages didn't back up.

Limits: one grader, not blind (the sheet labelled which answer was RAG), 19 answers, and the questions were written by Claude.

## Prompt v2 (Nov 12): fixing what the grading found

The grounded prompt (`backend/app/rag.py`, `RAG_PROMPT_VERSION = "v2"`) now:
- tells the model to use the passages for facts but explain at the student's grade, without copying textbook wording;
- for Math only: write the key equation(s), show one short worked example (with the student's numbers if given), and use the usual school method.

Same 62 questions, same model, LOW thinking (`eval/out/answers_low_v2.json`):

| | v1 | v2 |
|---|---|---|
| Answerable questions cited, and citing a gold section | 50/50 | 50/50 |
| Uncovered questions labelled not-from-textbook | 12/12 | 12/12 |
| Math answers that show an equation (`=`) | 13/32 | 25/32 |
| Median answer length, Math / Science (words) | 97 / 97 | 100 / 98 |
| RAG latency, median / p95 | 1.79 s / 3.60 s | 1.76 s / 3.89 s |
| Cost per 1,000 RAG requests, median | $0.88 | $0.99 |

On the three answers graded "prompt-only better": q28 now writes both equations and a worked example, q20 uses the "multiply to c, add to b" method, and q34 explains DNA replication in grade-9 language instead of listing Okazaki fragments and ligase. That before/after was judged by Claude reading the answers, not by re-grading. v2 is deployed on Cloud Run (revision `edureach-api-00003`), and every request log carries `rag_prompt`.

## Outage behavior

During a free-tier run, the embedding quota ran out in the middle of the eval. All 11 affected requests still returned an answer, marked `grounding: "unavailable"` with the error in the log, and none returned an error to the app. That run is excluded from the tables above.

## Not yet measured

1. A second, blind grader, and grades for the Spanish and French answers.
2. Questions written by someone other than Claude, or by real students.
3. Cold-start latency after scale-to-zero, measured more than once.
