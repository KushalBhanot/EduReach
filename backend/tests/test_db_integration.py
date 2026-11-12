"""Retriever against a real Postgres + pgvector (skipped unless TEST_DATABASE_URL is set).

    docker exec edureach-pg createdb -U postgres edureach_test
    TEST_DATABASE_URL=postgresql://postgres:dev@localhost:5433/edureach_test uv run pytest -q

Uses hand-made 768-d vectors and a fake embedder, so no model calls are made.
Covers the SQL itself: vector parameter typing, subject/grade filtering,
scope checks, the MIN_SCORE gate, keyword search and cascade deletes.
"""

import asyncio
import os
from types import SimpleNamespace

import psycopg
import pytest
from pgvector import Vector
from pgvector.psycopg import register_vector

from app import rag
from app.db import SCHEMA

URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL not set")


def unit(i: int) -> list[float]:
    v = [0.0] * 768
    v[i] = 1.0
    return v


class FakeEmbedClient:
    def __init__(self, vec):
        async def embed_content(*, model, contents, config):
            return SimpleNamespace(embeddings=[SimpleNamespace(values=vec)])
        self.aio = SimpleNamespace(models=SimpleNamespace(embed_content=embed_content))


@pytest.fixture()
def db():
    with psycopg.connect(URL, autocommit=True) as conn:
        conn.execute("DROP TABLE IF EXISTS chunks, sources CASCADE")
        conn.execute(SCHEMA)
        register_vector(conn)
        conn.execute("""INSERT INTO sources VALUES
            ('pre', 'Prealgebra', 'Math', 6, 8, 'lic', 'repo', 'abc', true, now()),
            ('bio', 'Biology', 'Science', 6, 10, 'lic', 'repo', 'abc', true, now())""")
        rows = [
            ("c1", "pre", "4.2", "Divide fractions", "multiply by the reciprocal of the divisor", unit(0)),
            ("c2", "pre", "5.3", "Fractions and decimals", "divide the numerator by the denominator", unit(1)),
            ("c3", "bio", "5.1", "Photosynthesis", "plants make sugar from light energy", unit(0)),
        ]
        for cid, book, sec, title, text, vec in rows:
            conn.execute(
                """INSERT INTO chunks (id, book, module_id, section_id, section_title, heading, ordinal,
                   content, word_count, content_hash, source_url, embed_model, embedding)
                   VALUES (%s,%s,'m',%s,%s,%s,0,%s,5,'h','u','test',%s)""",
                (cid, book, sec, title, title, text, Vector(vec)),
            )
        yield conn


def search(query_vec, subject="Math", grade=7, mode="vector", min_score=-1.0, query="fractions"):
    async def go():
        pool = rag.make_pool(URL)
        await pool.open()
        try:
            r = rag.Retriever(pool, min_score=min_score, mode=mode)
            return await r.search(FakeEmbedClient(query_vec), query, subject, grade, k=5)
        finally:
            await pool.close()
    return asyncio.run(go())


def test_nearest_chunk_first_and_subject_filter_applied(db):
    r = search(unit(0))
    assert r.in_scope
    assert [p.id for p in r.passages] == ["c1", "c2"]  # bio's c3 matches the vector but is Science
    assert r.passages[0].score == pytest.approx(1.0)


def test_grade_outside_every_book_is_out_of_scope(db):
    r = search(unit(0), grade=9)
    assert not r.in_scope and r.passages == []


def test_min_score_gate_drops_everything_when_best_match_is_weak(db):
    r = search(unit(5), min_score=0.5)  # orthogonal to every stored vector
    assert r.in_scope and r.passages == [] and r.top_score == pytest.approx(0.0)


def test_keyword_mode_uses_full_text(db):
    r = search(unit(5), mode="keyword", query="reciprocal")
    assert [p.id for p in r.passages] == ["c1"]


def test_removing_a_book_cascades_to_its_chunks(db):
    db.execute("DELETE FROM sources WHERE book = 'pre'")
    assert db.execute("SELECT count(*) FROM chunks").fetchone()[0] == 1
