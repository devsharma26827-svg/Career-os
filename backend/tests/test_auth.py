from app.models.user import User


def test_signup_success(client, db_session):
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "newuser@example.com",
            "password": "StrongPassword123!",
            "full_name": "Jordan Lee"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "newuser@example.com"
    assert data["user"]["full_name"] == "Jordan Lee"
    assert data["user"]["reduced_motion"] is False

    # Verify password was hashed and not saved plaintext
    user = db_session.query(User).filter(User.email == "newuser@example.com").first()
    assert user is not None
    assert user.hashed_password != "StrongPassword123!"
    assert user.hashed_password.startswith("$2b$")
    assert user.reduced_motion is False


def test_signup_duplicate_email_fails(client, test_user):
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": test_user.email,
            "password": "AnotherPassword123!",
            "full_name": "Duplicate User"
        }
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


def test_login_success(client, test_user):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "securepassword123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == test_user.email
    assert data["user"]["reduced_motion"] is False


def test_login_wrong_password_fails(client, test_user):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "WrongPassword!"
        }
    )
    assert response.status_code == 401
    assert "incorrect email or password" in response.json()["detail"].lower()


def test_get_current_user_profile(client, auth_headers, test_user):
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["full_name"] == test_user.full_name
    assert data["reduced_motion"] is False


def test_unauthenticated_access_rejected(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_update_user_preferences(client, auth_headers):
    response = client.put(
        "/api/v1/auth/preferences",
        headers=auth_headers,
        json={"font_size": "large", "display_mode": "advanced", "reduced_motion": True}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["font_size"] == "large"
    assert data["display_mode"] == "advanced"
    assert data["reduced_motion"] is True
