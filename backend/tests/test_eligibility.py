from app.models.scheme import Scheme


def test_eligibility_matching_student_post_matric(client):
    # Eligible SC Student in UP with income under 2.5L
    profile = {
        "age": 20,
        "gender": "ALL",
        "state_code": "UP",
        "district_name": "Lucknow",
        "caste_category": "SC",
        "annual_income": 120000.0,
        "education_level": "12TH_PASS",
        "employment_status": "STUDENT",
        "occupation": "STUDENT"
    }

    resp = client.post("/api/match", json=profile)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_evaluated"] > 0
    assert len(data["results"]) > 0

    # NSP Post-Matric SC should be top match
    top_matches = [r for r in data["results"] if r["scheme"]["slug"] == "nsp-post-matric-sc"]
    assert len(top_matches) == 1
    nsp = top_matches[0]
    assert nsp["match_score"] >= 80
    assert nsp["eligibility_status"] in ["ELIGIBLE", "LIKELY_ELIGIBLE"]
    assert len(nsp["required_documents"]) > 0


def test_eligibility_matching_handles_null_application_mode(db_session, client):
    scheme = db_session.query(Scheme).filter(Scheme.slug == "nsp-post-matric-sc").first()
    assert scheme is not None

    scheme.application_mode = None
    db_session.commit()

    profile = {
        "age": 20,
        "gender": "ALL",
        "state_code": "UP",
        "district_name": "Lucknow",
        "caste_category": "SC",
        "annual_income": 120000.0,
        "education_level": "12TH_PASS",
        "employment_status": "STUDENT",
        "occupation": "STUDENT"
    }

    resp = client.post("/api/match", json=profile)
    assert resp.status_code == 200
    data = resp.json()
    top_match = next(r for r in data["results"] if r["scheme"]["slug"] == "nsp-post-matric-sc")
    assert top_match["scheme"]["application_mode"] == "ONLINE"


def test_eligibility_state_boundary_disqualification(client):
    # Student in Maharashtra trying to apply for UP state scheme (UP Yuva Swarojgar)
    profile = {
        "age": 22,
        "gender": "MALE",
        "state_code": "MH",
        "annual_income": 150000.0,
        "education_level": "10TH_PASS",
        "employment_status": "UNEMPLOYED"
    }

    resp = client.post("/api/match", json=profile)
    assert resp.status_code == 200
    data = resp.json()

    up_schemes = [r for r in data["results"] if r["scheme"]["slug"] == "up-yuva-swarojgar-yojana"]
    if up_schemes:
        up_match = up_schemes[0]
        assert up_match["eligibility_status"] == "NOT_ELIGIBLE"
        assert any(b["status"] == "FAIL" and "state" in b["detail"].lower() for b in up_match["blockers"])
