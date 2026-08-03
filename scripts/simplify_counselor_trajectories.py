#!/usr/bin/env python3
"""Convert the full counselor export into a compact edit-trajectory dataset.

The compact output keeps one copy of the user letter, initial AI response, and
final response per case. Events retain only changed fragments and annotations.

Examples:
  python scripts/simplify_counselor_trajectories.py \
    --input data/counselors_01_04_for_ai.json \
    --out data/counselors_01_04_trajectories.json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "counselors_01_04_for_ai.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "counselors_01_04_trajectories.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a compact counselor edit-trajectory JSON.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Full AI-analysis JSON export.")
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT), help="Compact output JSON path.")
    parser.add_argument(
        "--split-dir",
        default="",
        help="Optional directory for one compact JSON file per counselor.",
    )
    parser.add_argument(
        "--include-incomplete",
        action="store_true",
        help="Include trajectories that cannot be linked to a saved consultation record.",
    )
    return parser.parse_args()


def task_key(item: dict[str, Any]) -> tuple[str, Any] | None:
    if item.get("workspace_task_id") is not None:
        return ("workspace_task", item["workspace_task_id"])
    if item.get("batch_item_id") is not None:
        return ("batch_item", item["batch_item_id"])
    if item.get("record_id") is not None:
        return ("record", item["record_id"])
    return None


def compact_changes(changes: Any) -> list[dict[str, str]]:
    if not isinstance(changes, list):
        return []
    compact: list[dict[str, str]] = []
    for change in changes:
        if not isinstance(change, dict):
            continue
        before = str(change.get("before") or "")
        after = str(change.get("after") or "")
        if before == after:
            continue
        compact.append(
            {
                "operation": str(change.get("operation") or "replace"),
                "before": before,
                "after": after,
            }
        )
    return compact


def compact_annotations(annotations: Any) -> list[dict[str, Any]]:
    if not isinstance(annotations, list):
        return []
    result: list[dict[str, Any]] = []
    for annotation in annotations:
        if not isinstance(annotation, dict):
            continue
        result.append(
            {
                "annotation_id": annotation.get("id"),
                "quote": str(annotation.get("quote") or ""),
                "note": str(annotation.get("note") or ""),
            }
        )
    return result


def compact_event(event: dict[str, Any]) -> dict[str, Any] | None:
    event_type = str(event.get("event_type") or "")
    result: dict[str, Any] = {
        "time": event.get("created_at"),
        "action": event_type,
    }

    if event_type == "manual_edit":
        changes = compact_changes(event.get("diff"))
        if not changes:
            return None
        result["changes"] = changes
    elif event_type == "planner_regenerate":
        result["planner_changes"] = event.get("planner_changes") or []
    elif event_type in {"annotation_added", "annotation_removed"}:
        result["annotations"] = compact_annotations(event.get("annotations"))
    elif event_type == "annotation_patch":
        result["annotations"] = compact_annotations(event.get("annotations"))
        result["changes"] = compact_changes(event.get("diff"))
        if event.get("version_index") is not None:
            result["version_index"] = event.get("version_index")
    elif event_type == "version_rollback":
        result["target_version_index"] = event.get("target_version_index")
    elif event_type == "record_submitted":
        result["finalization_mode"] = event.get("finalization_mode")
        result["regeneration_count"] = event.get("regeneration_count", 0)
        result["version_count"] = event.get("version_count", 0)
    else:
        return None
    return result


def record_case(
    record: dict[str, Any],
    display_name: str,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    trajectory = [
        compact
        for event in events
        if (compact := compact_event(event)) is not None
    ]
    action_counts = Counter(item["action"] for item in trajectory)
    return {
        "case_id": record.get("id"),
        "counselor_display_name": display_name,
        "workspace_task_id": record.get("workspace_task_id"),
        "batch_item_id": record.get("batch_item_id"),
        "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
        "user_letter": str(record.get("user_input") or ""),
        "initial_ai_response": str(record.get("ai_selected_raw_response") or ""),
        "final_counselor_response": str(record.get("expert_polished_response") or ""),
        "overall_annotation": str(record.get("expert_annotation") or ""),
        "summary": {
            "action_count": len(trajectory),
            "action_counts": dict(sorted(action_counts.items())),
            "initial_length": len(str(record.get("ai_selected_raw_response") or "")),
            "final_length": len(str(record.get("expert_polished_response") or "")),
        },
        "trajectory": trajectory,
    }


def build_compact_dataset(source: dict[str, Any], include_incomplete: bool) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    incomplete: list[dict[str, Any]] = []

    for counselor in source.get("counselors", []):
        if not isinstance(counselor, dict):
            continue
        display_name = str(counselor.get("display_name") or "")
        records = [item for item in counselor.get("records", []) if isinstance(item, dict)]
        events = [item for item in counselor.get("research_events", []) if isinstance(item, dict)]

        events_by_key: dict[tuple[str, Any], list[dict[str, Any]]] = {}
        for event in events:
            key = task_key(event)
            if key is not None:
                events_by_key.setdefault(key, []).append(event)

        used_event_ids: set[Any] = set()
        for record in records:
            key = task_key(record)
            linked_events = events_by_key.get(key, []) if key is not None else []
            used_event_ids.update(event.get("event_id") for event in linked_events)
            cases.append(record_case(record, display_name, linked_events))

        if include_incomplete:
            orphan_events = [
                compact
                for event in events
                if event.get("event_id") not in used_event_ids
                if (compact := compact_event(event)) is not None
            ]
            if orphan_events:
                incomplete.append(
                    {
                        "counselor_display_name": display_name,
                        "trajectory": orphan_events,
                    }
                )

    cases.sort(key=lambda item: (item["counselor_display_name"], str(item["created_at"]), item["case_id"]))
    counselor_counts = Counter(case["counselor_display_name"] for case in cases)
    return {
        "schema_version": "counselor_edit_trajectories_v1",
        "purpose": "分析咨询师如何修改 AI 回信；已排除 RAG、候选草稿、标签、风险评估和重复全文。",
        "summary": {
            "case_count": len(cases),
            "counselor_case_counts": dict(sorted(counselor_counts.items())),
            "incomplete_trajectory_count": len(incomplete),
        },
        "field_guide": {
            "manual_edit": "咨询师直接编辑回复；changes 只包含实际增删改片段。",
            "planner_regenerate": "咨询师修改 Planner 后重生成；只保留 Planner 改动字段。",
            "annotation_added": "咨询师添加局部批注。",
            "annotation_patch": "根据局部批注重生成；保留批注和实际变化片段。",
            "version_rollback": "咨询师切换到指定历史版本。",
            "record_submitted": "咨询师保存最终版本。",
        },
        "cases": cases,
        **({"incomplete_trajectories": incomplete} if include_incomplete else {}),
    }


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.out).expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"Input JSON does not exist: {input_path}")

    try:
        source = json.loads(input_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Could not read input JSON: {exc}") from exc
    if not isinstance(source, dict) or not isinstance(source.get("counselors"), list):
        raise SystemExit("Input JSON is not a counselors_for_ai export.")

    compact = build_compact_dataset(source, include_incomplete=args.include_incomplete)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(compact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.split_dir:
        split_dir = Path(args.split_dir).expanduser().resolve()
        split_dir.mkdir(parents=True, exist_ok=True)
        display_names = sorted({case["counselor_display_name"] for case in compact["cases"]})
        for display_name in display_names:
            counselor_cases = [
                case for case in compact["cases"]
                if case["counselor_display_name"] == display_name
            ]
            safe_name = "".join(
                character if character.isalnum() or character in {"-", "_"} else "_"
                for character in display_name
            ) or "unknown"
            counselor_payload = {
                "schema_version": compact["schema_version"],
                "purpose": compact["purpose"],
                "counselor_display_name": display_name,
                "case_count": len(counselor_cases),
                "field_guide": compact["field_guide"],
                "cases": counselor_cases,
            }
            counselor_path = split_dir / f"counselor_{safe_name}_trajectories.json"
            counselor_path.write_text(
                json.dumps(counselor_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        print(f"Split counselor files: {split_dir}")
    print(f"Cases: {compact['summary']['case_count']}")
    print(f"Output: {output_path}")
    print(f"Size: {output_path.stat().st_size / 1024:.1f} KiB")


if __name__ == "__main__":
    main()
