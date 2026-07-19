#!/usr/bin/env python3
"""Export append-only counselor research events from SQLite to JSON and/or XLSX.

Examples:
  python scripts/export_research_events.py
  python scripts/export_research_events.py --xlsx exports/research_events.xlsx
  python scripts/export_research_events.py --counselor-id counselor_a
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = PROJECT_ROOT / "data" / "app.db"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export research_events from mindful-copilot app.db")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--out", default="exports/research_events.json", help="JSON output; use an empty string to skip")
    parser.add_argument("--xlsx", default="exports/research_events.xlsx", help="Excel output; use an empty string to skip")
    parser.add_argument("--counselor-id", default="", help="Optionally export one counselor only")
    return parser.parse_args()


def load_events(db_path: Path, counselor_id: str) -> list[dict[str, Any]]:
    if not db_path.exists():
        raise SystemExit(f"Database does not exist: {db_path}")
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='research_events'"
        ).fetchone()
        if not exists:
            raise SystemExit("research_events table does not exist; restart the backend once before exporting")
        query = "SELECT * FROM research_events"
        params: tuple[str, ...] = ()
        if counselor_id:
            query += " WHERE counselor_id = ?"
            params = (counselor_id,)
        query += " ORDER BY created_at, id"
        rows = connection.execute(query, params).fetchall()
    finally:
        connection.close()

    events = [dict(row) for row in rows]
    for event in events:
        for key in ("diff_json", "annotations_json", "metadata_json"):
            try:
                event[key] = json.loads(event.get(key) or ("[]" if key != "metadata_json" else "{}"))
            except json.JSONDecodeError:
                pass
    return events


def write_json(path: Path, events: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(events, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_xlsx(path: Path, events: list[dict[str, Any]]) -> None:
    try:
        from openpyxl import Workbook
    except ImportError as exc:
        raise SystemExit("openpyxl is required for XLSX export") from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "research_events"
    headers = ["id", "created_at", "counselor_id", "event_type", "workspace_task_id", "batch_session_id", "batch_item_id", "record_id", "before_text", "after_text", "diff_json", "annotations_json", "metadata_json"]
    sheet.append(headers)
    for event in events:
        sheet.append([
            json.dumps(event.get(key), ensure_ascii=False) if key.endswith("_json") else event.get(key, "")
            for key in headers
        ])
    workbook.save(path)


def main() -> None:
    args = parse_args()
    events = load_events(Path(args.db).expanduser().resolve(), args.counselor_id.strip())
    if args.out:
        write_json(Path(args.out).expanduser(), events)
    if args.xlsx:
        write_xlsx(Path(args.xlsx).expanduser(), events)
    print(f"Exported {len(events)} research events")


if __name__ == "__main__":
    main()
