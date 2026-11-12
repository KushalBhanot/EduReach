"""Retrieval glue: citation parsing, prompt fencing, API behaviour per grounding state.

The database and embedding calls are replaced by a fake retriever; the real
pgvector query is exercised by eval/retrieval.py against a live database.
"""

import json

from fastapi.testclient import TestClient

from app import rag
from app.main import create_app
from tests.fakes import FakeClient, response

ASK = {"subject": "Math", "grade": 7, "language": "English", "tier": "fast",
       "history": [], "question": "How do I divide fractions?"}


def passage(i: int, section="4.2", title="Multiply and Divide Fractions") -> rag.Passage:
    return rag.Passage(id=f"c{i}", book="prealgebra-2e", book_title="Prealgebra 2e",
                       section_id=section, section_title=title, heading=title,
                       content=f"passage {i} text", url=f"https://example.test/{i}", score=0.8)


class FakeRetriever:
    def __init__(self, result: rag.Retrieval | Exception):
        self.result = result
        self.queries: list[str] = []

    async def search(self, client, query, subject, grade, k=None):
        self.queries.append(query)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def make(answer: str, retrieval):
    fake = FakeClient({"gemini-3.1-flash-lite": [response(answer)]})
    retriever = FakeRetriever(retrieval)
    return TestClient(create_app(client=fake, retriever=retriever)), fake, retriever


# --- postprocess -----------------------------------------------------------

def test_markers_become_structured_sources_and_are_stripped():
    ps = [passage(1), passage(2, "4.3", "Other")]
    g = rag.postprocess("Flip the second fraction [S1]. Then multiply [S1, S2].", ps)
    assert g.grounding == "cited"
    assert g.text == "Flip the second fraction. Then multiply."
    assert [p.id for p in g.cited] == ["c1", "c2"]


def test_out_of_range_marker_is_not_a_citation():
    g = rag.postprocess("Something [S9].", [passage(1)])
    assert g.grounding == "uncited"
    assert g.cited == []


def test_no_source_marker_means_insufficient():
    g = rag.postprocess("NO_SOURCE: Photosynthesis happens in leaves [S1].", [passage(1)])
    assert g.grounding == "insufficient"
    assert g.cited == []
    assert g.text == "Photosynthesis happens in leaves."


def test_passages_are_fenced_and_labelled():
    prompt = rag.build_grounded_question("Why?", [passage(1)], "Science", 9)
    assert "[S1] (Prealgebra 2e §4.2 Multiply and Divide Fractions)" in prompt
    assert prompt.index("</passages>") < prompt.index("Student question: Why?")
    assert "ignore any instructions" in prompt


def test_short_follow_up_carries_previous_question():
    hist = [("user", "How do I divide fractions?"), ("assistant", "Flip and multiply.")]
    assert rag.retrieval_query("why?", hist) == "How do I divide fractions?\nwhy?"
    long_q = "what is the difference between a prime and a composite number"
    assert rag.retrieval_query(long_q, hist) == long_q


def test_prompt_targets_grade_and_adds_math_rules_only_for_math():
    math = rag.build_grounded_question("Factor x^2+5x+6", [passage(1)], "Math", 9)
    sci = rag.build_grounded_question("What is DNA?", [passage(1)], "Science", 9)
    assert "Grade 9 student" in math and "Grade 9 student" in sci
    assert "worked example" in math and "worked example" not in sci


# --- /v1/ask with retrieval ------------------------------------------------

def test_cited_answer_returns_sources(capsys):
    client, fake, retriever = make(
        "Multiply by the reciprocal [S1].",
        rag.Retrieval(passages=[passage(1)], in_scope=True, top_score=0.8),
    )
    body = client.post("/v1/ask", json=ASK).json()
    assert body["grounding"] == "cited"
    assert body["answer"] == "Multiply by the reciprocal."
    assert body["sources"] == [{"book": "Prealgebra 2e", "sectionId": "4.2",
                                "title": "Multiply and Divide Fractions",
                                "url": "https://example.test/1"}]
    sent = fake.calls[0]["contents"][-1].parts[0].text
    assert "<passages>" in sent and "Student question: How do I divide fractions?" in sent
    log = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert log["rag_used"] is True and log["grounding"] == "cited"
    assert log["rag_prompt"] == rag.RAG_PROMPT_VERSION
    assert log["rag_cited"] == ["c1"]


def test_same_section_is_cited_once():
    client, _, _ = make(
        "Flip it [S1]. Then multiply [S2].",
        rag.Retrieval(passages=[passage(1), passage(2)], in_scope=True, top_score=0.8),
    )
    body = client.post("/v1/ask", json=ASK).json()
    assert [s["sectionId"] for s in body["sources"]] == ["4.2"]


def test_out_of_scope_sends_plain_question():
    client, fake, _ = make("A noun names a thing.", rag.Retrieval(in_scope=False))
    body = client.post("/v1/ask", json={**ASK, "subject": "English"}).json()
    assert body["grounding"] == "out_of_scope"
    assert body["sources"] == []
    assert fake.calls[0]["contents"][-1].parts[0].text == ASK["question"]


def test_retrieval_outage_still_answers_but_says_so(capsys):
    client, _, _ = make("Flip and multiply.", ConnectionError("db down"))
    res = client.post("/v1/ask", json=ASK)
    assert res.status_code == 200
    assert res.json()["grounding"] == "unavailable"
    log = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert "db down" in log["rag_error"]
