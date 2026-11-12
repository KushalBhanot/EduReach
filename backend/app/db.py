"""Postgres + pgvector schema and connection setup.

Locally: DATABASE_URL=postgresql://postgres:dev@localhost:5433/edureach
(docker run pgvector/pgvector:pg17, see README).
Cloud Run + Cloud SQL: a unix-socket URL such as
postgresql://edureach_api:...@/edureach?host=/cloudsql/PROJECT:REGION:INSTANCE
"""

from __future__ import annotations

import os

SCHEMA = """
CREATE EXTENSION IF NOT EXISTS vector;

-- One row per ingested book: where it came from and under what license.
CREATE TABLE IF NOT EXISTS sources (
    book            text PRIMARY KEY,
    title           text NOT NULL,
    subject         text NOT NULL,
    grade_min       int  NOT NULL,
    grade_max       int  NOT NULL,
    license_url     text NOT NULL,
    source_repo     text NOT NULL,
    source_commit   text NOT NULL,
    enabled         boolean NOT NULL DEFAULT true,
    ingested_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
    id              text PRIMARY KEY,
    book            text NOT NULL REFERENCES sources(book) ON DELETE CASCADE,
    module_id       text NOT NULL,
    section_id      text NOT NULL,
    section_title   text NOT NULL,
    heading         text NOT NULL,
    ordinal         int  NOT NULL,
    content         text NOT NULL,
    word_count      int  NOT NULL,
    content_hash    text NOT NULL,
    source_url      text NOT NULL,
    embed_model     text NOT NULL,
    embedding       vector(768) NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw
    ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS chunks_book ON chunks (book);

-- Keyword index for the full-text baseline and hybrid retrieval.
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS tsv tsvector
    GENERATED ALWAYS AS (
        to_tsvector('english', section_title || ' ' || heading || ' ' || content)
    ) STORED;
CREATE INDEX IF NOT EXISTS chunks_tsv ON chunks USING gin (tsv);
"""


def database_url() -> str | None:
    return os.environ.get("DATABASE_URL")
