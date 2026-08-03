#!/usr/bin/env python3
"""Export counselor records and cleaned research trajectories for AI analysis.

Examples:
  python scripts/export_counselors_for_ai.py
  python scripts/export_counselors_for_ai.py \
    --db data/app.db \
    --display-names 01,02,03,04 \
    --out exports/counselors_01_04_for_ai.json
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "app.db"
DEFAULT_OUT_PATH = PROJECT_ROOT / "exports" / "counselors_01_04_for_ai.json"
DEFAULT_DISPLAY_NAMES = ("01", "02", "03", "04")

RECORD_JSON_COLUMNS = {
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
}
EVENT_JSON_COLUMNS = {"diff_json", "annotations_json", "metadata_json"}
LIST_JSON_COLUMNS = {
    "draft_candidates_json",
    "source_annotations_json",
    "response_versions_json",
    "diff_json",
    "annotations_json",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export counselors 01-04 records and cleaned interaction events for AI analysis."
    )
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Path to the SQLite app.db.")
    parser.add_argument(
        "--display-names",
        default=",".join(DEFAULT_DISPLAY_NAMES),
        help="Comma-separated account display names. Default: 01,02,03,04.",
    )
    parser.add_argument(
        "--counselor-ids",
        default="",
        help="Optional comma-separated login usernames. When set, overrides --display-names.",
    )
    parser.add_argument("--out", default=str(DEFAULT_OUT_PATH), help="Output JSON path.")
    parser.add_argument(
        "--include-drafts",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include all generated draft candidates. Enabled by default.",
    )
    parser.add_argument(
        "--pretty",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Pretty-print JSON. Enabled by default.",
    )
    return parser.parse_args()


def parse_json(value: Any, fallback: Any) -> Any:
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
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        ).fetchone()
        is not None
    )


def normalize_row(row: sqlite3.Row, json_columns: set[str]) -> dict[str, Any]:
    result = dict(row)
    for column in json_columns:
        if column in result:
            fallback: Any = [] if column in LIST_JSON_COLUMNS else {}
            result[column] = parse_json(result[column], fallback)
    return result


def placeholders(values: list[str]) -> str:
    return ",".join("?" for _ in values)


def load_records(
    conn: sqlite3.Connection,
    counselor_ids: list[str],
    include_drafts: bool,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        f"""
        SELECT *
        FROM consultation_records
        WHERE counselor_id IN ({placeholders(counselor_ids)})
        ORDER BY counselor_id, created_at, id
        """,
        counselor_ids,
    ).fetchall()
    records = [normalize_row(row, RECORD_JSON_COLUMNS) for row in rows]
    if not include_drafts:
        for record in records:
            record.pop("draft_candidates_json", None)
    return records


def load_events(conn: sqlite3.Connection, counselor_ids: list[str]) -> list[dict[str, Any]]:
    if not has_table(conn, "research_events"):
        return []
    rows = conn.execute(
        f"""
        SELECT *
        FROM research_events
        WHERE counselor_id IN ({placeholders(counselor_ids)})
        ORDER BY counselor_id, created_at, id
        """,
        counselor_ids,
    ).fetchall()
    return [normalize_row(row, EVENT_JSON_COLUMNS) for row in rows]


def resolve_accounts(
    conn: sqlite3.Connection,
    display_names: list[str],
    counselor_ids: list[str],
) -> tuple[list[str], dict[str, dict[str, Any]]]:
    if not has_table(conn, "accounts"):
        raise SystemExit("Table accounts was not found; display names cannot be resolved.")

    if counselor_ids:
        rows = conn.execute(
            f"""
            SELECT id, username, display_name, role, created_at
            FROM accounts
            WHERE username IN ({placeholders(counselor_ids)})
            """,
            counselor_ids,
        ).fetchall()
        accounts = {str(row["username"]): dict(row) for row in rows}
        missing = [value for value in counselor_ids if value not in accounts]
        if missing:
            raise SystemExit(f"Counselor usernames not found: {', '.join(missing)}")
        return counselor_ids, accounts

    rows = conn.execute(
        f"""
        SELECT id, username, display_name, role, created_at
        FROM accounts
        WHERE display_name IN ({placeholders(display_names)})
        """,
        display_names,
    ).fetchall()
    by_display_name: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        account = dict(row)
        by_display_name.setdefault(str(account["display_name"]), []).append(account)

    missing = [value for value in display_names if value not in by_display_name]
    if missing:
        raise SystemExit(f"Counselor display names not found: {', '.join(missing)}")
    duplicates = [value for value in display_names if len(by_display_name[value]) > 1]
    if duplicates:
        raise SystemExit(
            "Duplicate counselor display names are ambiguous: " + ", ".join(duplicates)
        )

    ordered_accounts = [by_display_name[value][0] for value in display_names]
    resolved_ids = [str(account["username"]) for account in ordered_accounts]
    return resolved_ids, {
        str(account["username"]): account for account in ordered_accounts
    }


def planner_field_changes(before: Any, after: Any, prefix: str = "") -> list[dict[str, Any]]:
    if isinstance(before, dict) and isinstance(after, dict):
        changes: list[dict[str, Any]] = []
        for key in sorted(set(before) | set(after)):
            path = f"{prefix}.{key}" if prefix else str(key)
            changes.extend(planner_field_changes(before.get(key), after.get(key), path))
        return changes
    if before == after:
        return []
    return [{"field": prefix, "before": before, "after": after}]


def event_task_key(event: dict[str, Any]) -> tuple[str, Any]:
    if event.get("workspace_task_id") is not None:
        return ("workspace_task", event["workspace_task_id"])
    if event.get("batch_item_id") is not None:
        return ("batch_item", event["batch_item_id"])
    return ("record", event.get("record_id") or event.get("id"))


def clean_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest_submitted: dict[tuple[str, Any], int] = {}
    for event in events:
        if event.get("event_type") == "record_submitted":
            latest_submitted[event_task_key(event)] = int(event["id"])

    cleaned: list[dict[str, Any]] = []
    for event in events:
        event_type = str(event.get("event_type") or "")
        before_text = str(event.get("before_text") or "")
        after_text = str(event.get("after_text") or "")
        metadata = event.get("metadata_json") or {}

        if event_type == "manual_edit" and before_text == after_text:
            continue
        if (
            event_type == "record_submitted"
            and latest_submitted.get(event_task_key(event)) != int(event["id"])
        ):
            continue

        base = {
            "event_id": event.get("id"),
            "created_at": event.get("created_at"),
            "event_type": event_type,
            "workspace_task_id": event.get("workspace_task_id"),
            "batch_session_id": event.get("batch_session_id"),
            "batch_item_id": event.get("batch_item_id"),
            "record_id": event.get("record_id"),
        }
        if event_type == "planner_regenerate":
            base["planner_changes"] = planner_field_changes(
                metadata.get("planner_before", {}),
                metadata.get("planner_after", {}),
            )
            base["persona_name"] = metadata.get("persona_name", "")
        elif event_type in {"manual_edit", "annotation_patch"}:
            base.update(
                {
                    "before_text": before_text,
                    "after_text": after_text,
                    "diff": event.get("diff_json") or [],
                }
            )
            if event_type == "annotation_patch":
                base["annotations"] = event.get("annotations_json") or []
                base["version_index"] = metadata.get("version_index")
        elif event_type in {"annotation_added", "annotation_removed"}:
            base["annotations"] = event.get("annotations_json") or []
        elif event_type == "version_rollback":
            base["target_version_index"] = metadata.get("target_version_index")
        elif event_type == "record_submitted":
            base["finalization_mode"] = metadata.get("finalization_mode", "")
            base["regeneration_count"] = metadata.get("regeneration_count", 0)
            base["version_count"] = metadata.get("version_count", 0)
        else:
            base["metadata"] = metadata
        cleaned.append(base)
    return cleaned


def build_payload(
    counselor_ids: list[str],
    requested_display_names: list[str],
    accounts: dict[str, dict[str, Any]],
    records: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    counselors: list[dict[str, Any]] = []
    for counselor_id in counselor_ids:
        counselor_records = [row for row in records if row.get("counselor_id") == counselor_id]
        counselor_events = clean_events(
            [row for row in events if row.get("counselor_id") == counselor_id]
        )
        event_counts = Counter(str(row.get("event_type") or "") for row in counselor_events)
        account = accounts.get(counselor_id, {})
        counselors.append(
            {
                "counselor_id": counselor_id,
                "display_name": account.get("display_name", ""),
                "account_created_at": account.get("created_at"),
                "summary": {
                    "record_count": len(counselor_records),
                    "event_count": len(counselor_events),
                    "event_counts": dict(sorted(event_counts.items())),
                },
                "records": counselor_records,
                "research_events": counselor_events,
            }
        )

    return {
        "schema_version": "counselor_ai_analysis_v1",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "requested_display_names": requested_display_names,
        "counselor_ids": counselor_ids,
        "summary": {
            "counselor_count": len(counselors),
            "record_count": sum(item["summary"]["record_count"] for item in counselors),
            "event_count": sum(item["summary"]["event_count"] for item in counselors),
        },
        "analysis_notes": [
            "同一工单只保留最后一次 record_submitted 事件。",
            "过滤 before_text 与 after_text 完全相同的 manual_edit。",
            "planner_regenerate 仅保留发生变化的 Planner 字段。",
            "consultation_records 保留原始来信、初始 AI 回复、最终回复、批注、版本和评分。",
        ],
        "counselors": counselors,
    }


def main() -> None:
    args = parse_args()
    requested_display_names = [
        value.strip()
        for value in str(args.display_names).split(",")
        if value.strip()
    ]
    requested_counselor_ids = [
        value.strip()
        for value in str(args.counselor_ids).split(",")
        if value.strip()
    ]
    if not requested_display_names and not requested_counselor_ids:
        raise SystemExit("No counselor display names or usernames were provided.")

    db_path = Path(args.db).expanduser().resolve()
    if not db_path.exists():
        raise SystemExit(f"Database does not exist: {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        if not has_table(conn, "consultation_records"):
            raise SystemExit("Table consultation_records was not found.")
        counselor_ids, accounts = resolve_accounts(
            conn,
            requested_display_names,
            requested_counselor_ids,
        )
        records = load_records(conn, counselor_ids, include_drafts=args.include_drafts)
        events = load_events(conn, counselor_ids)
    finally:
        conn.close()

    payload = build_payload(
        counselor_ids,
        requested_display_names if not requested_counselor_ids else [],
        accounts,
        records,
        events,
    )
    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    separators = None if args.pretty else (",", ":")
    out_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2 if args.pretty else None,
            separators=separators,
        )
        + "\n",
        encoding="utf-8",
    )

    if requested_counselor_ids:
        print(f"Exported counselor usernames: {', '.join(counselor_ids)}")
    else:
        print(f"Requested display names: {', '.join(requested_display_names)}")
        print(f"Resolved counselor usernames: {', '.join(counselor_ids)}")
    print(f"Records: {payload['summary']['record_count']}")
    print(f"Cleaned research events: {payload['summary']['event_count']}")
    print(f"Output: {out_path}")
    print(f"Source database: {db_path}")


if __name__ == "__main__":
    main()
