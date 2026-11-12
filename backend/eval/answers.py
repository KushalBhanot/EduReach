"""End-to-end answer eval: RAG vs prompt-only, through the real /v1/ask code path.

    uv run python -m eval.answers [--limit N]

Runs every question in eval/questions.jsonl twice through the FastAPI app
(in-process): once with retrieval (DATABASE_URL set) and once without (the
v1-style prompt-only baseline). Both use the same tier, so the same model.

Automatic measures (no judge model):
- grounding outcome per question kind (cited / insufficient / out_of_scope ...)
- citation precision: share of cited answers whose cited section is a gold one
- latency per stage, tokens and cost per request, from the request log line

What it does NOT measure: whether the answer is correct and actually
supported by the cited passage. That needs a person. The script writes
eval/out/answers_review.md with both answers side by side and empty columns
to fill in; results.md reports those labels only after they're done.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import statistics
import time
from collections import Counter
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app

from .retrieval import OUT, load_questions

PACE_S = float(os.environ.get("EVAL_PACE_S", "4.5"))  # free-tier requests/minute


def call(client: TestClient, q: dict) -> tuple[dict, dict]:
    body = {"subject": q["subject"], "grade": q["grade"], "language": q["language"],
            "tier": "fast", "history": [], "question": q["question"]}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        res = client.post("/v1/ask", json=body)
    logs = [json.loads(line) for line in buf.getvalue().splitlines() if line.startswith("{")]
    log = next((entry for entry in reversed(logs) if entry.get("message") == "request"), {})
    return {"status": res.status_code, **res.json()}, log


def pct(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    if not xs:
        return float("nan")
    i = (len(xs) - 1) * p
    lo, hi = int(i), min(int(i) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--ids", help="comma-separated question ids, e.g. q01,q02")
    ap.add_argument("--out", default="answers", help="output file stem in eval/out/")
    args = ap.parse_args()
    os.environ["RATE_LIMIT_PER_MIN"] = "100000"
    qs = load_questions()
    if args.ids:
        wanted = set(args.ids.split(","))
        qs = [q for q in qs if q["id"] in wanted]
    qs = qs[: args.limit]

    db_url = os.environ.pop("DATABASE_URL", None)
    baseline_app = create_app()  # no retrieval
    if db_url:
        os.environ["DATABASE_URL"] = db_url
    rag_app = create_app()
    if db_url is None:
        raise SystemExit("Set DATABASE_URL")

    rows = []
    with TestClient(rag_app) as rag_client, TestClient(baseline_app) as base_client:
        for q in qs:
            out = {"q": q}
            for name, client in (("rag", rag_client), ("base", base_client)):
                resp, log = call(client, q)
                out[name] = {"resp": resp, "log": log}
                time.sleep(PACE_S)
            rows.append(out)
            g = out["rag"]["resp"].get("grounding")
            print(f"{q['id']} {q['kind']:<12} {g}", flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{args.out}.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    print(summarize(rows))
    write_review(rows, args.out)


def summarize(rows: list[dict]) -> str:
    lines = ["\n**Grounding outcome (RAG run) by question kind**\n",
             "| Kind | n | cited | uncited | insufficient | out_of_scope | error |",
             "|---|---|---|---|---|---|---|"]
    for kind in ["answerable", "multilingual", "unsupported", "no_corpus"]:
        sub = [r for r in rows if r["q"]["kind"] == kind]
        if not sub:
            continue
        c = Counter(r["rag"]["resp"].get("grounding", "error") if r["rag"]["resp"]["status"] == 200 else "error"
                    for r in sub)
        lines.append(f"| {kind} | {len(sub)} | {c['cited']} | {c['uncited']} | {c['insufficient']} | "
                     f"{c['out_of_scope']} | {c['error'] + c['unavailable']} |")

    cited = [r for r in rows if r["rag"]["resp"].get("grounding") == "cited" and r["q"]["gold"]]
    good = 0
    for r in cited:
        gold = {g["section"] for g in r["q"]["gold"]}
        if any(s["sectionId"] in gold for s in r["rag"]["resp"]["sources"]):
            good += 1
    lines.append(f"\nCited answers that cite at least one gold section: {good}/{len(cited)}")

    def stat(name: str, key: str, scale: float = 1.0, fmt: str = "{:.0f}") -> str:
        cells = []
        for mode in ("rag", "base"):
            xs = [r[mode]["log"][key] * scale for r in rows
                  if isinstance(r[mode]["log"].get(key), (int, float))]
            if xs:
                cells.append(f"{fmt.format(statistics.median(xs))} / {fmt.format(pct(xs, 0.95))}")
            else:
                cells.append("n/a")
        return f"| {name} | {cells[0]} | {cells[1]} |"

    lines += ["\n**Per-request cost and latency** (median / p95)\n",
              "| Measure | RAG | Prompt-only |", "|---|---|---|",
              stat("End-to-end latency (ms)", "latency_ms"),
              stat("Query embedding (ms)", "rag_embed_ms"),
              stat("Vector search (ms)", "rag_search_ms", fmt="{:.1f}"),
              stat("Generation (ms)", "generate_ms"),
              stat("Prompt tokens", "prompt_tokens"),
              stat("Output tokens", "output_tokens"),
              stat("Cost per request (USD, x1000)", "cost_usd", 1000, "{:.3f}")]
    models = Counter(r[m]["log"].get("model") for r in rows for m in ("rag", "base"))
    lines.append(f"\nModels that served: {dict(models)}")
    return "\n".join(lines)


def write_review(rows: list[dict], stem: str = "answers") -> None:
    out = ["# Answer review sheet", "",
           "Fill in the last three columns for each row: correct (y/n), supported "
           "(does the cited passage actually back the answer? y/n/na), better (rag/base/same).", ""]
    for r in rows:
        q, rag, base = r["q"], r["rag"]["resp"], r["base"]["resp"]
        srcs = "; ".join(f"{s['book']} §{s['sectionId']}" for s in rag.get("sources", [])) or "none"
        gold = ", ".join(f"§{g['section']}" for g in q["gold"]) or "none"
        out += [f"## {q['id']} ({q['kind']}, {q['subject']} grade {q['grade']}, {q['language']})",
                f"**Q:** {q['question']}  ", f"**Gold:** {gold}  ",
                f"**RAG** [{rag.get('grounding')}; cites {srcs}]: {rag.get('answer', rag)}  ",
                f"**Prompt-only:** {base.get('answer', base)}  ",
                "correct: __ · supported: __ · better: __", ""]
    (OUT / f"{stem}_review.md").write_text("\n".join(out))


if __name__ == "__main__":
    main()
