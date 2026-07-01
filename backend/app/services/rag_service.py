from __future__ import annotations

import re
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ConsultationRecord


LABEL_FIELDS = (
    "surface_issue",
    "core_issue",
    "positive_motive",
    "wrong_but_easy_answer",
    "value_guidance",
    "risk_assessment",
    "response_focus",
)

TAG_KEYWORDS = {
    "亲子沟通": ("妈妈", "爸爸", "父母", "家长", "沟通", "不理解", "管", "没收"),
    "学习动力": ("学习", "成绩", "补课", "上课", "作业", "考试", "数学", "英语", "高考", "中考"),
    "自主感冲突": ("自主", "自由", "被管", "控制", "手机", "自控", "不想听", "不乐意"),
    "人际边界": ("朋友", "同学", "关系", "边界", "拒绝", "表白", "聊天", "排挤"),
    "自我价值": ("自卑", "没用", "不行", "价值", "失败", "普通", "亮点"),
    "故事启发": ("故事", "启发", "名人", "真实人物", "迁移", "案例"),
    "安全风险": ("自杀", "轻生", "自残", "伤害自己", "不想活", "扛不住"),
}


@dataclass(frozen=True)
class RetrievedSample:
    id: int
    score: float
    selected_persona_name: str
    user_input: str
    expert_response: str
    expert_annotation: str
    sample_tags: dict[str, Any]
    planner_labels: dict[str, Any]
    source: str = "record"

    def to_prompt_block(self) -> dict[str, Any]:
        response_limit = 1600 if self.source == "seed" else 1200
        return {
            "record_id": self.id,
            "source": self.source,
            "score": round(self.score, 3),
            "selected_persona_name": self.selected_persona_name,
            "sample_tags": self.sample_tags,
            "planner_labels": self.planner_labels,
            "user_input_excerpt": self.user_input[:700],
            "expert_response_excerpt": self.expert_response[:response_limit],
            "expert_annotation": self.expert_annotation[:500],
        }


class RagService:
    def __init__(self, seed_path: str | None = None, seed_enabled: bool = True):
        self.seed_path = Path(seed_path).expanduser() if seed_path else None
        self.seed_enabled = seed_enabled
        self._seed_samples: list[RetrievedSample] | None = None
        self._seed_mtime_ns: int | None = None

    def seed_status(self) -> dict[str, Any]:
        exists = bool(self.seed_path and self.seed_path.exists())
        return {
            "enabled": self.seed_enabled,
            "path": str(self.seed_path) if self.seed_path else "",
            "exists": exists,
            "loaded_count": len(self._load_seed_samples()) if exists and self.seed_enabled else 0,
            "mtime_ns": self._seed_mtime_ns,
        }

    def build_planner_labels(self, planner_output: dict[str, Any]) -> dict[str, Any]:
        labels = {field: planner_output.get(field, "") for field in LABEL_FIELDS if planner_output.get(field)}
        action_strategy = planner_output.get("action_strategy")
        if isinstance(action_strategy, list):
            labels["action_strategy"] = [str(item) for item in action_strategy[:4]]
        return labels

    def build_sample_tags(
        self,
        user_input: str,
        planner_output: dict[str, Any],
        expert_annotation: str = "",
        source_annotations: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        planner_labels = self.build_planner_labels(planner_output)
        text = " ".join(
            [
                user_input,
                expert_annotation,
                " ".join(str(value) for value in planner_labels.values()),
                " ".join(str(item.get("note", "")) for item in (source_annotations or [])),
            ]
        )
        issue_tags = [
            tag
            for tag, keywords in TAG_KEYWORDS.items()
            if any(keyword in text for keyword in keywords)
        ]
        error_patterns = self._extract_error_patterns(planner_output, expert_annotation)
        return {
            "issue_tags": issue_tags,
            "error_patterns": error_patterns,
            "persona_name": planner_output.get("style_summary", {}).get("persona_name", ""),
            "has_global_feedback": bool(expert_annotation.strip()),
            "has_source_annotations": bool(source_annotations),
        }

    def retrieve_samples(
        self,
        db: Session,
        user_input: str,
        planner_output: dict[str, Any],
        persona_name: str,
        limit: int = 2,
    ) -> list[RetrievedSample]:
        query_tags = self.build_sample_tags(user_input=user_input, planner_output=planner_output)
        query_labels = self.build_planner_labels(planner_output)
        records = db.scalars(
            select(ConsultationRecord)
            .where(ConsultationRecord.rag_ready == "approved")
            .order_by(ConsultationRecord.updated_at.desc())
            .limit(80)
        ).all()

        samples: list[RetrievedSample] = []
        for record in records:
            if not record.expert_polished_response.strip():
                continue
            record_tags = record.sample_tags_json or {}
            record_labels = record.planner_labels_json or {}
            score = self._score(
                query_text=user_input,
                query_tags=query_tags,
                query_labels=query_labels,
                record=record,
                record_tags=record_tags,
                record_labels=record_labels,
                persona_name=persona_name,
            )
            if score <= 0:
                continue
            samples.append(
                RetrievedSample(
                    id=record.id,
                    score=score,
                    selected_persona_name=record.selected_persona_name,
                    user_input=record.user_input,
                    expert_response=record.expert_polished_response,
                    expert_annotation=record.expert_annotation,
                    sample_tags=record_tags,
                    planner_labels=record_labels,
                )
            )

        samples.extend(
            self._retrieve_seed_samples(
                user_input=user_input,
                query_tags=query_tags,
                query_labels=query_labels,
            )
        )
        samples.sort(key=lambda item: item.score, reverse=True)
        return samples[:limit]

    def _retrieve_seed_samples(
        self,
        user_input: str,
        query_tags: dict[str, Any],
        query_labels: dict[str, Any],
    ) -> list[RetrievedSample]:
        seed_samples = self._load_seed_samples()
        scored: list[RetrievedSample] = []
        for sample in seed_samples:
            score = self._score_seed_sample(
                query_text=user_input,
                query_tags=query_tags,
                query_labels=query_labels,
                sample=sample,
            )
            if score <= 0:
                continue
            scored.append(
                RetrievedSample(
                    id=sample.id,
                    score=score,
                    selected_persona_name=sample.selected_persona_name,
                    user_input=sample.user_input,
                    expert_response=sample.expert_response,
                    expert_annotation=sample.expert_annotation,
                    sample_tags=sample.sample_tags,
                    planner_labels=sample.planner_labels,
                    source=sample.source,
                )
            )
        return scored

    def _load_seed_samples(self) -> list[RetrievedSample]:
        current_mtime_ns: int | None = None
        if self.seed_enabled and self.seed_path is not None and self.seed_path.exists():
            current_mtime_ns = self.seed_path.stat().st_mtime_ns
        if self._seed_samples is not None and self._seed_mtime_ns == current_mtime_ns:
            return self._seed_samples
        if not self.seed_enabled or self.seed_path is None or not self.seed_path.exists():
            self._seed_samples = []
            self._seed_mtime_ns = current_mtime_ns
            return self._seed_samples
        try:
            raw = json.loads(self.seed_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self._seed_samples = []
            self._seed_mtime_ns = current_mtime_ns
            return self._seed_samples
        if not isinstance(raw, list):
            self._seed_samples = []
            self._seed_mtime_ns = current_mtime_ns
            return self._seed_samples

        samples: list[RetrievedSample] = []
        for index, item in enumerate(raw, start=1):
            if not isinstance(item, dict):
                continue
            user_input = str(item.get("send_content", "")).strip()
            response = str(item.get("reply_content", "")).strip()
            if not user_input or not response:
                continue
            pseudo_planner = {
                "core_issue": self._infer_seed_core_issue(user_input),
                "style_summary": {"persona_name": "seed"},
            }
            samples.append(
                RetrievedSample(
                    id=-(int(item.get("index") or index)),
                    score=0.0,
                    selected_persona_name="seed",
                    user_input=user_input,
                    expert_response=response,
                    expert_annotation="现场种子库参考回复",
                    sample_tags=self.build_sample_tags(user_input=user_input, planner_output=pseudo_planner),
                    planner_labels=self.build_planner_labels(pseudo_planner),
                    source="seed",
                )
            )
        self._seed_samples = samples
        self._seed_mtime_ns = current_mtime_ns
        return self._seed_samples

    def _score(
        self,
        query_text: str,
        query_tags: dict[str, Any],
        query_labels: dict[str, Any],
        record: ConsultationRecord,
        record_tags: dict[str, Any],
        record_labels: dict[str, Any],
        persona_name: str,
    ) -> float:
        score = 0.0
        query_issue_tags = set(query_tags.get("issue_tags") or [])
        record_issue_tags = set(record_tags.get("issue_tags") or [])
        score += 2.4 * len(query_issue_tags & record_issue_tags)

        query_errors = set(query_tags.get("error_patterns") or [])
        record_errors = set(record_tags.get("error_patterns") or [])
        score += 1.8 * len(query_errors & record_errors)

        if record.selected_persona_name == persona_name:
            score += 1.0

        query_core = str(query_labels.get("core_issue", ""))
        record_core = str(record_labels.get("core_issue", ""))
        score += 2.0 * self._text_overlap(query_core, record_core)
        score += 1.2 * self._text_overlap(query_text, record.user_input)
        return score

    def _score_seed_sample(
        self,
        query_text: str,
        query_tags: dict[str, Any],
        query_labels: dict[str, Any],
        sample: RetrievedSample,
    ) -> float:
        score = 0.0
        query_issue_tags = set(query_tags.get("issue_tags") or [])
        sample_issue_tags = set(sample.sample_tags.get("issue_tags") or [])
        score += 2.0 * len(query_issue_tags & sample_issue_tags)
        score += 1.6 * self._text_overlap(str(query_labels.get("core_issue", "")), str(sample.planner_labels.get("core_issue", "")))
        score += 1.4 * self._text_overlap(query_text, sample.user_input)
        return score

    def _extract_error_patterns(self, planner_output: dict[str, Any], expert_annotation: str) -> list[str]:
        text = f"{planner_output.get('wrong_but_easy_answer', '')} {expert_annotation}"
        patterns = []
        candidates = {
            "抓错核心": ("核心", "本质", "抓错", "没抓住"),
            "建议表面": ("表面", "治标", "泛泛", "空泛", "不够有深度"),
            "故事无启发": ("故事", "启发", "平平无奇", "生硬", "复述"),
            "缺少价值观": ("价值观", "引导", "学习不重要", "误解"),
            "缺少话术": ("话术", "具体", "可操作", "方法"),
        }
        for pattern, keywords in candidates.items():
            if any(keyword in text for keyword in keywords):
                patterns.append(pattern)
        return patterns

    def _text_overlap(self, left: str, right: str) -> float:
        left_tokens = self._tokenize(left)
        right_tokens = self._tokenize(right)
        if not left_tokens or not right_tokens:
            return 0.0
        return len(left_tokens & right_tokens) / max(len(left_tokens), 1)

    def _tokenize(self, text: str) -> set[str]:
        chunks = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]+", text)
        tokens: set[str] = set()
        for chunk in chunks:
            if re.fullmatch(r"[\u4e00-\u9fff]+", chunk):
                tokens.update(chunk[index : index + 2] for index in range(max(0, len(chunk) - 1)))
            else:
                tokens.add(chunk.lower())
        return tokens

    def _infer_seed_core_issue(self, user_input: str) -> str:
        tags = [
            tag
            for tag, keywords in TAG_KEYWORDS.items()
            if any(keyword in user_input for keyword in keywords)
        ]
        if tags:
            return "、".join(tags)
        return user_input[:80]
