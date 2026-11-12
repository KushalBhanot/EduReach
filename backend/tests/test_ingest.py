"""Parser and chunker on small CNXML snippets (no network, no database)."""

from xml.etree import ElementTree as ET

from ingest.chunk import chunk_section
from ingest.parse import Section, clean, math_to_text

M = "http://www.w3.org/1998/Math/MathML"


def mathml(inner: str) -> ET.Element:
    return ET.fromstring(f'<m:math xmlns:m="{M}">{inner}</m:math>')


def test_fraction_and_power_become_plain_text():
    frac = mathml("<m:mfrac><m:mn>3</m:mn><m:mrow><m:mi>x</m:mi><m:mo>+</m:mo><m:mn>1</m:mn></m:mrow></m:mfrac>")
    assert math_to_text(frac) == "3/(x+1)"
    sup = mathml("<m:msup><m:mi>x</m:mi><m:mn>2</m:mn></m:msup>")
    assert math_to_text(sup) == "x^2"
    assert math_to_text(mathml("<m:msqrt><m:mn>16</m:mn></m:msqrt>")) == "sqrt(16)"


def test_clean_drops_table_and_figure_debris():
    raw = "Look at the chart ().\n|\nSimplify. |\nSolution:\nSolution\n-\n"
    assert clean(raw) == "Look at the chart .\nSimplify.\nSolution:"


def section(text: str) -> Section:
    return Section(book="b", module_id="m1", section_id="1.2", chapter_title="Ch",
                   title="Add Whole Numbers", url="https://x", text=text,
                   parts=[("Add Whole Numbers", text)])


def test_chunk_ids_are_stable_and_change_with_content():
    text = "\n".join(f"Paragraph {i} " + "word " * 60 for i in range(10))
    a = chunk_section(section(text), "Book")
    b = chunk_section(section(text), "Book")
    assert [c.id for c in a] == [c.id for c in b]
    assert len(a) > 1 and all(c.word_count <= 280 + 70 for c in a)
    edited = chunk_section(section(text.replace("Paragraph 0", "Paragraph zero")), "Book")
    assert edited[0].id != a[0].id
    assert edited[-1].id == a[-1].id  # untouched tail keeps its id


def test_embed_text_carries_breadcrumb_but_content_does_not():
    c = chunk_section(section("To add whole numbers, line up the place values. " * 5), "Prealgebra 2e")[0]
    assert c.embed_text.startswith("Prealgebra 2e > Ch > 1.2 Add Whole Numbers")
    assert not c.content.startswith("Prealgebra")
