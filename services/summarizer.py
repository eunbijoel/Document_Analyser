"""연구노트용 통합 요약 생성 — LLM + 규칙 fallback."""

from __future__ import annotations

import re


RESEARCH_NOTE_SECTIONS = """
아래 형식을 그대로 지켜 작성하세요. 각 제목은 반드시 줄의 시작에 쓰고, 마크다운(#, **)은 쓰지 마세요.
원문에 없는 내용은 만들지 말고, 없으면 「확인 필요」라고 쓰세요.

주제 제안:

연구 또는 작업 목적

사용한 자료 및 파일

내용:

연구 결과:

확인된 문제점

향후 작업 계획
"""

# 줄 머리 제목만 매칭 — '문서 내용' 같은 문장 중간 단어와 혼동 방지
_SECTION_SPECS: list[tuple[str, str]] = [
    ("topic", r"(?m)^\s*주제\s*제안\s*:?\s*"),
    ("purpose", r"(?m)^\s*연구\s*또는\s*작업\s*목적\s*:?\s*"),
    ("materials", r"(?m)^\s*사용한\s*자료(?:\s*및\s*파일)?\s*:?\s*"),
    ("content", r"(?m)^\s*(?:주요\s*)?내용\s*:?\s*"),
    ("results", r"(?m)^\s*연구\s*결과\s*:?\s*"),
    ("issues", r"(?m)^\s*확인된\s*문제점\s*:?\s*"),
    ("plan", r"(?m)^\s*향후\s*작업\s*계획\s*:?\s*"),
]


def parse_research_note_fields(text: str) -> dict[str, str]:
    """통합 요약에서 주제/내용/연구결과만 추출 (다른 섹션은 경계로만 사용)."""
    raw = (text or "").replace("\r\n", "\n").strip()
    out = {"topic": "", "content": "", "results": ""}
    if not raw:
        return out

    hits: list[tuple[int, str, int]] = []
    for key, pat in _SECTION_SPECS:
        m = re.search(pat, raw)
        if m:
            hits.append((m.start(), key, m.end()))
    if not hits:
        out["content"] = raw
        return out

    hits.sort(key=lambda x: x[0])
    for i, (_start, key, end) in enumerate(hits):
        if key not in out:
            continue
        stop = hits[i + 1][0] if i + 1 < len(hits) else len(raw)
        body = raw[end:stop].strip()
        body = re.sub(r"^\s*[-·*]\s*", "", body, count=1)
        out[key] = body.strip()
    return out


def suggest_title(filenames: list[str], summary: str) -> str:
    if len(filenames) == 1:
        base = re.sub(r"\.[^.]+$", "", filenames[0])
        return f"연구노트 — {base}"
    if filenames:
        return f"연구노트 — {filenames[0]} 외 {len(filenames) - 1}건"
    m = re.search(r"(?:목적|주제)[:：]?\s*(.{4,40})", summary)
    if m:
        return f"연구노트 — {m.group(1).strip()}"
    return "연구노트"
