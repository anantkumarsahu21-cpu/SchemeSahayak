def test_register_and_login(client):
    email = "citizen.test@schemesahayak.gov.in"
    password = "SecurePassword@123"

    # Register
    reg_resp = client.post("/api/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Test Citizen",
        "preferred_language": "en"
    })
    assert reg_resp.status_code == 200
    data = reg_resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == email

    # Duplicate Register should fail
    dup_resp = client.post("/api/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Duplicate"
    })
    assert dup_resp.status_code == 400

    # Login
    login_resp = client.post("/api/auth/login", json={
        "email": email,
        "password": password
    })
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert "access_token" in login_data

def test_user_profile_crud(client):
    email = "profile.test@schemesahayak.gov.in"
    password = "ProfilePassword@123"

    reg = client.post("/api/auth/register", json={"email": email, "password": password, "full_name": "Profile User"})
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get profile
    get_p = client.get("/api/auth/profile", headers=headers)
    assert get_p.status_code == 200

    # Update profile
    up_p = client.put("/api/auth/profile", headers=headers, json={
        "age": 24,
        "gender": "FEMALE",
        "state_code": "UP",
        "district_name": "Lucknow",
        "annual_income": 180000.0,
        "education_level": "GRADUATE",
        "employment_status": "STUDENT"
    })
    assert up_p.status_code == 200
    assert up_p.json()["state_code"] == "UP"
    assert up_p.json()["age"] == 24
