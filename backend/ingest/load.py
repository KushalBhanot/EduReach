"""Ingest OpenStax books into Postgres/pgvector. Idempotent.

    uv run python -m ingest.load                 # all books in ingest/sources.py
    uv run python -m ingest.load --book prealgebra-2e
    uv run python -m ingest.load --remove concepts-biology

Re-running on unchanged sources embeds nothing and changes nothing. Edited
sections get new chunk IDs; their old chunks are deleted (retired) in the same
transaction, so retrieval never sees two versions of one passage. Removing a
book deletes its chunks through ON DELETE CASCADE.

Embeddings are cached on disk by sha256(model, dim, text), so rebuilding the
database does not pay for them again.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from xml.etree import ElementTree as ET

import psycopg
from google.genai import errors
from pgvector.psycopg import register_vector

from app.db import SCHEMA, database_url
from app.embeddings import EMBED_DIM, EMBED_MODEL, EMBED_PRICE_PER_M, embed_documents
from app.genai_client import backend_name, make_client

from .chunk import Chunk, chunk_section
from .parse import MD, parse_book
from .sources import BOOKS, BOOKS_BY_SLUG, BookSource

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
CACHE = ROOT / "data" / "embed_cache"
CHUNKS_OUT = ROOT / "data" / "chunks.jsonl"
# Small batches stay under the Developer API free tier's tokens-per-minute
# limit; on Vertex this can go up to 100 (EMBED_BATCH env var).
EMBED_BATCH = int(os.environ.get("EMBED_BATCH", "20"))


def _quota_info(e: errors.APIError) -> tuple[str, float | None]:
    """Which quota a 429 hit, and the server's suggested retry delay."""
    details = e.details.get("error", {}).get("details", []) if isinstance(e.details, dict) else []
    quotas, wait = [], None
    for d in details:
        quotas += [v.get("quotaId", "?") for v in d.get("violations", []) or []]
        if d.get("retryDelay"):
            wait = float(str(d["retryDelay"]).rstrip("s")) + 1
    return ",".join(quotas) or str(e.message)[:80], wait


def _cache_key(text: str) -> str:
    return hashlib.sha256(f"{EMBED_MODEL}|{EMBED_DIM}|{text}".encode()).hexdigest()


def _embed_with_cache(client, chunks: list[Chunk]) -> tuple[list[list[float]], int, int]:
    """Returns (vectors, n_from_cache, est_tokens_embedded_now)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    vectors: dict[str, list[float]] = {}
    todo: list[Chunk] = []
    for c in chunks:
        f = CACHE / f"{_cache_key(c.embed_text)}.json"
        if f.exists():
            vectors[c.id] = json.loads(f.read_text())
        else:
            todo.append(c)
    hits = len(chunks) - len(todo)
    est_tokens = sum(len(c.embed_text) // 4 for c in todo)
    step = EMBED_BATCH
    for i in range(0, len(todo), step):
        batch = todo[i:i + step]
        for attempt in range(8):
            try:
                vecs = embed_documents(client, [c.embed_text for c in batch])
                break
            except errors.APIError as e:
                if e.code == 429 or e.code >= 500:
                    quota, wait = _quota_info(e)
                    wait = wait or min(15 * (attempt + 1), 90)
                    print(f"  embed {e.code} {quota}, retrying in {wait:.0f}s", file=sys.stderr)
                    time.sleep(wait)
                    continue
                raise
        else:
            raise RuntimeError("embedding kept failing")
        for c, v in zip(batch, vecs):
            vectors[c.id] = v
            (CACHE / f"{_cache_key(c.embed_text)}.json").write_text(json.dumps(v))
        print(f"  embedded {min(i + step, len(todo))}/{len(todo)}", file=sys.stderr)
    return [vectors[c.id] for c in chunks], hits, est_tokens


def _license(book: BookSource) -> str:
    col = ET.parse(RAW / book.repo / "collections" / f"{book.slug}.collection.xml").getroot()
    lic = col.find(f".//{MD}license")
    return lic.get("url") if lic is not None else ""


def _commit(book: BookSource) -> str:
    return subprocess.run(
        ["git", "-C", str(RAW / book.repo), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def build_chunks(book: BookSource) -> list[Chunk]:
    sections = parse_book(RAW / book.repo, book.slug)
    return [c for s in sections for c in chunk_section(s, book.title)]


def ingest(conn: psycopg.Connection, client, book: BookSource) -> dict:
    lic = _license(book)
    if lic != book.expected_license:
        raise SystemExit(f"{book.slug}: license is {lic!r}, expected {book.expected_license!r}. Stopping.")
    chunks = build_chunks(book)
    ids = {c.id for c in chunks}
    if len(ids) != len(chunks):
        raise SystemExit(f"{book.slug}: duplicate chunk IDs")

    existing = {r[0] for r in conn.execute("SELECT id FROM chunks WHERE book = %s", (book.slug,))}
    new = [c for c in chunks if c.id not in existing]
    retired = existing - ids
    vectors, cache_hits, est_tokens = _embed_with_cache(client, new) if new else ([], 0, 0)

    with conn.transaction():
        conn.execute(
            """INSERT INTO sources (book, title, subject, grade_min, grade_max, license_url,
                                    source_repo, source_commit)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (book) DO UPDATE SET
                 title = EXCLUDED.title, subject = EXCLUDED.subject,
                 grade_min = EXCLUDED.grade_min, grade_max = EXCLUDED.grade_max,
                 license_url = EXCLUDED.license_url, source_repo = EXCLUDED.source_repo,
                 source_commit = EXCLUDED.source_commit, ingested_at = now()""",
            (book.slug, book.title, book.subject, book.grade_min, book.grade_max, lic,
             f"github.com/openstax/{book.repo}", _commit(book)),
        )
        if retired:
            conn.execute("DELETE FROM chunks WHERE id = ANY(%s)", (list(retired),))
        with conn.cursor() as cur:
            cur.executemany(
                """INSERT INTO chunks (id, book, module_id, section_id, section_title, heading,
                                       ordinal, content, word_count, content_hash, source_url,
                                       embed_model, embedding)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                [(c.id, c.book, c.module_id, c.section_id, c.section_title, c.heading,
                  c.ordinal, c.content, c.word_count, c.content_hash, c.source_url,
                  f"{EMBED_MODEL}@{EMBED_DIM}", v) for c, v in zip(new, vectors)],
            )
    return {
        "book": book.slug, "chunks": len(chunks), "inserted": len(new),
        "unchanged": len(chunks) - len(new), "retired": len(retired),
        "embed_cache_hits": cache_hits, "est_embed_tokens": est_tokens,
        "est_embed_cost_usd": round(est_tokens * EMBED_PRICE_PER_M / 1e6, 4),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", action="append", help="slug(s) to ingest; default all")
    ap.add_argument("--remove", help="delete a book and all of its chunks")
    args = ap.parse_args()

    url = database_url()
    if not url:
        raise SystemExit("Set DATABASE_URL")
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(SCHEMA)
        register_vector(conn)
        if args.remove:
            n = conn.execute("DELETE FROM sources WHERE book = %s", (args.remove,)).rowcount
            print(json.dumps({"removed": args.remove, "rows": n}))
            return
        books = [BOOKS_BY_SLUG[s] for s in args.book] if args.book else BOOKS
        client = make_client()
        print(f"embedding via {backend_name()} ({EMBED_MODEL}, {EMBED_DIM} dims)", file=sys.stderr)
        all_chunks = []
        for book in books:
            start = time.perf_counter()
            stats = ingest(conn, client, book)
            stats["seconds"] = round(time.perf_counter() - start, 1)
            print(json.dumps(stats))
            all_chunks.extend(build_chunks(book))
        CHUNKS_OUT.write_text("".join(json.dumps(c.to_dict()) + "\n" for c in all_chunks))


if __name__ == "__main__":
    main()
