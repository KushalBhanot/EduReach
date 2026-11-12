"""Retrieval eval: does the right textbook section come back?

    uv run python -m eval.retrieval            # needs DATABASE_URL and model access

For each question in eval/questions.jsonl:
- answerable/multilingual: a hit is any retrieved chunk whose (book, section)
  is in the question's gold list. Reports hit@1/3/5 and MRR@10 per search
  mode (vector, keyword, hybrid).
- unsupported: records the best cosine similarity, to calibrate MIN_SCORE
  (the gate that turns "nothing relevant" into grounding=out_of_scope).

Query embeddings are computed once and cached in data/eval_cache/, so modes are
compared on identical inputs. Writes eval/out/retrieval.json and prints a
markdown table for docs/results.md.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import statistics
from pathlib import Path

from app import rag
from app.db import database_url
from app.genai_client import backend_name, make_client

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS = ROOT / "eval" / "questions.jsonl"
OUT = ROOT / "eval" / "out"
CACHE = ROOT / "data" / "eval_cache"
MODES = ["vector", "keyword", "hybrid"]


def load_questions() -> list[dict]:
    return [json.loads(line) for line in QUESTIONS.read_text().splitlines() if line.strip()]


class CachedQueryClient:
    """Wraps the genai client so each question is embedded once across modes and runs."""

    def __init__(self, client):
        self._client = client
        outer = self

        class _Models:
            async def embed_content(self, *, model, contents, config):
                key = hashlib.sha256(f"{model}|{config.output_dimensionality}|{config.task_type}|{contents[0]}".encode()).hexdigest()
                f = CACHE / f"{key}.json"
                if f.exists():
                    from google.genai import types
                    return types.EmbedContentResponse(embeddings=[types.ContentEmbedding(values=json.loads(f.read_text()))])
                for attempt in range(8):
                    try:
                        resp = await outer._client.aio.models.embed_content(model=model, contents=contents, config=config)
                        break
                    except Exception as e:  # free-tier 429s
                        if "429" not in str(e) or attempt == 7:
                            raise
                        await asyncio.sleep(15 * (attempt + 1))
                CACHE.mkdir(parents=True, exist_ok=True)
                f.write_text(json.dumps(resp.embeddings[0].values))
                return resp

        self.aio = type("Aio", (), {"models": _Models()})()


def gold_rank(passages: list[rag.Passage], gold: list[dict]) -> int | None:
    wanted = {(g["book"], g["section"]) for g in gold}
    for i, p in enumerate(passages, start=1):
        if (p.book, p.section_id) in wanted:
            return i
    return None


async def run(loaded_only: bool = False) -> dict:
    qs = load_questions()
    pool = rag.make_pool(database_url())
    await pool.open()
    if loaded_only:  # partial corpus: keep questions whose subject/grade some loaded book covers
        retr = rag.Retriever(pool)
        async with pool.connection() as conn:
            loaded = {r[0] for r in await (await conn.execute("SELECT book FROM sources")).fetchall()}
        qs = [q for q in qs if q["kind"] != "no_corpus" and await retr.in_scope(q["subject"], q["grade"])
              and all(g["book"] in loaded for g in q["gold"])]
    retriever = rag.Retriever(pool, min_score=-1.0)  # no gate: measure raw ranking
    client = CachedQueryClient(make_client())
    per_question = []
    try:
        for q in qs:
            row = {"id": q["id"], "kind": q["kind"], "question": q["question"], "modes": {}}
            for mode in MODES:
                r = await retriever.search(client, q["question"], q["subject"], q["grade"], k=10, mode=mode)
                row["in_scope"] = r.in_scope
                row["top_score"] = r.top_score
                row["modes"][mode] = {
                    "rank": gold_rank(r.passages, q["gold"]) if q["gold"] else None,
                    "top": [f"{p.book}:{p.section_id}" for p in r.passages[:5]],
                    "search_ms": round(r.search_ms, 1),
                }
            per_question.append(row)
    finally:
        await pool.close()
    return {"backend": backend_name(), "questions": per_question}


def summarize(res: dict) -> str:
    rows = res["questions"]
    lines = []
    for label, kinds in [("English questions", {"answerable"}), ("Hindi/Spanish/French questions", {"multilingual"})]:
        subset = [r for r in rows if r["kind"] in kinds]
        if not subset:
            continue
        lines.append(f"\n**{label}**, n={len(subset)}\n")
        lines.append("| Mode | hit@1 | hit@3 | hit@5 | MRR@10 |")
        lines.append("|---|---|---|---|---|")
        for mode in MODES:
            ranks = [r["modes"][mode]["rank"] for r in subset]
            hit = lambda k: sum(1 for x in ranks if x and x <= k)
            mrr = sum(1 / x for x in ranks if x) / len(ranks)
            n = len(ranks)
            lines.append(f"| {mode} | {hit(1)}/{n} | {hit(3)}/{n} | {hit(5)}/{n} | {mrr:.3f} |")

    ans = [r["top_score"] for r in rows if r["kind"] in ("answerable", "multilingual")]
    uns = [r["top_score"] for r in rows if r["kind"] == "unsupported"]
    lines.append("\n**Best cosine similarity: covered vs not covered by the books**\n")
    lines.append("| Set | n | min | median | max |")
    lines.append("|---|---|---|---|---|")
    for name, xs in [("covered", ans), ("not covered", uns)]:
        if not xs:
            continue
        lines.append(f"| {name} | {len(xs)} | {min(xs):.3f} | {statistics.median(xs):.3f} | {max(xs):.3f} |")
    lines.append("\n**What a MIN_SCORE gate would do**\n")
    lines.append("| Threshold | covered questions kept | not-covered questions rejected |")
    lines.append("|---|---|---|")
    for t in [0.55, 0.60, 0.62, 0.64, 0.66, 0.68, 0.70, 0.72]:
        if not ans or not uns:
            break
        kept = sum(1 for x in ans if x >= t)
        rej = sum(1 for x in uns if x < t)
        lines.append(f"| {t:.2f} | {kept}/{len(ans)} | {rej}/{len(uns)} |")
    misses = [r for r in rows if r["kind"] in ("answerable", "multilingual")
              and not (r["modes"]["vector"]["rank"] and r["modes"]["vector"]["rank"] <= 5)]
    lines.append("\n**Vector misses at k=5** (question -> top results)\n")
    for r in misses:
        lines.append(f"- {r['id']} \"{r['question']}\" -> {', '.join(r['modes']['vector']['top'][:3])}")
    no_corpus = [r for r in rows if r["kind"] == "no_corpus"]
    lines.append(f"\nNo-corpus questions skipped retrieval: {sum(1 for r in no_corpus if not r['in_scope'])}/{len(no_corpus)}")
    return "\n".join(lines)


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--loaded-only", action="store_true", help="only questions the loaded books can answer")
    args = ap.parse_args()
    res = asyncio.run(run(args.loaded_only))
    OUT.mkdir(parents=True, exist_ok=True)
    name = "retrieval_partial.json" if args.loaded_only else "retrieval.json"
    (OUT / name).write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(summarize(res))


if __name__ == "__main__":
    main()
