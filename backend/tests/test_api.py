import json

from fastapi.testclient import TestClient

from app.main import MAX_HISTORY_TURNS, create_app
from tests.fakes import FakeClient, api_error, response

ASK = {
    "subject": "Math",
    "grade": 7,
    "language": "English",
    "tier": "fast",
    "history": [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello!"}],
    "question": "What is a prime number?",
}


def make(script, monkeypatch=None, rate=None):
    if monkeypatch and rate:
        monkeypatch.setenv("RATE_LIMIT_PER_MIN", str(rate))
    fake = FakeClient(script)
    return TestClient(create_app(client=fake)), fake


def test_healthz():
    client, _ = make({})
    assert client.get("/healthz").json() == {"ok": True}


def test_ask_returns_camel_case(capsys):
    client, fake = make({"gemini-3.1-flash-lite": [response("A prime has two factors.")]})
    res = client.post("/v1/ask", json=ASK)
    assert res.status_code == 200
    body = res.json()
    assert body["answer"] == "A prime has two factors."
    assert body["actualModel"] == "gemini-3.1-flash-lite"
    assert body["usedFallback"] is False
    assert body["sources"] == []
    roles = [c.role for c in fake.calls[0]["contents"]]
    assert roles == ["user", "model", "user"]

    log = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert log["route"] == "/v1/ask"
    assert log["model"] == "gemini-3.1-flash-lite"
    assert log["cost_usd"] > 0
    assert log["rag_used"] is False


def test_history_is_trimmed():
    client, fake = make({"gemini-3.1-flash-lite": [response("ok")]})
    long_history = [{"role": "user", "content": str(i)} for i in range(50)]
    client.post("/v1/ask", json={**ASK, "history": long_history})
    assert len(fake.calls[0]["contents"]) == MAX_HISTORY_TURNS + 1


def test_replayed_client_request_id_is_served_from_cache():
    client, fake = make({"gemini-3.1-flash-lite": [response("first")]})
    body = {**ASK, "clientRequestId": "queue-123"}
    headers = {"x-device-id": "dev-1"}
    first = client.post("/v1/ask", json=body, headers=headers).json()
    second = client.post("/v1/ask", json=body, headers=headers).json()
    assert first == second
    assert len(fake.calls) == 1


def test_rate_limit(monkeypatch):
    client, _ = make({"gemini-3.1-flash-lite": [response("1"), response("2")]}, monkeypatch, rate=2)
    headers = {"x-device-id": "dev-2"}
    assert client.post("/v1/ask", json=ASK, headers=headers).status_code == 200
    assert client.post("/v1/ask", json=ASK, headers=headers).status_code == 200
    res = client.post("/v1/ask", json=ASK, headers=headers)
    assert res.status_code == 429
    assert res.json()["error"] == "rate_limited"


def test_quota_exhausted_maps_to_429():
    client, _ = make({
        "gemini-3.1-flash-lite": [api_error(429)],
        "gemini-3.5-flash-lite": [api_error(429)],
    })
    res = client.post("/v1/ask", json=ASK)
    assert res.status_code == 429
    assert res.json()["error"] == "quota_exhausted"


def test_invalid_grade_is_rejected():
    client, _ = make({})
    assert client.post("/v1/ask", json={**ASK, "grade": 11}).status_code == 422


QUIZ = {"subject": "Science", "grade": 5, "language": "English", "explanation": "Plants make food."}


def test_quiz_drops_malformed_items():
    items = [
        {"question": "Q1?", "options": ["a", "b", "c", "d"], "correct_index": 1, "explanation": "e"},
        {"question": "Q2?", "options": ["a", "b"], "correct_index": 0, "explanation": "e"},
        {"question": "Q3?", "options": ["a", "b", "c", "d"], "correct_index": 7, "explanation": "e"},
    ]
    client, fake = make({"gemini-3.1-flash-lite": [response(json.dumps(items))]})
    res = client.post("/v1/quiz", json=QUIZ)
    assert res.status_code == 200
    questions = res.json()["questions"]
    assert [q["question"] for q in questions] == ["Q1?"]
    assert questions[0]["correctIndex"] == 1
    assert fake.calls[0]["config"].response_mime_type == "application/json"


def test_quiz_with_unparseable_output_is_502():
    client, _ = make({"gemini-3.1-flash-lite": [response("not json")]})
    assert client.post("/v1/quiz", json=QUIZ).status_code == 502


def test_missing_credentials_is_503_and_logged(capsys):
    from google.auth.exceptions import DefaultCredentialsError

    class NoCreds(FakeClient):
        async def _generate(self, **kw):
            raise DefaultCredentialsError("none")

    fake = NoCreds({})
    client = TestClient(create_app(client=fake))
    res = client.post("/v1/ask", json=ASK)
    assert res.status_code == 503
    assert res.json()["error"] == "backend_misconfigured"
    log = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert log["status"] == 503 and "credentials" in log["error"]
