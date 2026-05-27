from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
import app.services.safety_service as safety_service_module


def build_test_client(tmp_path):
    """
    输入：
    - tmp_path：pytest 提供的临时目录。
    输出：
    - 返回一个使用临时 SQLite 数据库和 mock LLM 的测试客户端。
    作用：
    - 为安全检测接口测试提供隔离运行环境。
    """

    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'safety.db'}",
        mock_llm=True,
        safety_mode="mock",
    )
    app = create_app(settings)
    return TestClient(app)


def build_test_client_with_settings(tmp_path, **overrides):
    """
    输入：
    - tmp_path：pytest 提供的临时目录。
    - overrides：需要覆盖的 Settings 字段。
    输出：
    - 返回一个使用临时 SQLite 数据库和自定义配置的测试客户端。
    作用：
    - 让测试能够更直接地验证安全链路独立 env 配置是否生效，而不影响其他测试用例的默认构造方式。
    """

    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'safety-custom.db'}",
        **overrides,
    )
    app = create_app(settings)
    return TestClient(app)


def test_safety_check_returns_safe_result_for_low_risk_input(tmp_path):
    client = build_test_client(tmp_path)

    response = client.post(
        "/api/v1/safety/check",
        json={"user_input": "最近学习压力有点大，但我想慢慢调整回来。"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_safe"] is True
    assert payload["risk_codes"] == [0]
    assert payload["risk_labels"] == ["安全"]
    assert payload["safe_response"] is None
    assert payload["safe_highlight_segments"] == []
    assert payload["safe_highlight_source"] is None


def test_safety_check_returns_labels_and_safe_reply_for_unsafe_input(tmp_path):
    client = build_test_client(tmp_path)

    response = client.post(
        "/api/v1/safety/check",
        json={"user_input": "我真的有点不想活了，也有过想伤害自己的念头。"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_safe"] is False
    assert payload["risk_codes"] == [1, 3]
    assert payload["risk_labels"] == ["自杀倾向", "非自杀性自伤行为"]
    assert payload["reason"]
    assert payload["safe_response"]
    assert payload["safe_highlight_segments"]
    assert payload["safe_highlight_source"] == "fallback"
    assert all(segment in payload["safe_response"] for segment in payload["safe_highlight_segments"])


def test_safety_check_uses_history_records_matched_by_corrected_risk_labels(tmp_path):
    """
    输入：
    - 临时测试数据库目录。
    输出：
    - 断言当历史安全记录的 `corrected_risk_labels_json` 与当前风险标签匹配时，
      mock 安全回复会带出“过往相似风险来信”的 few-shot 提示痕迹。
    作用：
    - 验证安全回复链路已经能基于历史安全记录完成最小版 few-shot 检索。
    """

    client = build_test_client(tmp_path)

    create_response = client.post(
        "/api/v1/safety-records",
        json={
            "user_input": "我真的快撑不住了，也有过想伤害自己的念头。",
            "risk_labels": ["自杀倾向", "非自杀性自伤行为"],
            "corrected_risk_labels": ["自杀倾向", "非自杀性自伤行为"],
            "risk_reason": "历史样本中出现了明显的轻生和自伤风险。",
            "ai_safe_response": "先联系信任的大人和老师。",
            "expert_polished_response": "先让现实里值得信任的大人、老师或专业支持接住你。",
        },
    )
    assert create_response.status_code == 201

    response = client.post(
        "/api/v1/safety/check",
        json={"user_input": "我真的有点不想活了，也有过想伤害自己的念头。"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_safe"] is False
    assert payload["safe_response"]
    assert "过往相似风险来信" in payload["safe_response"]
    assert payload["safe_highlight_segments"]
    assert payload["safe_highlight_source"] == "fallback"
    assert all(segment in payload["safe_response"] for segment in payload["safe_highlight_segments"])


def test_safety_mode_can_force_mock_independently_of_main_generation(tmp_path):
    """
    输入：
    - 临时测试数据库目录。
    输出：
    - 断言即使普通主链路配置成 API，安全链路仍然可以被 `safety_mode=mock` 单独强制切到 mock。
    作用：
    - 验证新增的安全独立 env 已经真正接入安全检测接口，而不是只停留在配置层。
    """

    client = build_test_client_with_settings(
        tmp_path,
        mock_llm=False,
        planner_mode="api",
        generator_mode="api",
        safety_mode="mock",
    )

    response = client.post(
        "/api/v1/safety/check",
        json={"user_input": "我真的有点不想活了，也有过想伤害自己的念头。"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_safe"] is False
    assert payload["safe_highlight_source"] == "fallback"
    assert payload["safe_response"]


def test_safety_mode_defaults_to_api(tmp_path):
    """
    输入：
    - 临时测试数据库目录。
    输出：
    - 断言未显式配置 `safety_mode` 时，安全链路默认模式为 `api`。
    作用：
    - 验证删除 `inherit` 后，默认值已经变成更直接、更易理解的显式模式。
    """

    client = build_test_client_with_settings(
        tmp_path,
        mock_llm=False,
        doubao_api_key="demo-key",
    )

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["safety_mode"] == "api"


def test_healthcheck_exposes_effective_safety_mode(tmp_path):
    """
    输入：
    - 临时测试数据库目录。
    输出：
    - 断言健康检查结果里包含安全链路的实际模式判定。
    作用：
    - 让前端和手工调试时都能快速确认当前安全链路到底走的是 mock、api 还是 local。
    """

    client = build_test_client_with_settings(
        tmp_path,
        mock_llm=False,
        generator_mode="api",
        safety_mode="mock",
    )

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["safety_mode"] == "mock"


def test_safety_check_returns_clear_error_when_vllm_is_selected_but_safety_local_is_not_connected(tmp_path):
    """
    输入：
    - 临时测试数据库目录。
    输出：
    - 断言当用户在工作台里显式选择 `vllm`，但安全链路没有接入本地安全模型时，
      `/safety/check` 会直接返回清晰错误，而不是悄悄继续走 API。
    作用：
    - 防止安全链路与用户的来源选择产生误导性偏差，尤其是在“只改安全部分”的需求下。
    """

    client = build_test_client_with_settings(
        tmp_path,
        mock_llm=False,
        safety_mode="api",
        doubao_api_key="demo-key",
    )

    response = client.post(
        "/api/v1/safety/check",
        json={
            "user_input": "最近学习压力很大，我想让自己缓一缓。",
            "source_mode": "vllm",
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert "vLLM" in payload["detail"]


def test_safety_check_returns_compare_candidates_when_compare_mode_is_selected(tmp_path, monkeypatch):
    """
    输入：
    - 临时测试数据库目录，以及 pytest 的 monkeypatch 工具。
    输出：
    - 断言安全链路在对比模式下会同时返回 API 与本地安全模型两份候选回复。
    作用：
    - 验证新增的安全对比模式不会再只返回单份回复，也不会把候选切换逻辑留给前端自行猜测。
    """

    def fake_detect_single_letter(user_input: str, if_local: bool = False):
        assert user_input
        assert if_local is False
        return {
            "risk_codes": [1],
            "reason": "检测到明显的自伤与轻生风险信号。",
        }

    def fake_generate_single_safe_reply(
        user_input: str,
        risk_codes: list[int],
        risk_reason: str,
        *,
        few_shot_examples: list[dict[str, str | int | list[str]]],
        if_local: bool = False,
    ):
        assert user_input
        assert risk_codes == [1]
        assert risk_reason
        assert few_shot_examples == []
        return {
            "intent": "先把来信人从危险边缘接住，并推动现实求助。",
            "response": "请先联系你信任的大人和老师，让他们现在就陪着你。" if not if_local else "请先不要一个人待着，马上联系身边可信任的大人陪你。",
        }

    async def fake_extract_highlight_segments(
        self,
        safe_response: str,
        *,
        if_local: bool = False,
        lora_path: str | None = None,
    ):
        assert safe_response
        assert lora_path is None
        return ([safe_response.split("，")[0]], "llm" if not if_local else "fallback")

    monkeypatch.setattr(safety_service_module, "detect_single_letter", fake_detect_single_letter)
    monkeypatch.setattr(
        safety_service_module,
        "generate_single_safe_reply",
        fake_generate_single_safe_reply,
    )
    monkeypatch.setattr(
        safety_service_module.SafeReplyHighlightService,
        "extract_highlight_segments",
        fake_extract_highlight_segments,
    )

    client = build_test_client_with_settings(
        tmp_path,
        mock_llm=False,
        safety_mode="api",
        doubao_api_key="demo-key",
        local_generator_model_path=str(tmp_path / "local-safety-model"),
    )

    response = client.post(
        "/api/v1/safety/check",
        json={
            "user_input": "我真的不想活了，想现在就结束这一切。",
            "source_mode": "compare",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_safe"] is False
    assert payload["safe_response"]
    assert len(payload["safe_response_candidates"]) == 2
    assert [item["source"] for item in payload["safe_response_candidates"]] == ["api", "local"]
    assert payload["safe_response_candidates"][0]["safe_highlight_source"] == "llm"
    assert payload["safe_response_candidates"][1]["safe_highlight_source"] == "fallback"


def test_safety_regenerate_returns_candidate_for_selected_source(tmp_path, monkeypatch):
    """
    输入：
    - 临时测试数据库目录，以及 pytest 的 monkeypatch 工具。
    输出：
    - 断言安全回复重生成接口会沿用当前候选来源，并把原回复、划词批注和专家说明一起送入生成链路。
    作用：
    - 验证安全页新增的“专家批注再生成”按钮确实有独立后端支持，而不是误复用安全检测入口。
    """

    captured: dict[str, object] = {}

    def fake_generate_single_safe_reply(
        user_input: str,
        risk_codes: list[int],
        risk_reason: str,
        *,
        few_shot_examples: list[dict[str, str | int | list[str]]],
        if_local: bool = False,
    ):
        captured["user_input"] = user_input
        captured["risk_codes"] = risk_codes
        captured["risk_reason"] = risk_reason
        captured["few_shot_examples"] = few_shot_examples
        captured["if_local"] = if_local
        return {
            "intent": "先接住情绪，再把现实求助建议说得更具体。",
            "response": "请先联系你信任的大人或老师，让他们现在陪着你，不要一个人硬撑。",
        }

    async def fake_extract_highlight_segments(
        self,
        safe_response: str,
        *,
        if_local: bool = False,
        lora_path: str | None = None,
    ):
        assert safe_response
        assert if_local is False
        assert lora_path is None
        return (["请先联系你信任的大人或老师"], "llm")

    monkeypatch.setattr(
        safety_service_module,
        "generate_single_safe_reply",
        fake_generate_single_safe_reply,
    )
    monkeypatch.setattr(
        safety_service_module.SafeReplyHighlightService,
        "extract_highlight_segments",
        fake_extract_highlight_segments,
    )

    client = build_test_client_with_settings(
        tmp_path,
        mock_llm=False,
        safety_mode="api",
        doubao_api_key="demo-key",
    )

    response = client.post(
        "/api/v1/safety/regenerate",
        json={
            "user_input": "我真的不想活了，觉得自己快扛不住了。",
            "risk_codes": [1],
            "corrected_risk_labels": ["自杀倾向"],
            "risk_reason": "检测到明显的轻生风险。",
            "source": "api",
            "current_response": "请先联系你信任的大人，告诉他们你现在很危险。",
            "source_annotations": [
                {
                    "id": "annotation-1",
                    "start": 0,
                    "end": 9,
                    "quote": "请先联系你信任的大人",
                    "note": "这里还需要补上老师，避免支持对象过窄。",
                    "color": "amber",
                }
            ],
            "expert_annotation": "整体语气还可以，但现实求助建议需要更具体一点。",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "api"
    assert payload["source_label"] == "API 安全回复"
    assert payload["safe_response"]
    assert payload["safe_highlight_segments"] == ["请先联系你信任的大人或老师"]
    assert payload["safe_highlight_source"] == "llm"
    assert captured["if_local"] is False
    assert captured["risk_codes"] == [1]
    assert "【当前安全回复】" in str(captured["user_input"])
    assert "【专家对当前安全回复的高亮批注】" in str(captured["user_input"])
    assert "【专家总体说明】" in str(captured["user_input"])


def test_safety_regenerate_rejects_empty_annotation_and_expert_note(tmp_path):
    """
    输入：
    - 临时测试数据库目录。
    输出：
    - 断言当安全回复没有任何高亮批注或总体说明时，重生成接口会返回明确错误提示。
    作用：
    - 防止前端误触重生成按钮后发送一条没有人工意图的空请求，浪费调用并制造困惑。
    """

    client = build_test_client_with_settings(
        tmp_path,
        mock_llm=False,
        safety_mode="api",
        doubao_api_key="demo-key",
    )

    response = client.post(
        "/api/v1/safety/regenerate",
        json={
            "user_input": "我真的不想活了，觉得自己快扛不住了。",
            "risk_codes": [1],
            "corrected_risk_labels": ["自杀倾向"],
            "risk_reason": "检测到明显的轻生风险。",
            "source": "api",
            "current_response": "请先联系你信任的大人，告诉他们你现在很危险。",
            "source_annotations": [],
            "expert_annotation": "",
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert "至少一条高亮批注" in payload["detail"]
