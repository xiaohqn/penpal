from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def build_test_client(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        mock_llm=True,
    )
    app = create_app(settings)
    return TestClient(app)


def test_generation_stream_returns_multiple_persona_events(tmp_path):
    client = build_test_client(tmp_path)

    response = client.post(
        "/api/v1/generations/stream",
        json={
            "user_input": "最近我有点撑不住，想找人说说。",
            "persona_names": ["温暖倾听者", "理性教练"],
        },
    )

    assert response.status_code == 200
    text = response.text
    assert "event: draft_started" in text
    assert "温暖倾听者" in text
    assert "理性教练" in text
    assert "event: job_done" in text
