from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def build_test_client(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'records.db'}",
        mock_llm=True,
    )
    app = create_app(settings)
    return TestClient(app)


def test_record_create_and_fetch(tmp_path):
    client = build_test_client(tmp_path)

    payload = {
        "user_input": "我最近特别累，不知道该怎么办。",
        "selected_persona_name": "温暖倾听者",
        "selected_style_config": {"persona_name": "温暖倾听者"},
        "planner_output": {"generation_plan": "先接住情绪，再给小动作"},
        "draft_candidates": [
            {
                "persona_name": "温暖倾听者",
                "style_config": {"persona_name": "温暖倾听者"},
                "planner_output": {"generation_plan": "test"},
                "response": "你好，我在这里。",
                "raw_response": "",
            }
        ],
        "ai_selected_raw_response": "你好，我在这里。",
        "expert_polished_response": "你好，我认真看见了你的疲惫。",
        "expert_annotation": "我补了更具体的开口话术。",
        "rag_ready": "approved",
        "sample_reason": "专家认为这条回复兼顾情绪承接和具体建议，适合纳入后续检索语料。",
        "sample_snapshot": {"final_response": "你好，我认真看见了你的疲惫。"},
    }

    create_response = client.post("/api/v1/records", json=payload)
    assert create_response.status_code == 201
    record_id = create_response.json()["id"]

    list_response = client.get("/api/v1/records")
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    detail_response = client.get(f"/api/v1/records/{record_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["expert_polished_response"] == payload["expert_polished_response"]
    assert detail_response.json()["expert_annotation"] == payload["expert_annotation"]
    assert detail_response.json()["rag_ready"] == payload["rag_ready"]
    assert detail_response.json()["sample_reason"] == payload["sample_reason"]
