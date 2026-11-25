from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)



def test_register_user():
    email = f"auth_test_{uuid4().hex}@example.com"

    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert data["email"] == email
    assert data["role"] == "user"
    assert "password_hash" not in data



def test_register_duplicate_email():
    email = f"auth_duplicate_{uuid4().hex}@example.com"

    first_response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "TestPassword123!",
        },
    )

    second_response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "TestPassword123!",
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409

def test_login_returns_access_token():
    email = f"auth_login_{uuid4().hex}@example.com"
    password = "TestPassword123!"

    # Register a new user first
    register_response = client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 201

    # Log in with the registered credentials
    login_response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )

    assert login_response.status_code == 200
    data = login_response.json()
    assert data["token_type"] == "bearer"
    assert "access_token" in data
    assert len(data["access_token"]) > 0


def test_get_current_user_with_access_token():
    email = f"auth_me_{uuid4().hex}@example.com"
    password = "TestPassword123!"

    # Register the user
    register_response = client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 201

    # Log in to get an access token
    login_response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    # Call /auth/me using the bearer token
    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert me_response.status_code == 200
    data = me_response.json()
    assert data["email"] == email
    assert data["role"] == "user"
    assert "password_hash" not in data

def test_get_current_user_without_token():
    response = client.get("/auth/me")

    assert response.status_code == 401
