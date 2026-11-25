from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import Document, User

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


def create_rbac_test_document():
    db = SessionLocal()

    try:
        document = Document(
            filename=f"rbac_test_{uuid4().hex}.pdf",
            content_type="application/pdf",
            status="pending",
            extracted_text="RBAC test document",
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        return document.id

    finally:
        db.close()


def delete_rbac_test_document(document_id):
    db = SessionLocal()

    try:
        db.query(Document).filter(
            Document.id == document_id
        ).delete()

        db.commit()

    finally:
        db.close()


def register_and_login(email):
    password = "TestPassword123!"

    register_response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
        },
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    return {
        "Authorization": f"Bearer {access_token}"
    }


def test_register_cannot_create_admin():
    email = f"rbac_register_{uuid4().hex}@example.com"

    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "TestPassword123!",
            "role": "admin",
        },
    )

    assert response.status_code == 201
    assert response.json()["role"] == "user"


def test_regular_user_cannot_update_document_status():
    email = f"rbac_user_{uuid4().hex}@example.com"
    headers = register_and_login(email)

    document_id = create_rbac_test_document()

    try:
        response = client.patch(
            f"/documents/{document_id}",
            json={"status": "completed"},
            headers=headers,
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Admin privileges required"

    finally:
        delete_rbac_test_document(document_id)


def test_admin_can_update_document_status():
    email = f"rbac_admin_{uuid4().hex}@example.com"

    # Register a regular user first.
    register_response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "TestPassword123!",
        },
    )

    assert register_response.status_code == 201

    # Promote this test user to admin directly in the test database.
    db = SessionLocal()

    try:
        user = db.query(User).filter(
            User.email == email
        ).first()

        assert user is not None

        user.role = "admin"
        db.commit()

    finally:
        db.close()

    # Log in after the role has been changed.
    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "TestPassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    document_id = create_rbac_test_document()

    try:
        response = client.patch(
            f"/documents/{document_id}",
            json={"status": "completed"},
            headers=headers,
        )

        assert response.status_code == 200
        assert response.json()["status"] == "completed"

    finally:
        delete_rbac_test_document(document_id)
