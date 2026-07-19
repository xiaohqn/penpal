#!/usr/bin/env python3
"""Export letter processing trajectories from the app SQLite database.

This script joins the main process tables used by the counselor workspace:
mail_threads, mail_messages, risk_assessments, conversation_memories,
batch_sessions, batch_session_items, and consultation_records.

Examples:
  python scripts/export_letter_processes.py
  python scripts/export_letter_processes.py --db data/app.db --out exports/letter_processes.json
  python scripts/export_letter_processes.py --db data/app.db --xlsx exports/letter_processes.xlsx
  python scripts/export_letter_processes.py --completed-only --counselor-id counselor_a
  python scripts/export_letter_processes.py --include-user-side
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "app.db"
DEFAULT_JSON_OUT = Path("exports") / "letter_processes.json"

JSON_COLUMNS = {
    "selected_style_config_json",
    "planner_output_json",
    "draft_candidates_json",
    "source_annotations_json",
    "response_versions_json",
    "sample_snapshot_json",
    "sample_tags_json",
    "planner_labels_json",
    "risk_assessment_json",
    "evaluation_json",
    "context_json",
    "selected_persona_names_json",
    "categories_json",
    "signals_json",
    "state_json",
}

LIST_JSON_COLUMNS = {
    "draft_candidates_json",
    "source_annotations_json",
    "response_versions_json",
    "selected_persona_names_json",
    "categories_json",
    "signals_json",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export full letter processing trajectories.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Path to the SQLite app.db.")
    parser.add_argument(
        "--out",
        default=str(DEFAULT_JSON_OUT),
        help="Output JSON path. Parent directories are created automatically.",
    )
    parser.add_argument(
        "--xlsx",
        default="",
        help="Optional Excel summary output path, for example exports/letter_processes.xlsx.",
    )
    parser.add_argument(
        "--counselor-id",
        default="",
        help="Only export processes handled by this counselor id. Empty exports all.",
    )
    parser.add_argument(
        "--completed-only",
        action="store_true",
        help="Only export completed/sent processes where possible.",
    )
    parser.add_argument(
        "--include-orphan-records",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include consultation_records that cannot be linked to a mail thread or batch item.",
    )
    parser.add_argument(
        "--include-user-side",
        action="store_true",
        help="Also include user-side AI-only mail threads and user-satisfied AI records. Disabled by default.",
    )
    parser.add_argument(
        "--pretty",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Pretty-print JSON output. Enabled by default.",
    )
    return parser.parse_args()


def parse_json_value(value: Any, fallback: Any) -> Any:
    if value is None or value == "":
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def has_table(conn: sqlite3.Connection, table_name: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
        is not None
    )


def load_table(conn: sqlite3.Connection, table_name: str) -> list[dict[str, Any]]:
    if not has_table(conn, table_name):
        return []
    rows = conn.execute(f"SELECT * FROM {table_name}").fetchall()
    return [normalize_row(dict(row)) for row in rows]


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    for column in JSON_COLUMNS:
        if column not in row:
            continue
        fallback: Any = [] if column in LIST_JSON_COLUMNS else {}
        row[column] = parse_json_value(row[column], fallback)
    return row


def group_by(rows: list[dict[str, Any]], key: str) -> dict[Any, list[dict[str, Any]]]:
    grouped: dict[Any, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row.get(key), []).append(row)
    return grouped


def index_by_id(rows: list[dict[str, Any]]) -> dict[Any, dict[str, Any]]:
    return {row.get("id"): row for row in rows if row.get("id") is not None}


def first_user_message(messages: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next((message for message in messages if message.get("sender_type") == "user"), None)


def latest_user_message(messages: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next((message for message in reversed(messages) if message.get("sender_type") == "user"), None)


def latest_counselor_message(messages: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next((message for message in reversed(messages) if message.get("sender_type") == "counselor"), None)


def latest_risk(risks: list[dict[str, Any]], target_type: str = "user_letter") -> dict[str, Any] | None:
    filtered = [risk for risk in risks if risk.get("target_type") == target_type]
    return filtered[-1] if filtered else None


def record_mail_thread_id(record: dict[str, Any]) -> int | None:
    snapshot = record.get("sample_snapshot_json") or {}
    value = snapshot.get("mail_thread_id") if isinstance(snapshot, dict) else None
    return int(value) if isinstance(value, int) or (isinstance(value, str) and value.isdigit()) else None


def build_processes(
    *,
    mail_threads: list[dict[str, Any]],
    mail_messages: list[dict[str, Any]],
    memories: list[dict[str, Any]],
    risks: list[dict[str, Any]],
    batch_sessions: list[dict[str, Any]],
    batch_items: list[dict[str, Any]],
    records: list[dict[str, Any]],
    counselor_id: str,
    completed_only: bool,
    include_orphan_records: bool,
    include_user_side: bool,
) -> list[dict[str, Any]]:
    messages_by_thread = group_by(sorted(mail_messages, key=lambda item: (str(item.get("created_at") or ""), item.get("id") or 0)), "thread_id")
    risks_by_thread = group_by(sorted(risks, key=lambda item: (str(item.get("created_at") or ""), item.get("id") or 0)), "thread_id")
    memory_by_thread = {memory.get("thread_id"): memory for memory in memories}
    sessions_by_id = index_by_id(batch_sessions)
    items_by_thread = group_by(batch_items, "mail_thread_id")
    records_by_batch_item = group_by(records, "batch_item_id")

    records_by_thread: dict[int, list[dict[str, Any]]] = {}
    for record in records:
        thread_id = record_mail_thread_id(record)
        if thread_id is not None:
            records_by_thread.setdefault(thread_id, []).append(record)

    processes: list[dict[str, Any]] = []
    used_batch_item_ids: set[int] = set()
    used_record_ids: set[int] = set()

    for thread in sorted(mail_threads, key=lambda item: (str(item.get("created_at") or ""), item.get("id") or 0)):
        thread_id = thread.get("id")
        workspace_items = sorted(items_by_thread.get(thread_id, []), key=lambda item: (str(item.get("updated_at") or ""), item.get("id") or 0))
        if counselor_id:
            assigned = thread.get("assigned_counselor_id")
            item_counselors = {
                (sessions_by_id.get(item.get("session_id")) or {}).get("counselor_id")
                for item in workspace_items
            }
            record_counselors = {record.get("counselor_id") for record in records_by_thread.get(thread_id, [])}
            if counselor_id not in {assigned, *item_counselors, *record_counselors}:
                continue

        process_messages = messages_by_thread.get(thread_id, [])
        process_risks = risks_by_thread.get(thread_id, [])
        linked_records = list(records_by_thread.get(thread_id, []))
        for item in workspace_items:
            used_batch_item_ids.add(item.get("id"))
            linked_records.extend(records_by_batch_item.get(item.get("id"), []))
        linked_records = dedupe_by_id(linked_records)
        used_record_ids.update(record.get("id") for record in linked_records if record.get("id") is not None)

        if not include_user_side and not is_counselor_handled_thread(
            thread=thread,
            messages=process_messages,
            workspace_items=workspace_items,
            records=linked_records,
            sessions_by_id=sessions_by_id,
        ):
            continue

        if completed_only and not is_completed_thread_process(thread, workspace_items, linked_records, process_messages):
            continue

        processes.append(
            build_thread_process(
                thread=thread,
                messages=process_messages,
                risks=process_risks,
                memory=memory_by_thread.get(thread_id),
                workspace_items=workspace_items,
                sessions_by_id=sessions_by_id,
                records=linked_records,
            )
        )

    for item in sorted(batch_items, key=lambda row: (row.get("session_id") or 0, row.get("row_number") or 0, row.get("id") or 0)):
        item_id = item.get("id")
        if item_id in used_batch_item_ids:
            continue
        session = sessions_by_id.get(item.get("session_id")) or {}
        if not include_user_side and is_user_side_counselor_id(session.get("counselor_id")):
            continue
        if counselor_id and session.get("counselor_id") != counselor_id:
            continue
        if completed_only and item.get("status") != "completed":
            continue
        linked_records = records_by_batch_item.get(item_id, [])
        used_record_ids.update(record.get("id") for record in linked_records if record.get("id") is not None)
        processes.append(build_batch_item_process(item=item, session=session, records=linked_records))

    if include_orphan_records:
        for record in sorted(records, key=lambda row: row.get("id") or 0):
            record_id = record.get("id")
            if record_id in used_record_ids:
                continue
            if not include_user_side and is_user_side_counselor_id(record.get("counselor_id")):
                continue
            if counselor_id and record.get("counselor_id") != counselor_id:
                continue
            if completed_only and not str(record.get("expert_polished_response") or "").strip():
                continue
            processes.append(build_record_process(record))

    return processes


def is_user_side_counselor_id(value: Any) -> bool:
    return str(value or "").startswith("user:")


def is_counselor_handled_thread(
    *,
    thread: dict[str, Any],
    messages: list[dict[str, Any]],
    workspace_items: list[dict[str, Any]],
    records: list[dict[str, Any]],
    sessions_by_id: dict[Any, dict[str, Any]],
) -> bool:
    if thread.get("assigned_counselor_id"):
        return True
    if any(message.get("sender_type") == "counselor" for message in messages):
        return True
    for item in workspace_items:
        session = sessions_by_id.get(item.get("session_id")) or {}
        if not is_user_side_counselor_id(session.get("counselor_id")):
            return True
    return any(not is_user_side_counselor_id(record.get("counselor_id")) for record in records)


def dedupe_by_id(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[Any] = set()
    result: list[dict[str, Any]] = []
    for row in rows:
        row_id = row.get("id")
        marker = row_id if row_id is not None else id(row)
        if marker in seen:
            continue
        seen.add(marker)
        result.append(row)
    return result


def is_completed_thread_process(
    thread: dict[str, Any],
    workspace_items: list[dict[str, Any]],
    records: list[dict[str, Any]],
    messages: list[dict[str, Any]],
) -> bool:
    if thread.get("status") in {"waiting_user", "completed"} and latest_counselor_message(messages):
        return True
    if any(item.get("status") == "completed" for item in workspace_items):
        return True
    return bool(records)


def build_thread_process(
    *,
    thread: dict[str, Any],
    messages: list[dict[str, Any]],
    risks: list[dict[str, Any]],
    memory: dict[str, Any] | None,
    workspace_items: list[dict[str, Any]],
    sessions_by_id: dict[Any, dict[str, Any]],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    workspace_payloads = [
        {
            "batch_session": summarize_session(sessions_by_id.get(item.get("session_id")) or {}),
            "item": item,
        }
        for item in workspace_items
    ]
    summary = summarize_process(
        source_type="mail_thread",
        thread=thread,
        messages=messages,
        risks=risks,
        workspace_items=workspace_items,
        records=records,
    )
    if not summary.get("counselor_id"):
        summary["counselor_id"] = first_workspace_counselor_id(workspace_payloads)
    return {
        "process_id": f"mail_thread:{thread.get('id')}",
        "source_type": "mail_thread",
        "summary": summary,
        "mail_thread": thread,
        "messages": messages,
        "conversation_memory": memory or {},
        "risk_assessments": risks,
        "workspace_items": workspace_payloads,
        "consultation_records": records,
    }


def build_batch_item_process(item: dict[str, Any], session: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    summary = summarize_process(
        source_type="batch_item",
        thread={},
        messages=[],
        risks=[item.get("risk_assessment_json") or {}],
        workspace_items=[item],
        records=records,
    )
    if not summary.get("counselor_id"):
        summary["counselor_id"] = session.get("counselor_id")
    return {
        "process_id": f"batch_item:{item.get('id')}",
        "source_type": "batch_item",
        "summary": summary,
        "mail_thread": {},
        "messages": [],
        "conversation_memory": {},
        "risk_assessments": [item.get("risk_assessment_json") or {}],
        "workspace_items": [{"batch_session": summarize_session(session), "item": item}],
        "consultation_records": records,
    }


def first_workspace_counselor_id(workspace_payloads: list[dict[str, Any]]) -> str:
    for payload in workspace_payloads:
        session = payload.get("batch_session") or {}
        counselor_id = str(session.get("counselor_id") or "")
        if counselor_id:
            return counselor_id
    return ""


def build_record_process(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "process_id": f"record:{record.get('id')}",
        "source_type": "consultation_record",
        "summary": summarize_process(
            source_type="consultation_record",
            thread={},
            messages=[],
            risks=[record.get("risk_assessment_json") or {}],
            workspace_items=[],
            records=[record],
        ),
        "mail_thread": {},
        "messages": [],
        "conversation_memory": {},
        "risk_assessments": [record.get("risk_assessment_json") or {}],
        "workspace_items": [],
        "consultation_records": [record],
    }


def summarize_session(session: dict[str, Any]) -> dict[str, Any]:
    if not session:
        return {}
    return {
        "id": session.get("id"),
        "counselor_id": session.get("counselor_id"),
        "title": session.get("title"),
        "source_file_name": session.get("source_file_name"),
        "status": session.get("status"),
        "created_at": session.get("created_at"),
        "updated_at": session.get("updated_at"),
    }


def summarize_process(
    *,
    source_type: str,
    thread: dict[str, Any],
    messages: list[dict[str, Any]],
    risks: list[dict[str, Any]],
    workspace_items: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    first_user = first_user_message(messages)
    latest_user = latest_user_message(messages)
    latest_counselor = latest_counselor_message(messages)
    latest_item = workspace_items[-1] if workspace_items else {}
    latest_record = records[-1] if records else {}
    risk = latest_risk(risks) or (risks[-1] if risks else {})
    final_response = (
        (latest_counselor or {}).get("content")
        or latest_item.get("latest_response")
        or latest_record.get("expert_polished_response")
        or ""
    )
    user_input = (
        (latest_user or {}).get("content")
        or latest_item.get("user_input")
        or latest_record.get("user_input")
        or ""
    )
    annotations = latest_item.get("source_annotations_json") or latest_record.get("source_annotations_json") or []
    versions = latest_item.get("response_versions_json") or latest_record.get("response_versions_json") or []
    drafts = latest_item.get("draft_candidates_json") or latest_record.get("draft_candidates_json") or []
    snapshot = latest_item.get("sample_snapshot_json") or latest_record.get("sample_snapshot_json") or {}
    initial_ai_response = snapshot.get("initial_ai_response") or latest_record.get("ai_selected_raw_response") or latest_item.get("ai_selected_raw_response") or ""
    finalization_mode = snapshot.get("finalization_mode") or infer_finalization_mode(initial_ai_response, final_response, versions)
    return {
        "source_type": source_type,
        "mail_thread_id": thread.get("id"),
        "batch_item_id": latest_item.get("id"),
        "record_id": latest_record.get("id"),
        "user_id": thread.get("user_id"),
        "counselor_id": latest_record.get("counselor_id") or thread.get("assigned_counselor_id"),
        "assigned_counselor_id": thread.get("assigned_counselor_id"),
        "status": latest_item.get("status") or thread.get("status") or latest_record.get("rag_ready") or "",
        "created_at": thread.get("created_at") or latest_item.get("created_at") or latest_record.get("created_at"),
        "updated_at": latest_item.get("updated_at") or thread.get("updated_at") or latest_record.get("updated_at"),
        "message_count": len(messages),
        "user_input": user_input,
        "first_user_input": (first_user or {}).get("content") or user_input,
        "final_response": final_response,
        "initial_ai_response": initial_ai_response,
        "ai_selected_raw_response": latest_item.get("ai_selected_raw_response") or latest_record.get("ai_selected_raw_response") or "",
        "finalization_mode": finalization_mode,
        "expert_annotation": latest_item.get("expert_annotation") or latest_record.get("expert_annotation") or "",
        "selected_persona_name": latest_item.get("selected_persona_name") or latest_record.get("selected_persona_name") or "",
        "risk_level": risk.get("risk_level") or risk.get("level") or "",
        "risk_reasoning": risk.get("reasoning") or "",
        "annotation_count": len(annotations) if isinstance(annotations, list) else 0,
        "version_count": len(versions) if isinstance(versions, list) else 0,
        "draft_count": len(drafts) if isinstance(drafts, list) else 0,
        "record_count": len(records),
    }


def infer_finalization_mode(initial_response: str, final_response: str, versions: list[dict[str, Any]]) -> str:
    if versions:
        source = str((versions[-1] or {}).get("source") or "")
        if source in {"planner_regenerate", "annotation_patch"}:
            return source
    if str(initial_response or "").strip() and str(initial_response or "").strip() != str(final_response or "").strip():
        return "manual_edit"
    return "direct_accept"


def write_json(path: Path, payload: Any, pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None)
    path.write_text(text + "\n", encoding="utf-8")


def write_xlsx(path: Path, processes: list[dict[str, Any]]) -> None:
    try:
        from openpyxl import Workbook
    except ImportError as exc:
        raise SystemExit("openpyxl is required for --xlsx. Install backend requirements first.") from exc

    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "letter_processes"
    headers = [
        "process_id",
        "source_type",
        "mail_thread_id",
        "batch_item_id",
        "record_id",
        "user_id",
        "counselor_id",
        "status",
        "created_at",
        "updated_at",
        "risk_level",
        "finalization_mode",
        "message_count",
        "draft_count",
        "annotation_count",
        "version_count",
        "record_count",
        "selected_persona_name",
        "user_input",
        "initial_ai_response",
        "ai_selected_raw_response",
        "final_response",
        "expert_annotation",
        "risk_reasoning",
    ]
    sheet.append(headers)
    for process in processes:
        summary = process.get("summary", {})
        sheet.append(
            [
                process.get("process_id", ""),
                summary.get("source_type", ""),
                summary.get("mail_thread_id", ""),
                summary.get("batch_item_id", ""),
                summary.get("record_id", ""),
                summary.get("user_id", ""),
                summary.get("counselor_id", ""),
                summary.get("status", ""),
                summary.get("created_at", ""),
                summary.get("updated_at", ""),
                summary.get("risk_level", ""),
                summary.get("finalization_mode", ""),
                summary.get("message_count", ""),
                summary.get("draft_count", ""),
                summary.get("annotation_count", ""),
                summary.get("version_count", ""),
                summary.get("record_count", ""),
                summary.get("selected_persona_name", ""),
                summary.get("user_input", ""),
                summary.get("initial_ai_response", ""),
                summary.get("ai_selected_raw_response", ""),
                summary.get("final_response", ""),
                summary.get("expert_annotation", ""),
                summary.get("risk_reasoning", ""),
            ]
        )
    workbook.save(path)


def main() -> None:
    args = parse_args()
    db_path = Path(args.db).expanduser().resolve()
    if not db_path.exists():
        raise SystemExit(f"Database does not exist: {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        processes = build_processes(
            mail_threads=load_table(conn, "mail_threads"),
            mail_messages=load_table(conn, "mail_messages"),
            memories=load_table(conn, "conversation_memories"),
            risks=load_table(conn, "risk_assessments"),
            batch_sessions=load_table(conn, "batch_sessions"),
            batch_items=load_table(conn, "batch_session_items"),
            records=load_table(conn, "consultation_records"),
            counselor_id=args.counselor_id.strip(),
            completed_only=args.completed_only,
            include_orphan_records=args.include_orphan_records,
            include_user_side=args.include_user_side,
        )
    finally:
        conn.close()

    out_path = Path(args.out).expanduser()
    write_json(out_path, processes, pretty=args.pretty)
    print(f"Exported {len(processes)} letter processes to {out_path}")
    if args.xlsx:
        xlsx_path = Path(args.xlsx).expanduser()
        write_xlsx(xlsx_path, processes)
        print(f"Exported Excel summary to {xlsx_path}")
    print(f"Source database: {db_path}")


if __name__ == "__main__":
    main()
