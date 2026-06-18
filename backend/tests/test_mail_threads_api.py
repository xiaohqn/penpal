from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def build_test_client(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'mail_threads.db'}",
        mock_llm=True,
        counselor_features_enabled=True,
        visitor_invite_codes=["visitor-test"],
        counselor_invite_codes=["counselor-test"],
    )
    app = create_app(settings)
    return TestClient(app)


def register(client: TestClient, username: str, role: str = "visitor", invite_code: str | None = None) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "password": "password123",
            "display_name": username,
            "role": role,
            "invite_code": invite_code or ("counselor-test" if role == "counselor" else "visitor-test"),
        },
    )
    assert response.status_code == 201
    return response.json()["token"]


def test_register_requires_matching_invite_code(tmp_path):
    client = build_test_client(tmp_path)

    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "bad-invite",
            "password": "password123",
            "display_name": "bad-invite",
            "role": "visitor",
            "invite_code": "wrong",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "邀请码无效"


def test_mail_thread_multiturn_and_memory(tmp_path):
    client = build_test_client(tmp_path)
    user_token = register(client, "visitor-a")

    create_response = client.post(
        "/api/v1/mail-threads",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "signature": "小星",
            "content": "我最近注意力很难集中，也觉得很孤独。",
            "reply_mode": "ai",
            "response_preference": "温柔陪伴",
            "ai_reply_text": "我认真读完了你的来信。你不是一个人在面对这些。",
        },
    )
    assert create_response.status_code == 201
    thread = create_response.json()
    assert len(thread["messages"]) == 2
    assert thread["memory"]["message_count"] == 2

    followup_response = client.post(
        f"/api/v1/mail-threads/{thread['id']}/messages",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "content": "谢谢你。我还是想知道明天可以怎么开始。",
            "ai_reply_text": "那我们把明天缩小到第一步：先做一件五分钟能完成的小事。",
        },
    )
    assert followup_response.status_code == 201
    updated = followup_response.json()
    assert len(updated["messages"]) == 4
    assert "最近一次来信重点" in updated["memory"]["summary"]


def test_counselor_can_reply_to_assigned_thread(tmp_path):
    client = build_test_client(tmp_path)
    counselor_token = register(client, "counselor-a", role="counselor")
    user_token = register(client, "visitor-b")

    create_response = client.post(
        "/api/v1/mail-threads",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "signature": "匿名",
            "content": "我想把这封信交给人工咨询师。",
            "reply_mode": "human",
            "response_preference": "温柔陪伴",
        },
    )
    assert create_response.status_code == 201
    thread_id = create_response.json()["id"]

    assigned_response = client.get(
        "/api/v1/mail-threads/assigned/mine",
        headers={"Authorization": f"Bearer {counselor_token}"},
    )
    assert assigned_response.status_code == 200
    assert assigned_response.json()["total"] == 1

    reply_response = client.post(
        f"/api/v1/mail-threads/assigned/{thread_id}/reply",
        headers={"Authorization": f"Bearer {counselor_token}"},
        json={"content": "我看见你愿意把这封信交出来，这本身已经很不容易。"},
    )
    assert reply_response.status_code == 200
    assert reply_response.json()["status"] == "waiting_user"
    assert len(reply_response.json()["messages"]) == 2


def test_high_risk_letter_is_forced_to_human(tmp_path):
    client = build_test_client(tmp_path)
    counselor_token = register(client, "counselor-risk", role="counselor")
    user_token = register(client, "visitor-risk")

    response = client.post(
        "/api/v1/mail-threads",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "signature": "匿名",
            "content": "我最近经常想死，也想伤害自己。",
            "reply_mode": "ai",
            "response_preference": "温柔陪伴",
            "ai_reply_text": "我在这里。",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["reply_mode"] == "human"
    assert data["status"] == "waiting_counselor"
    assert data["assigned_counselor_id"] == "counselor-risk"
    assert data["risk_assessments"][0]["risk_level"] == "HIGH"

    assigned_response = client.get(
        "/api/v1/mail-threads/assigned/mine",
        headers={"Authorization": f"Bearer {counselor_token}"},
    )
    assert assigned_response.status_code == 200
    assert assigned_response.json()["total"] == 1


def test_crisis_letter_gets_crisis_response(tmp_path):
    client = build_test_client(tmp_path)
    register(client, "counselor-crisis", role="counselor")
    user_token = register(client, "visitor-crisis")

    response = client.post(
        "/api/v1/mail-threads",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "signature": "匿名",
            "content": "我已经准备好了，今晚准备结束生命。",
            "reply_mode": "ai",
            "response_preference": "温柔陪伴",
            "ai_reply_text": "普通回复不应该被使用。",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "crisis"
    assert data["reply_mode"] == "human"
    assert data["risk_assessments"][0]["risk_level"] == "CRISIS"
    assert "紧急服务" in data["messages"][-1]["content"]


def test_high_risk_letter_does_not_transfer_when_counselor_features_disabled(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'mail_threads_disabled.db'}",
        mock_llm=True,
        counselor_features_enabled=False,
        visitor_invite_codes=["visitor-test"],
        counselor_invite_codes=["counselor-test"],
    )
    client = TestClient(create_app(settings))
    register(client, "counselor-disabled", role="counselor")
    user_token = register(client, "visitor-disabled")

    human_response = client.post(
        "/api/v1/mail-threads",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "signature": "匿名",
            "content": "我想把这封信交给人工咨询师。",
            "reply_mode": "human",
            "response_preference": "温柔陪伴",
        },
    )
    assert human_response.status_code == 409

    risk_response = client.post(
        "/api/v1/mail-threads",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "signature": "匿名",
            "content": "我最近经常想死，也想伤害自己。",
            "reply_mode": "ai",
            "response_preference": "温柔陪伴",
            "ai_reply_text": "普通回复不应该被使用。",
        },
    )
    assert risk_response.status_code == 201
    data = risk_response.json()
    assert data["reply_mode"] == "ai"
    assert data["status"] == "waiting_user"
    assert data["assigned_counselor_id"] is None
    assert "不能替代现实中的专业支持" in data["messages"][-1]["content"]
