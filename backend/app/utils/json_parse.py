import json
import re


def safe_json_parse(text: str | None) -> dict | None:
    if not text:
        return None

    raw = text.strip()
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    match = re.search(r"\{[\s\S]*\}", raw, re.DOTALL)
    if match:
        try:
            obj = json.loads(match.group(0))
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

    cleaned = raw.replace("```json", "").replace("```", "").strip()
    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict):
            return obj
    except Exception:
        return None
    return None


def parse_response_only(raw_text: str) -> tuple[str, str]:
    raw = (raw_text or "").strip()
    obj = safe_json_parse(raw)
    if isinstance(obj, dict):
        response = (obj.get("response") or obj.get("output") or "").strip()
        if response:
            return response, raw

    match = re.search(r'"response"\s*:\s*"([\s\S]*?)"\s*\}', raw)
    if match:
        return match.group(1).strip(), raw

    return raw, raw
