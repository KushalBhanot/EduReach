"""Split parsed sections into retrieval chunks with stable IDs.

Chunks follow the book's own structure first (module -> subsection heading),
then paragraphs, packed up to ~MAX_WORDS with one paragraph of overlap.
Each chunk's embedded text starts with a breadcrumb header
("Prealgebra 2e > Fractions > 4.2 Multiply and Divide Fractions > ..."), so a
short paragraph still carries the topic it belongs to.

IDs are a hash of (book, module, heading, ordinal, content). Re-running on
unchanged sources produces the same IDs, so the loader can skip them; edited
text produces new IDs and the loader retires the old ones.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass

from .parse import Section

MAX_WORDS = 280
MIN_WORDS = 40


@dataclass
class Chunk:
    id: str
    book: str
    module_id: str
    section_id: str
    section_title: str
    heading: str
    ordinal: int
    content: str  # what the model sees and the citation quotes
    embed_text: str  # header + content, what gets embedded
    word_count: int
    content_hash: str
    source_url: str

    def to_dict(self) -> dict:
        return asdict(self)


def _words(s: str) -> int:
    return len(s.split())


def _paragraphs(text: str) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n|\n(?=- )|\n", text) if p.strip()]
    out: list[str] = []
    for p in paras:
        # Very long paragraphs (tables, long solutions) get split on sentences.
        if _words(p) > MAX_WORDS:
            sentences = re.split(r"(?<=[.!?])\s+", p)
            buf: list[str] = []
            for s in sentences:
                if buf and _words(" ".join(buf + [s])) > MAX_WORDS:
                    out.append(" ".join(buf))
                    buf = []
                buf.append(s)
            if buf:
                out.append(" ".join(buf))
        else:
            out.append(p)
    return out


def _pack(paras: list[str]) -> list[str]:
    chunks: list[list[str]] = []
    cur: list[str] = []
    for p in paras:
        if cur and _words("\n".join(cur + [p])) > MAX_WORDS:
            chunks.append(cur)
            # One paragraph of overlap keeps a definition next to its example.
            cur = [cur[-1]] if _words(cur[-1]) < MAX_WORDS // 3 else []
        cur.append(p)
    if cur:
        chunks.append(cur)
    # Fold a tiny tail into the previous chunk.
    if len(chunks) > 1 and _words("\n".join(chunks[-1])) < MIN_WORDS:
        tail = chunks.pop()
        chunks[-1].extend(p for p in tail if p not in chunks[-1])
    return ["\n".join(c) for c in chunks]


def chunk_section(sec: Section, book_title: str) -> list[Chunk]:
    out: list[Chunk] = []
    ordinal = 0
    for heading, text in sec.parts:
        for content in _pack(_paragraphs(text)):
            if _words(content) < 8:
                continue
            crumb = f"{book_title} > {sec.chapter_title} > {sec.section_id} {sec.title}"
            if heading and heading != sec.title:
                crumb += f" > {heading}"
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            cid = hashlib.sha256(
                f"{sec.book}|{sec.module_id}|{heading}|{ordinal}|{content_hash}".encode()
            ).hexdigest()[:24]
            out.append(Chunk(
                id=cid,
                book=sec.book,
                module_id=sec.module_id,
                section_id=sec.section_id,
                section_title=sec.title,
                heading=heading,
                ordinal=ordinal,
                content=content,
                embed_text=f"{crumb}\n\n{content}",
                word_count=_words(content),
                content_hash=content_hash,
                source_url=sec.url,
            ))
            ordinal += 1
    return out
