def test_schemes_list_and_filters(client):
    resp = client.get("/api/schemes")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert data["total"] > 0

    # Search keyword
    search_resp = client.get("/api/schemes?q=pmegp")
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert any("pmegp" in item["slug"].lower() for item in search_data["items"])

def test_scheme_detail_by_slug(client):
    resp = client.get("/api/schemes/pmegp")
    assert resp.status_code == 200
    scheme = resp.json()
    assert scheme["slug"] == "pmegp"
    assert scheme["source_authority"] is not None
    assert scheme["verification_status"] == "VERIFIED"
    assert len(scheme["documents"]) > 0

def test_calculators_api(client):
    # EMI calculation
    emi_resp = client.post("/api/calculators/emi", json={
        "loan_amount": 500000.0,
        "annual_interest_rate": 9.5,
        "tenure_months": 60
    })
    assert emi_resp.status_code == 200
    emi_data = emi_resp.json()
    assert emi_data["monthly_emi"] > 0
    assert emi_data["total_interest"] > 0

    # Subsidy calculation (PMEGP Special Rural)
    sub_resp = client.post("/api/calculators/subsidy", json={
        "scheme_type": "PMEGP",
        "business_type": "MANUFACTURING",
        "area_type": "RURAL",
        "category": "SPECIAL",
        "project_cost": 1000000.0
    })
    assert sub_resp.status_code == 200
    sub_data = sub_resp.json()
    assert sub_data["subsidy_percentage"] == 35.0
    assert sub_data["subsidy_amount"] == 350000.0
    assert sub_data["own_contribution_percentage"] == 5.0
