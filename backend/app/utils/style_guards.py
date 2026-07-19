import re


GENERIC_EMPATHY_PATTERN = re.compile(
    r"(?:任谁|换谁|任何人|谁(?:遇到|碰到))"
    r"[^，。！？\n]{0,24}都(?:会|很|难免|无法|受不了|觉得|感到)"
)


def find_generic_empathy_phrase(text: str) -> str | None:
    match = GENERIC_EMPATHY_PATTERN.search(text)
    return match.group(0) if match else None
