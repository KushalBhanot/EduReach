"""Parse OpenStax CNXML book sources into sections of plain text.

Input: a local clone of an OpenStax `osbooks-*` bundle (see ingest/SOURCES.md).
Output: one Section per book module, with its chapter.section number, title,
canonical openstax.org URL and the expository text.

Exercise sets, readiness quizzes, "try it" drills and multimedia links are
dropped: they are mostly numbers without explanation and would crowd out the
teaching text at retrieval time. Worked examples and their solutions stay.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

COL = "{http://cnx.rice.edu/collxml}"
MD = "{http://cnx.rice.edu/mdml}"
CNX = "{http://cnx.rice.edu/cnxml}"
MATHML = "{http://www.w3.org/1998/Math/MathML}"

# <section>/<note>/<exercise> classes that are drills, quizzes or links.
SKIP_CLASSES = {
    "try", "be-prepared", "section-exercises", "practice-perfect", "writing",
    "everyday", "self-check", "media-2", "review-exercises", "practice-test",
    "links-to-literacy", "links-to-learning", "sr-contrib-auth", "contrib-auth",
    "multiple-choice", "critical-thinking", "visual-exercise", "interactive",
    "free-response",
}
SKIP_TAGS = {"media", "image", "figure", "metadata", "link", "newline", "label", "colspec"}
BLOCK_TAGS = {"para", "title", "list", "item", "row", "example", "note", "equation",
              "problem", "solution", "definition", "meaning", "table", "section", "figure"}


@dataclass
class Section:
    book: str
    module_id: str
    section_id: str  # "2.3"; chapter intros are "2.0"
    chapter_title: str
    title: str
    url: str
    text: str
    # Subsection headings with their own text, so chunks can carry a heading.
    parts: list[tuple[str, str]] = field(default_factory=list)


def _classes(el: ET.Element) -> set[str]:
    return set((el.get("class") or "").split())


def math_to_text(el: ET.Element) -> str:
    """MathML -> readable plain text (the app never renders LaTeX)."""
    tag = el.tag.replace(MATHML, "")
    kids = list(el)
    if tag in {"mn", "mi", "mo", "mtext"}:
        t = (el.text or "").strip()
        return {"−": "-", "×": "×", "·": "·"}.get(t, t)
    if tag == "mspace":
        return " "
    if tag == "mfrac" and len(kids) == 2:
        a, b = math_to_text(kids[0]), math_to_text(kids[1])
        wrap = lambda s: s if re.fullmatch(r"[\w.]+", s) else f"({s})"
        return f"{wrap(a)}/{wrap(b)}"
    if tag == "msup" and len(kids) == 2:
        return f"{math_to_text(kids[0])}^{math_to_text(kids[1])}"
    if tag == "msub" and len(kids) == 2:
        return f"{math_to_text(kids[0])}_{math_to_text(kids[1])}"
    if tag == "msqrt":
        return "sqrt(" + "".join(math_to_text(k) for k in kids) + ")"
    if tag == "mroot" and len(kids) == 2:
        return f"root{math_to_text(kids[1])}({math_to_text(kids[0])})"
    if tag in {"mtable"}:
        return "; ".join(math_to_text(k) for k in kids)
    if tag in {"mtr"}:
        return " ".join(math_to_text(k) for k in kids)
    return "".join(math_to_text(k) for k in kids)


def _text(el: ET.Element, out: list[str]) -> None:
    tag = el.tag.split("}")[-1]
    if el.tag.startswith(MATHML):
        if tag == "math":
            out.append(" " + re.sub(r"\s+", " ", math_to_text(el)).strip() + " ")
        if el.tail:
            out.append(el.tail)
        return
    if tag in SKIP_TAGS or _classes(el) & SKIP_CLASSES:
        if el.tail:
            out.append(el.tail)
        return
    if tag in BLOCK_TAGS:
        out.append("\n")
    if tag == "item":
        out.append("- ")
    if tag == "solution":
        out.append("Solution: ")
    if el.text:
        out.append(el.text)
    for kid in el:
        _text(kid, out)
    if tag in {"entry"}:
        out.append(" | ")
    if tag in BLOCK_TAGS:
        out.append("\n")
    if el.tail:
        out.append(el.tail)


def clean(s: str) -> str:
    s = re.sub(r"[ \t ]+", " ", s)
    s = re.sub(r" *\n *", "\n", s)
    # Table cells: drop the separators left on their own line or at line end.
    s = re.sub(r"(?m)^[|\s]+$", "", s)
    s = re.sub(r"(?m)\s*\|\s*$", "", s)
    # Figure references whose <link> was dropped leave "()" or "(see )".
    s = re.sub(r"\((?:see )?\s*\)", "", s)
    # Solutions carry their own "Solution" title.
    s = re.sub(r"Solution:\s*\nSolution\b", "Solution:", s)
    # List bullets with nothing after them.
    s = re.sub(r"(?m)^-\s*$", "", s)
    s = re.sub(r"\n{2,}", "\n", s)
    return s.strip()


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def parse_module(path: Path) -> tuple[str, list[tuple[str, str]]]:
    """Returns (title, [(heading, text)]) for one module."""
    root = ET.parse(path).getroot()
    title = (root.findtext(f"{CNX}title") or "").strip()
    content = root.find(f"{CNX}content")
    parts: list[tuple[str, str]] = []
    if content is None:
        return title, parts
    # Text before the first <section> belongs under the module title.
    lead: list[str] = []
    for kid in content:
        if kid.tag == f"{CNX}section" and not (_classes(kid) & SKIP_CLASSES):
            out: list[str] = []
            heading = (kid.findtext(f"{CNX}title") or title).strip()
            for sub in kid:
                if sub.tag != f"{CNX}title":
                    _text(sub, out)
            parts.append((heading, clean("".join(out))))
        else:
            _text(kid, lead)
    lead_text = clean("".join(lead))
    if lead_text:
        parts.insert(0, (title, lead_text))
    return title, [(h, t) for h, t in parts if t]


def parse_book(bundle: Path, slug: str) -> list[Section]:
    col = ET.parse(bundle / "collections" / f"{slug}.collection.xml").getroot()
    sections: list[Section] = []
    # Chapters are subcollections that hold modules directly. Some books
    # (Concepts of Biology) group chapters into units; units are flattened.
    chapters = [
        sub for sub in col.iter(f"{COL}subcollection")
        if sub.find(f"{COL}content").find(f"{COL}module") is not None
    ]
    for ch_no, chapter in enumerate(chapters, start=1):
        ch_title = (chapter.findtext(f"{MD}title") or "").strip()
        modules = chapter.find(f"{COL}content").findall(f"{COL}module")
        has_intro = bool(modules) and _first_is_intro(bundle, modules)
        for idx, mod in enumerate(modules):
            module_id = mod.get("document")
            title, parts = parse_module(bundle / "modules" / module_id / "index.cnxml")
            # OpenStax numbers chapter intros N.0 (URL "N-introduction"),
            # then sections N.1, N.2, ...
            is_intro = idx == 0 and has_intro
            sec_no = 0 if is_intro else idx if has_intro else idx + 1
            section_id = f"{ch_no}.{sec_no}"
            url_slug = f"{ch_no}-introduction" if is_intro else f"{ch_no}-{sec_no}-{slugify(title)}"
            text = "\n\n".join(t for _, t in parts)
            if not text:
                continue
            sections.append(Section(
                book=slug,
                module_id=module_id,
                section_id=section_id,
                chapter_title=ch_title,
                title=title,
                url=f"https://openstax.org/books/{slug}/pages/{url_slug}",
                text=text,
                parts=parts,
            ))
    return sections


def _first_is_intro(bundle: Path, modules: list[ET.Element]) -> bool:
    first = bundle / "modules" / modules[0].get("document") / "index.cnxml"
    title = (ET.parse(first).getroot().findtext(f"{CNX}title") or "").lower()
    return title.startswith("introduction")
