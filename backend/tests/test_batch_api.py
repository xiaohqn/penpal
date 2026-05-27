from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook

from app.core.config import Settings
from app.main import create_app


def build_test_client(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'batch.db'}",
        mock_llm=True,
    )
    app = create_app(settings)
    return TestClient(app)


def make_test_excel() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["user_input", "selected_persona_names"])
    sheet.append(["我最近压力很大，想找人说说。", "温暖倾听者,理性教练"])
    sheet.append(["我总觉得自己快扛不住了。", "故事导师"])

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def test_batch_import_excel(tmp_path):
    client = build_test_client(tmp_path)
    excel_bytes = make_test_excel()

    response = client.post(
        "/api/v1/batch/import",
        files={"file": ("batch.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["items"][0]["selected_persona_names"] == []


def test_export_records_excel(tmp_path):
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
        "expert_annotation": "补充了具体求助对象。",
        "rag_ready": "approved",
        "sample_reason": "这条适合作为 RAG 样本。",
        "sample_snapshot": {"final_response": "你好，我认真看见了你的疲惫。"},
    }
    client.post("/api/v1/records", json=payload)

    response = client.get("/api/v1/batch/records/export")
    assert response.status_code == 200

    workbook = load_workbook(BytesIO(response.content))
    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    assert rows[0][3] == "rag_ready"
    assert rows[1][3] == payload["rag_ready"]
    assert rows[0][4] == "sample_reason"
    assert rows[1][4] == payload["sample_reason"]
    assert rows[0][8] == "expert_annotation"
    assert rows[1][8] == payload["expert_annotation"]


def test_batch_regenerate_keeps_first_ai_reply_as_original_response(tmp_path):
    """
    输入：
    - 临时测试数据库目录，以及一个已经导入的批量任务。
    输出：
    - 断言批量条目在批注重生成后，`ai_selected_raw_response` 仍然保留首轮草稿，而不是被新版本覆盖。
    作用：
    - 防止“原始回复”字段在批量工作流里被批注重生成结果污染，导致历史记录失去首版基线。
    """

    client = build_test_client(tmp_path)
    excel_bytes = make_test_excel()
    import_response = client.post(
        "/api/v1/batch/import",
        files={"file": ("batch.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert import_response.status_code == 200

    session_payload = import_response.json()
    session_id = session_payload["id"]
    item = session_payload["items"][0]
    item_id = item["id"]

    initial_response = "这是首轮 AI 草稿，请先找老师聊聊。"
    update_response = client.put(
        f"/api/v1/batch/sessions/{session_id}/items/{item_id}",
        json={
            "selected_persona_names": ["温暖倾听者"],
            "selected_persona_name": "温暖倾听者",
            "selected_style_config": {"persona_name": "温暖倾听者"},
            "planner_output": {"generation_plan": "先共情，再给现实建议"},
            "draft_candidates": [
                {
                    "draft_id": "温暖倾听者::api",
                    "persona_name": "温暖倾听者",
                    "source": "api",
                    "source_label": "API 模型",
                    "style_config": {"persona_name": "温暖倾听者"},
                    "planner_output": {"generation_plan": "先共情，再给现实建议"},
                    "response": initial_response,
                    "raw_response": initial_response,
                }
            ],
            "ai_selected_raw_response": "",
            "latest_response": initial_response,
            "expert_annotation": "",
            "rag_ready": "pending",
            "sample_reason": "",
            "sample_snapshot": {},
            "source_annotations": [],
            "response_versions": [],
            "active_version_index": 0,
            "status": "in_progress",
            "record_id": None,
        },
    )
    assert update_response.status_code == 200

    async def fake_generate_all(user_input: str, persona_names: list[str]):
        assert "【当前 AI 回复】" in user_input
        assert persona_names == ["温暖倾听者"]
        return [
            {
                "draft_id": "温暖倾听者::api",
                "persona_name": "温暖倾听者",
                "source": "api",
                "source_label": "API 模型",
                "style_config": {"persona_name": "温暖倾听者"},
                "planner_output": {"generation_plan": "按批注重写"},
                "response": "这是批注重生成后的新版本，请联系班主任和家长。",
                "raw_response": "这是批注重生成后的新版本，请联系班主任和家长。",
            }
        ]

    client.app.state.orchestration_service.generate_all = fake_generate_all

    regenerate_response = client.post(
        f"/api/v1/batch/sessions/{session_id}/items/{item_id}/regenerate",
        json={
            "selected_persona_name": "温暖倾听者",
            "selected_persona_names": ["温暖倾听者"],
            "source_annotations": [
                {
                    "id": "annotation-1",
                    "start": 0,
                    "end": 6,
                    "quote": "这是首轮 AI 草稿",
                    "note": "这里还需要补老师和家长两个现实支持对象。",
                    "color": "amber",
                }
            ],
            "expert_annotation": "把现实求助对象说得更具体一些。",
            "current_response": initial_response,
        },
    )
    assert regenerate_response.status_code == 200

    updated_item = next(
        current for current in regenerate_response.json()["items"] if current["id"] == item_id
    )
    assert updated_item["ai_selected_raw_response"] == initial_response
    assert updated_item["latest_response"] == "这是批注重生成后的新版本，请联系班主任和家长。"
