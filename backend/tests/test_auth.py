from unittest.mock import MagicMock

from app.auth import models, jwt as jwt_module


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


def test_chat_returns_answer_and_steps_for_authenticated_user(client, monkeypatch):
    _signup(client)
    token = _login(client).json()["access_token"]

    monkeypatch.setattr(
        "app.server.graph_app.invoke",
        MagicMock(return_value={"generation": "the answer", "steps": ["retrieve", "generate"]}),
    )

    resp = client.post(
        "/chat",
        json={"question": "hello"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"answer": "the answer", "steps": ["retrieve", "generate"]}
