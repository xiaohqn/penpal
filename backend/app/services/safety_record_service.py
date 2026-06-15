"""
输入：
- 数据库会话 `Session`。
- 前端提交的安全回复记录保存请求，或列表/详情/导出查询参数。
输出：
- 创建安全回复记录、分页列出安全回复记录、返回单条安全回复记录详情、删除指定记录、
  导出全部安全回复记录，或按人工修正后的风险标签检索 few-shot 安全回复样本。
作用：
- 这个 service 封装安全回复记录的持久化逻辑，让路由层只负责 HTTP 协议处理。
"""
from dataclasses import dataclass
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db.models import SafetyReplyRecord
from app.schemas.safety_record import (
    SafetyReplyRecordListItem,
    SafetyReplyRecordListResponse,
    SafetyReplyRecordResponse,
    SafetyReplyRecordSaveRequest,
    hydrate_safety_reply_record_response,
)


class SafetyRecordService:
    """
    输入：
    - 数据库会话和安全回复记录相关的请求参数。
    输出：
    - 对应的安全回复记录创建结果、列表结果、详情结果、删除结果或 few-shot 检索结果。
    作用：
    - 统一管理安全回复记录的数据库读写流程。
    """

    def create_record(
        self,
        db: Session,
        payload: SafetyReplyRecordSaveRequest,
    ) -> SafetyReplyRecordResponse:
        """
        输入：
        - db：当前请求绑定的数据库会话。
        - payload：前端提交的安全回复记录保存数据。
        输出：
        - 返回已写入数据库并刷新后的安全回复记录详情。
        作用：
        - 把一次安全回复结果固化为可复查、可复用的历史样本。
        """

        sample_snapshot = dict(payload.sample_snapshot)
        if payload.safety_evaluation:
            # 安全对话评分暂时复用过程快照承载，避免为单个评价扩展引入数据库迁移；
            # 响应层会再把它提升为 `safety_evaluation` 字段，供前端详情页直接展示。
            sample_snapshot["safety_evaluation"] = payload.safety_evaluation

        record = SafetyReplyRecord(
            style_name="安全",
            user_input=payload.user_input,
            risk_labels_json=payload.risk_labels,
            corrected_risk_labels_json=payload.corrected_risk_labels,
            risk_reason=payload.risk_reason,
            ai_safe_response=payload.ai_safe_response,
            expert_polished_response=payload.expert_polished_response,
            selected_response_source=payload.selected_response_source,
            selected_response_source_label=payload.selected_response_source_label,
            safe_response_candidates_json=payload.safe_response_candidates,
            expert_annotation=payload.expert_annotation,
            sample_snapshot_json=sample_snapshot,
            source_annotations_json=payload.source_annotations,
            response_versions_json=payload.response_versions,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return hydrate_safety_reply_record_response(record)

    def list_records(
        self,
        db: Session,
        page: int,
        page_size: int,
    ) -> SafetyReplyRecordListResponse:
        """
        输入：
        - db：数据库会话。
        - page / page_size：分页参数。
        输出：
        - 返回按创建时间倒序排列的安全回复记录分页结果。
        作用：
        - 为历史页左侧列表提供安全回复记录概览。
        """

        total = db.scalar(select(func.count()).select_from(SafetyReplyRecord)) or 0
        offset = (page - 1) * page_size
        records = db.scalars(
            select(SafetyReplyRecord)
            .order_by(desc(SafetyReplyRecord.created_at))
            .offset(offset)
            .limit(page_size)
        ).all()

        items = [
            SafetyReplyRecordListItem(
                id=record.id,
                style_name=record.style_name,
                user_input=record.user_input,
                created_at=record.created_at,
                updated_at=record.updated_at,
            )
            for record in records
        ]
        return SafetyReplyRecordListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_record(self, db: Session, record_id: int) -> SafetyReplyRecordResponse | None:
        """
        输入：
        - db：数据库会话。
        - record_id：目标安全回复记录 ID。
        输出：
        - 找到则返回安全回复记录详情；找不到则返回 `None`。
        作用：
        - 为历史页右侧详情面板按 ID 读取完整记录。
        """

        record = db.get(SafetyReplyRecord, record_id)
        if record is None:
            return None
        return hydrate_safety_reply_record_response(record)

    def delete_record(self, db: Session, record_id: int) -> bool:
        """
        输入：
        - db：数据库会话。
        - record_id：要删除的安全回复记录 ID。
        输出：
        - 删除成功返回 `True`；如果记录不存在则返回 `False`。
        作用：
        - 为历史页的删除动作提供底层持久化能力，确保样本库可以移除误存或无效数据。
        """

        record = db.get(SafetyReplyRecord, record_id)
        if record is None:
            return False

        db.delete(record)
        db.commit()
        return True

    def get_all_records_for_export(self, db: Session) -> list[dict]:
        """
        输入：
        - db：数据库会话。
        输出：
        - 返回按创建时间倒序排列的全部安全回复记录字典列表。
        作用：
        - 为“历史安全回复导出 Excel”提供统一的数据读取入口，避免路由层直接拼 ORM 字段。
        """

        records = db.scalars(
            select(SafetyReplyRecord).order_by(desc(SafetyReplyRecord.created_at))
        ).all()
        return [hydrate_safety_reply_record_response(record).model_dump() for record in records]

    @dataclass(frozen=True)
    class FewShotExample:
        """
        输入：
        - 来自安全回复历史库中与当前风险标签匹配的一条高质量记录。
        输出：
        - 提供 few-shot 提示词拼接所需的精简样本结构。
        作用：
        - 把数据库 ORM 记录转换成更稳定、对生成层更友好的检索结果载体。
        """

        record_id: int
        corrected_risk_labels: list[str]
        user_input: str
        risk_reason: str
        expert_polished_response: str

    def find_few_shot_examples_by_corrected_labels(
        self,
        db: Session,
        corrected_risk_labels: list[str],
        limit: int = 3,
    ) -> list["SafetyRecordService.FewShotExample"]:
        """
        输入：
        - db：数据库会话。
        - corrected_risk_labels：当前待生成安全回复的人工修正后风险标签列表。
        - limit：最多返回多少条 few-shot 样本，默认 3 条。
        输出：
        - 返回按“标签完全匹配优先、交集越多越优先、最新记录优先”排序的 few-shot 样本列表。
        作用：
        - 仅基于 `corrected_risk_labels_json` 从历史安全记录中检索最合适的参考案例，
          为后续安全回复生成提供稳定、可控的 few-shot 上下文。
        """

        normalized_query_labels = self._normalize_risk_labels(corrected_risk_labels)
        if not normalized_query_labels or limit <= 0:
            return []

        query_label_set = set(normalized_query_labels)
        records = db.scalars(
            select(SafetyReplyRecord).order_by(desc(SafetyReplyRecord.created_at))
        ).all()

        ranked_records: list[
            tuple[int, int, int, float, SafetyReplyRecord]
        ] = []
        for record in records:
            normalized_record_labels = self._normalize_risk_labels(record.corrected_risk_labels_json)
            if not normalized_record_labels:
                continue

            record_label_set = set(normalized_record_labels)
            overlap_count = len(query_label_set & record_label_set)
            if overlap_count == 0:
                continue

            exact_match_score = 1 if record_label_set == query_label_set else 0
            label_count_distance = abs(len(record_label_set) - len(query_label_set))
            created_at_score = record.created_at.timestamp()
            ranked_records.append(
                (
                    exact_match_score,
                    overlap_count,
                    -label_count_distance,
                    created_at_score,
                    record,
                )
            )

        ranked_records.sort(reverse=True)
        selected_records = [item[-1] for item in ranked_records[:limit]]
        return [
            self.FewShotExample(
                record_id=record.id,
                corrected_risk_labels=self._normalize_risk_labels(record.corrected_risk_labels_json),
                user_input=record.user_input,
                risk_reason=record.risk_reason,
                expert_polished_response=record.expert_polished_response,
            )
            for record in selected_records
        ]

    @staticmethod
    def _normalize_risk_labels(labels: list[str]) -> list[str]:
        """
        输入：
        - labels：数据库中已保存或当前待检索的风险标签列表。
        输出：
        - 返回去空白、去空项、去重后的标签列表，并保留原有顺序。
        作用：
        - 保证 few-shot 检索时的标签集合比较稳定可靠，不受空白字符和重复标签干扰。
        """

        normalized_labels: list[str] = []
        for label in labels:
            cleaned_label = label.strip()
            if cleaned_label and cleaned_label not in normalized_labels:
                normalized_labels.append(cleaned_label)
        return normalized_labels
