"""The corpus manifest: which books are ingested, from where, under what license.

Licenses are read from each book's collection.xml metadata at ingest time and
checked against `expected_license`; a mismatch stops the ingest.
"""

from dataclasses import dataclass

from app.schemas import Subject


@dataclass(frozen=True)
class BookSource:
    slug: str
    title: str
    repo: str  # github.com/openstax/<repo>
    subject: Subject
    grade_min: int
    grade_max: int
    expected_license: str


BOOKS: list[BookSource] = [
    BookSource("prealgebra-2e", "Prealgebra 2e", "osbooks-prealgebra-bundle", "Math", 6, 8,
               "http://creativecommons.org/licenses/by-nc-sa/4.0/"),
    BookSource("elementary-algebra-2e", "Elementary Algebra 2e", "osbooks-prealgebra-bundle", "Math", 8, 10,
               "http://creativecommons.org/licenses/by-nc-sa/4.0/"),
    BookSource("concepts-biology", "Concepts of Biology", "osbooks-biology-bundle", "Science", 6, 10,
               "http://creativecommons.org/licenses/by-nc-sa/4.0/"),
]

BOOKS_BY_SLUG = {b.slug: b for b in BOOKS}
