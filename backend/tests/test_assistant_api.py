def test_assistant_chat_endpoint(client):
    # Test guest chat query
    payload = {
        "message": "Which scholarships can I apply for as a student?",
        "language": "en"
    }
    resp = client.post("/api/assistant/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert len(data["reply"]) > 0
    assert "session_id" in data
    assert isinstance(data["sources"], list)
    assert len(data["suggested_questions"]) > 0

    session_id = data["session_id"]

    # Follow-up question with existing session
    follow_up = {
        "message": "What documents are required?",
        "session_id": session_id,
        "language": "en"
    }
    f_resp = client.post("/api/assistant/chat", json=follow_up)
    assert f_resp.status_code == 200
    f_data = f_resp.json()
    assert f_data["session_id"] == session_id

def test_assistant_chat_hindi(client):
    # Test Hindi query
    payload = {
        "message": "मुझे छात्रवृत्ति योजना के बारे में बताएं",
        "language": "hi"
    }
    resp = client.post("/api/assistant/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert len(data["sources"]) > 0
