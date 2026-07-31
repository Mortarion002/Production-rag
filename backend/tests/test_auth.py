import json
from unittest.mock import MagicMock

from app.auth import models, jwt as jwt_module


def _parse_sse(body: str) -> list[dict]:
    events = []
    for block in body.strip().split("\n\n"):
        if not block.strip():
            continue
        lines = block.splitlines()
        event = next(l.split(": ", 1)[1] for l in lines if l.startswith("event: "))
        data = next(l.split(": ", 1)[1] for l in lines if l.startswith("data: "))
        events.append({"event": event, "data": json.loads(data)})
    return events


def _signup(client, email="user@example.com", password="password123"):
    return client.post("/auth/signup", json={"email": email, "password": password})


def _login(client, email="user@example.com", password="password123"):
    return client.post("/auth/token", data={"username": email, "password": password})


def _create_user(db_session, email, password, role):
    user = models.User(
        email=email,
        hashed_password=jwt_module.get_password_hash(password),
        role=role,
    )
    db_session.add(user)
    db_session.commit()
    return user


# --- signup / login ---

def test_signup_then_login_succeeds(client):
    signup_resp = _signup(client)
    assert signup_resp.status_code == 200
    assert signup_resp.json()["role"] == models.UserRole.USER.value

    login_resp = _login(client)
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


def test_signup_duplicate_email_rejected(client):
    _signup(client)
    resp = _signup(client)
    assert resp.status_code == 400


def test_login_wrong_password_rejected(client):
    _signup(client)
    resp = _login(client, password="wrong-password")
    assert resp.status_code == 401


# --- /ingest role gating ---

def test_ingest_rejects_non_admin(client, db_session):
    _create_user(db_session, "plain@example.com", "password123", models.UserRole.USER.value)
    token = _login(client, "plain@example.com", "password123").json()["access_token"]

    resp = client.post(
        "/ingest",
        json={"text": "some text", "filename": "doc.txt"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_ingest_allows_admin(client, db_session, monkeypatch):
    _create_user(db_session, "admin@example.com", "password123", models.UserRole.ADMIN.value)
    token = _login(client, "admin@example.com", "password123").json()["access_token"]

    monkeypatch.setattr("app.server.ingest_text", lambda text, metadata=None: 3)

    resp = client.post(
        "/ingest",
        json={"text": "some text", "filename": "doc.txt"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Successfully ingested 3 chunks"


# --- /chat auth wiring ---

def test_chat_requires_auth(client):
    resp = client.post("/chat", json={"question": "hello"})
    assert resp.status_code == 401


def test_chat_streams_step_events_then_done(client, monkeypatch):
    _signup(client)
    token = _login(client).json()["access_token"]

    updates = [
        {"retrieve": {"steps": ["retrieve"]}},
        {"grade_documents": {"steps": ["retrieve", "grade_documents"]}},
        {"generate": {"steps": ["retrieve", "grade_documents", "generate"]}},
        {"hallucination_check": {
            "steps": ["retrieve", "grade_documents", "generate", "hallucination_check"],
            "generation": "the answer",
        }},
    ]
    monkeypatch.setattr("app.server.graph_app.stream", MagicMock(return_value=iter(updates)))

    resp = client.post(
        "/chat",
        json={"question": "hello"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(resp.text)
    assert [e["event"] for e in events] == ["step", "step", "step", "step", "done"]
    assert events[0]["data"] == {"node": "retrieve", "label": "Retrieving documents..."}
    assert events[-1]["data"] == {
        "answer": "the answer",
        "steps": ["retrieve", "grade_documents", "generate", "hallucination_check"],
    }


def test_chat_emits_error_event_on_exception(client, monkeypatch):
    _signup(client)
    token = _login(client).json()["access_token"]

    def _raise(*args, **kwargs):
        raise RuntimeError("graph blew up")
        yield  # pragma: no cover - makes this a generator function

    monkeypatch.setattr("app.server.graph_app.stream", _raise)

    resp = client.post(
        "/chat",
        json={"question": "hello"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    assert events[-1]["event"] == "error"
    assert "graph blew up" in events[-1]["data"]["detail"]
