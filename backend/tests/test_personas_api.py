from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def build_test_client(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'personas.db'}",
        mock_llm=True,
    )
    app = create_app(settings)
    return TestClient(app)


def test_persona_catalog_uses_merged_personas(tmp_path):
    client = build_test_client(tmp_path)

    response = client.get("/api/v1/personas")

    assert response.status_code == 200
    names = [item["name"] for item in response.json()["personas"]]
    assert names == ["温暖倾听者", "理性破局教练", "启发故事导师"]
