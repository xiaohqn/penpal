#!/usr/bin/env python3
"""Export consultation expert records from the app SQLite database.

Examples:
  python scripts/export_expert_records.py
  python scripts/export_expert_records.py --db data/app.db --out exports/expert_records.json
  python scripts/export_expert_records.py --approved-only --seed-format --out exports/expert_seed.json
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "app.db"
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
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export consultation_records from a SQLite app.db.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Path to app.db.")
    parser.add_argument(
        "--out",
        default="expert_records_export.json",
        help="Output JSON file path. Parent directories are created automatically.",
    )
    parser.add_argument(
        "--approved-only",
        action="store_true",
        help="Only export records where rag_ready = 'approved'.",
    )
    parser.add_argument(
        "--seed-format",
        action="store_true",
        help="Export as RAG seed records with index/send_content/reply_content.",
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


def ensure_consultation_records_table(conn: sqlite3.Connection) -> None:
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'consultation_records'"
    ).fetchone()
    if not exists:
        raise SystemExit("Table consultation_records was not found in this database.")


def load_records(db_path: Path, approved_only: bool) -> list[dict[str, Any]]:
    if not db_path.exists():
        raise SystemExit(f"Database does not exist: {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        ensure_consultation_records_table(conn)
        query = "SELECT * FROM consultation_records"
        params: tuple[Any, ...] = ()
        if approved_only:
            query += " WHERE rag_ready = ?"
            params = ("approved",)
        query += " ORDER BY id"
        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()

    records: list[dict[str, Any]] = []
    for row in rows:
        record = dict(row)
        for column in JSON_COLUMNS:
            if column in record:
                fallback = [] if column in {"draft_candidates_json", "source_annotations_json", "response_versions_json"} else {}
                record[column] = parse_json_value(record[column], fallback)
        records.append(record)
    return records


def to_seed_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seed_records: list[dict[str, Any]] = []
    for index, record in enumerate(records, start=1):
        send_content = str(record.get("user_input") or "").strip()
        reply_content = str(record.get("expert_polished_response") or "").strip()
        if not send_content or not reply_content:
            continue
        seed_records.append(
            {
                "index": index,
                "send_content": send_content,
                "reply_content": reply_content,
                "source": "expert_record",
                "source_record_id": record.get("id"),
                "selected_persona_name": record.get("selected_persona_name") or "",
                "expert_annotation": record.get("expert_annotation") or "",
                "rag_ready": record.get("rag_ready") or "",
                "sample_reason": record.get("sample_reason") or "",
                "sample_tags": record.get("sample_tags_json") or {},
                "planner_labels": record.get("planner_labels_json") or {},
                "risk_assessment": record.get("risk_assessment_json") or {},
                "created_at": record.get("created_at"),
                "updated_at": record.get("updated_at"),
                "counselor_id": record.get("counselor_id") or "default",
            }
        )
    return seed_records


def write_json(path: Path, payload: Any, pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if pretty:
        text = json.dumps(payload, ensure_ascii=False, indent=2)
    else:
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    path.write_text(text + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    db_path = Path(args.db).expanduser().resolve()
    out_path = Path(args.out).expanduser()
    records = load_records(db_path=db_path, approved_only=args.approved_only)
    payload: Any = to_seed_records(records) if args.seed_format else records
    write_json(out_path, payload, pretty=args.pretty)
    print(f"Exported {len(payload)} records to {out_path}")
    print(f"Source database: {db_path}")


if __name__ == "__main__":
    main()
