"""
JobPulse AI - End-to-End Authentication Verification against Live Database
Tests:
1. Signup with a new user
2. Login with newly created user
3. Get /me endpoint and verify preferences (including reduced_motion)
4. Update display preferences (toggle reduced_motion to True)
5. Re-login as existing user and verify updated preferences persist
6. Duplicate email rejection (HTTP 400, not SQL error)
7. Invalid password rejection (HTTP 401, not SQL error)
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.abspath("backend"))

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.user import User

client = TestClient(app)

def test_full_auth_lifecycle():
    print("==================================================")
    print("TESTING FULL AUTHENTICATION LIFECYCLE (LIVE DB)")
    print("==================================================")

    test_email = "test_verified_user@example.com"
    test_password = "SecurePassword123!"
    test_name = "Taylor Swift"

    # Clean up test user if previously left over
    db = SessionLocal()
    existing = db.query(User).filter(User.email == test_email).first()
    if existing:
        db.delete(existing)
        db.commit()
    db.close()

    # 1. Signup
    print("\n[STEP 1] Testing User Signup...")
    signup_payload = {
        "email": test_email,
        "password": test_password,
        "full_name": test_name
    }
    signup_resp = client.post("/api/v1/auth/signup", json=signup_payload)
    print(f"  Status code: {signup_resp.status_code}")
    assert signup_resp.status_code == 201, f"Signup failed: {signup_resp.text}"
    signup_data = signup_resp.json()
    assert "access_token" in signup_data
    user_info = signup_data["user"]
    print(f"  User created: ID={user_info['id']}, Email={user_info['email']}")
    print(f"  reduced_motion value: {user_info.get('reduced_motion')}")
    assert user_info["reduced_motion"] is False
    token = signup_data["access_token"]

    # 2. Duplicate Signup Protection
    print("\n[STEP 2] Testing Duplicate Email Signup...")
    dup_resp = client.post("/api/v1/auth/signup", json=signup_payload)
    print(f"  Status code: {dup_resp.status_code} (Expected 400)")
    assert dup_resp.status_code == 400
    assert "already exists" in dup_resp.json()["detail"]
    print("  [OK] Duplicate email handled cleanly without SQL error.")

    # 3. Login
    print("\n[STEP 3] Testing User Login...")
    login_payload = {
        "email": test_email,
        "password": test_password
    }
    login_resp = client.post("/api/v1/auth/login", json=login_payload)
    print(f"  Status code: {login_resp.status_code}")
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    login_data = login_resp.json()
    assert "access_token" in login_data
    assert login_data["user"]["reduced_motion"] is False
    print("  [OK] Login successful, JWT token received.")

    # 4. Invalid Password Login
    print("\n[STEP 4] Testing Invalid Password Login...")
    bad_login_resp = client.post("/api/v1/auth/login", json={"email": test_email, "password": "WrongPassword!"})
    print(f"  Status code: {bad_login_resp.status_code} (Expected 401)")
    assert bad_login_resp.status_code == 401
    print("  [OK] Invalid password rejected cleanly without SQL error.")

    # 5. Get /me
    print("\n[STEP 5] Testing GET /api/v1/auth/me...")
    headers = {"Authorization": f"Bearer {token}"}
    me_resp = client.get("/api/v1/auth/me", headers=headers)
    print(f"  Status code: {me_resp.status_code}")
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == test_email
    assert me_data["reduced_motion"] is False
    print("  [OK] Current user fetched successfully.")

    # 6. Update preferences (toggle reduced_motion to True)
    print("\n[STEP 6] Testing PUT /api/v1/auth/preferences (toggle reduced_motion)...")
    pref_payload = {
        "font_size": "large",
        "display_mode": "advanced",
        "reduced_motion": True
    }
    pref_resp = client.put("/api/v1/auth/preferences", json=pref_payload, headers=headers)
    print(f"  Status code: {pref_resp.status_code}")
    assert pref_resp.status_code == 200
    updated_user = pref_resp.json()
    print(f"  Updated preferences: font_size={updated_user['font_size']}, display_mode={updated_user['display_mode']}, reduced_motion={updated_user['reduced_motion']}")
    assert updated_user["reduced_motion"] is True
    assert updated_user["font_size"] == "large"
    assert updated_user["display_mode"] == "advanced"

    # 7. Re-login as existing user and verify updated preferences persist in DB
    print("\n[STEP 7] Testing Re-Login as Existing User with Updated Preferences...")
    relogin_resp = client.post("/api/v1/auth/login", json=login_payload)
    assert relogin_resp.status_code == 200
    relogin_user = relogin_resp.json()["user"]
    print(f"  Existing user re-login: reduced_motion={relogin_user['reduced_motion']}")
    assert relogin_user["reduced_motion"] is True
    assert relogin_user["font_size"] == "large"
    assert relogin_user["display_mode"] == "advanced"
    print("  [OK] Updated preferences persisted and verified on re-login.")

    # 8. Check direct database row
    print("\n[STEP 8] Directly Verifying SQLite Database Row...")
    db = SessionLocal()
    db_user = db.query(User).filter(User.email == test_email).first()
    assert db_user is not None
    print(f"  DB User: id={db_user.id}, email={db_user.email}, reduced_motion={db_user.reduced_motion}")
    assert db_user.reduced_motion is True
    db.close()

    print("\n==================================================")
    print("SUCCESS: ALL AUTH & MIGRATION TESTS PASSED 100%!")
    print("==================================================")

if __name__ == "__main__":
    test_full_auth_lifecycle()
