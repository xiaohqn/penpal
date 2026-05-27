from types import SimpleNamespace

import clients.doubao_client as doubao_client


def test_create_doubao_client_prefers_backend_settings_over_process_env(monkeypatch):
    """
    输入：
    - monkeypatch：pytest 提供的补丁工具，用来隔离环境变量和配置加载行为。
    输出：
    - 断言 `create_doubao_client()` 在没有显式传参时，会优先使用后端 Settings 中的 key 与 base URL。
    作用：
    - 验证安全链路依赖的豆包 client 已经和 `backend/.env` 打通，而不是只能依赖额外的
      `export DOUBAO_API_KEY=...` 进程级环境变量。
    """

    captured_kwargs: dict[str, object] = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)

    monkeypatch.setattr(
        doubao_client,
        "_load_backend_settings",
        lambda: SimpleNamespace(
            doubao_api_key="settings-key",
            doubao_base_url="https://settings.example/v1",
        ),
    )
    monkeypatch.setattr(doubao_client, "OpenAI", FakeOpenAI)
    monkeypatch.delenv("DOUBAO_API_KEY", raising=False)
    monkeypatch.delenv("ARK_API_KEY", raising=False)
    monkeypatch.delenv("DOUBAO_BASE_URL", raising=False)
    monkeypatch.delenv("ARK_BASE_URL", raising=False)

    client = doubao_client.create_doubao_client(model="demo-model")

    assert captured_kwargs["api_key"] == "settings-key"
    assert captured_kwargs["base_url"] == "https://settings.example/v1"
    assert client.config.model == "demo-model"
