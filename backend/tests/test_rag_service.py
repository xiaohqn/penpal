import json

from app.services.rag_service import RagService


class EmptyScalarResult:
    def all(self):
        return []


class EmptySession:
    def scalars(self, *args, **kwargs):
        return EmptyScalarResult()


def test_seed_exact_user_input_retrieves_itself(tmp_path):
    seed_path = tmp_path / "seed.json"
    user_input = "难道我很差吗？不管我怎么努力学习都上不去。"
    seed_path.write_text(
        json.dumps(
            [
                {
                    "index": 100,
                    "send_content": user_input,
                    "reply_content": "同学，你好。努力没有立刻转化成成绩，并不代表你很差。",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    service = RagService(seed_path=str(seed_path))
    samples = service.retrieve_samples(
        db=EmptySession(),
        user_input=user_input,
        planner_output={"core_issue": user_input, "style_summary": {"persona_name": "理性破局教练"}},
        persona_name="理性破局教练",
        limit=1,
    )

    assert len(samples) == 1
    assert samples[0].id == -100
    assert samples[0].user_input == user_input


def test_seed_cache_refreshes_when_file_changes(tmp_path):
    seed_path = tmp_path / "seed.json"
    seed_path.write_text(
        json.dumps(
            [
                {
                    "index": 1,
                    "send_content": "旧来信",
                    "reply_content": "旧回信",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = RagService(seed_path=str(seed_path))
    assert service.seed_status()["loaded_count"] == 1

    seed_path.write_text(
        json.dumps(
            [
                {
                    "index": 1,
                    "send_content": "旧来信",
                    "reply_content": "旧回信",
                },
                {
                    "index": 2,
                    "send_content": "新来信",
                    "reply_content": "新回信",
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    assert service.seed_status()["loaded_count"] == 2
