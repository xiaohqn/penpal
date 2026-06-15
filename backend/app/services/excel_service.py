from __future__ import annotations

"""
输入：
- 普通记录、安全记录、批量结果等服务层整理出的字典列表，或用户上传的批量 Excel 二进制内容。
输出：
- 返回用于导入批量来信的结构化行数据，或导出为 Excel 文件的二进制结果。
作用：
- 这个文件集中处理工作台里所有 Excel 导入导出逻辑，避免路由层和 service 层重复拼装表头与序列化细节。
"""
import io
import json
from datetime import datetime
from typing import Any

from openpyxl import Workbook, load_workbook

from app.schemas.record import BatchExcelImportResponse, BatchExcelRow


class ExcelService:
    """
    输入：
    - 来自前后端不同业务链路的结构化记录数据，或上传的 Excel 文件内容。
    输出：
    - 统一返回批量导入解析结果和多种历史导出 Excel 二进制内容。
    作用：
    - 把项目里与 Excel 读写相关的表头约定、字段映射和 JSON 序列化细节集中到一个服务里维护。
    """

    def parse_batch_import(self, content: bytes) -> BatchExcelImportResponse:
        """
        输入：
        - content：用户上传的批量导入 Excel 文件二进制内容。
        输出：
        - 返回过滤空行后的批量导入记录列表及总数。
        作用：
        - 解析批量工作台导入文件，只提取后续生成流程真正需要的 `user_input` 列。
        """

        workbook = load_workbook(filename=io.BytesIO(content), data_only=True)
        sheet = workbook.active

        header_row = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True), None)
        if not header_row:
            raise ValueError("Excel 文件缺少表头")

        headers = [str(cell).strip() if cell is not None else "" for cell in header_row]
        if "user_input" not in headers:
            raise ValueError("Excel 文件必须包含 user_input 列")

        user_input_index = headers.index("user_input")

        items: list[BatchExcelRow] = []
        for row_number, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            user_input = str(row[user_input_index]).strip() if row[user_input_index] is not None else ""
            if not user_input:
                continue

            items.append(
                BatchExcelRow(
                    row_number=row_number,
                    user_input=user_input,
                )
            )

        return BatchExcelImportResponse(items=items, total=len(items))

    def export_records_excel(self, records: list[dict[str, Any]]) -> bytes:
        """
        输入：
        - records：普通人格回信历史记录的完整字典列表。
        输出：
        - 返回一个包含普通人格记录明细的 Excel 二进制内容。
        作用：
        - 为历史记录页导出普通人格回信样本库提供统一的 Excel 生成能力。
        """

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "consultation_records"

        headers = [
            "id",
            "created_at",
            "selected_persona_name",
            "rag_ready",
            "sample_reason",
            "sample_tags_json",
            "planner_labels_json",
            "evaluation_total",
            "evaluation_intent_safety",
            "evaluation_authentic_empathy",
            "evaluation_grounded_guidance",
            "evaluation_narrative_companionship",
            "evaluation_json",
            "user_input",
            "ai_selected_raw_response",
            "expert_polished_response",
            "expert_annotation",
            "sample_snapshot_json",
            "selected_style_config_json",
            "planner_output_json",
            "draft_candidates_json",
        ]
        sheet.append(headers)

        for record in records:
            created_at = record.get("created_at")
            if isinstance(created_at, datetime):
                created_at_value = created_at.isoformat()
            else:
                created_at_value = str(created_at or "")
            evaluation = record.get("evaluation_json", {}) or {}
            scores = evaluation.get("scores", {}) or {}

            sheet.append(
                [
                    record.get("id", ""),
                    created_at_value,
                    record.get("selected_persona_name", ""),
                    record.get("rag_ready", ""),
                    record.get("sample_reason", ""),
                    json.dumps(record.get("sample_tags_json", {}), ensure_ascii=False),
                    json.dumps(record.get("planner_labels_json", {}), ensure_ascii=False),
                    evaluation.get("total_score", ""),
                    scores.get("intent_safety", ""),
                    scores.get("authentic_empathy", ""),
                    scores.get("grounded_guidance", ""),
                    scores.get("narrative_companionship", ""),
                    json.dumps(evaluation, ensure_ascii=False),
                    record.get("user_input", ""),
                    record.get("ai_selected_raw_response", ""),
                    record.get("expert_polished_response", ""),
                    record.get("expert_annotation", ""),
                    json.dumps(record.get("sample_snapshot_json", {}), ensure_ascii=False),
                    json.dumps(record.get("selected_style_config_json", {}), ensure_ascii=False),
                    json.dumps(record.get("planner_output_json", {}), ensure_ascii=False),
                    json.dumps(record.get("draft_candidates_json", []), ensure_ascii=False),
                ]
            )

        output = io.BytesIO()
        workbook.save(output)
        return output.getvalue()

    def export_safety_records_excel(self, records: list[dict[str, Any]]) -> bytes:
        """
        输入：
        - records：安全回复历史记录的完整字典列表。
        输出：
        - 返回一个包含安全回复记录明细的 Excel 二进制内容。
        作用：
        - 为历史记录页导出安全回复样本库提供独立的 Excel 生成能力，便于后续 few-shot / RAG 整理。
        """

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "safety_reply_records"

        headers = [
            "id",
            "created_at",
            "style_name",
            "selected_response_source_label",
            "risk_labels_json",
            "corrected_risk_labels_json",
            "risk_reason",
            "user_input",
            "ai_safe_response",
            "expert_polished_response",
            "expert_annotation",
            "source_annotations_json",
            "response_versions_json",
            "safe_response_candidates_json",
            "sample_snapshot_json",
        ]
        sheet.append(headers)

        for record in records:
            created_at = record.get("created_at")
            if isinstance(created_at, datetime):
                created_at_value = created_at.isoformat()
            else:
                created_at_value = str(created_at or "")

            sheet.append(
                [
                    record.get("id", ""),
                    created_at_value,
                    record.get("style_name", ""),
                    record.get("selected_response_source_label", ""),
                    json.dumps(record.get("risk_labels_json", []), ensure_ascii=False),
                    json.dumps(record.get("corrected_risk_labels_json", []), ensure_ascii=False),
                    record.get("risk_reason", ""),
                    record.get("user_input", ""),
                    record.get("ai_safe_response", ""),
                    record.get("expert_polished_response", ""),
                    record.get("expert_annotation", ""),
                    json.dumps(record.get("source_annotations_json", []), ensure_ascii=False),
                    json.dumps(record.get("response_versions_json", []), ensure_ascii=False),
                    json.dumps(record.get("safe_response_candidates_json", []), ensure_ascii=False),
                    json.dumps(record.get("sample_snapshot_json", {}), ensure_ascii=False),
                ]
            )

        output = io.BytesIO()
        workbook.save(output)
        return output.getvalue()

    def export_batch_generation_excel(self, results: list[dict[str, Any]]) -> bytes:
        """
        输入：
        - results：批量生成人格草稿后的逐行结果列表，包含原始来信、候选人格和多份草稿。
        输出：
        - 返回一个按“每条草稿一行”展开的 Excel 二进制内容。
        作用：
        - 为批量生成阶段提供可离线复核的导出文件，方便在外部继续筛选和比对不同人格草稿。
        """

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "batch_generation_results"

        headers = [
            "row_number",
            "user_input",
            "selected_persona_names",
            "draft_count",
            "persona_name",
            "response",
            "planner_output_json",
        ]
        sheet.append(headers)

        for result in results:
            drafts = result.get("drafts", [])
            if not drafts:
                sheet.append(
                    [
                        result.get("row_number", ""),
                        result.get("user_input", ""),
                        ",".join(result.get("selected_persona_names", [])),
                        0,
                        "",
                        "",
                        "",
                    ]
                )
                continue

            for draft in drafts:
                sheet.append(
                    [
                        result.get("row_number", ""),
                        result.get("user_input", ""),
                        ",".join(result.get("selected_persona_names", [])),
                        result.get("draft_count", 0),
                        draft.get("persona_name", ""),
                        draft.get("response", ""),
                        json.dumps(draft.get("planner_output", {}), ensure_ascii=False),
                    ]
                )

        output = io.BytesIO()
        workbook.save(output)
        return output.getvalue()

    def export_reviewed_batch_excel(self, items: list[dict[str, Any]]) -> bytes:
        """
        输入：
        - items：已经完成人工审阅的批量处理条目列表。
        输出：
        - 返回一个只保留最终结论字段的 Excel 二进制内容。
        作用：
        - 为批量工作流的“已审阅结果导出”提供轻量成品文件，便于交付和后续样本整理。
        """

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "reviewed_batch_results"

        headers = [
            "row_number",
            "user_input",
            "selected_persona_name",
            "rag_ready",
            "sample_reason",
            "evaluation_total",
            "evaluation_intent_safety",
            "evaluation_authentic_empathy",
            "evaluation_grounded_guidance",
            "evaluation_narrative_companionship",
            "evaluation_json",
            "final_response",
            "expert_annotation",
        ]
        sheet.append(headers)

        for item in items:
            evaluation = item.get("evaluation", {}) or {}
            scores = evaluation.get("scores", {}) or {}
            sheet.append(
                [
                    item.get("row_number", ""),
                    item.get("user_input", ""),
                    item.get("selected_persona_name", ""),
                    item.get("rag_ready", ""),
                    item.get("sample_reason", ""),
                    evaluation.get("total_score", ""),
                    scores.get("intent_safety", ""),
                    scores.get("authentic_empathy", ""),
                    scores.get("grounded_guidance", ""),
                    scores.get("narrative_companionship", ""),
                    json.dumps(evaluation, ensure_ascii=False),
                    item.get("final_response", ""),
                    item.get("expert_annotation", ""),
                ]
            )

        output = io.BytesIO()
        workbook.save(output)
        return output.getvalue()
