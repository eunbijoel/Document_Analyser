"""연구노트용 통합 요약 생성 — LLM + 규칙 fallback."""

from __future__ import annotations

import re
from typing import Any

from services._hwp_path import ensure_hwp_paths
from services.document_parser import ParseResult


RESEARCH_NOTE_SECTIONS = """
다음 항목을 포함하되, 원문에 없는 내용은 만들지 마세요. 정보가 없으면 해당 줄을 생략하거나 「확인 필요」라고 쓰세요.

1. 연구 또는 작업 목적
2. 사용한 자료 및 파일
3. 주요 작업 내용
4. 분석 또는 구현 결과
5. 확인된 문제점
6. 향후 작업 계획

전체 20줄 내외, 마크다운(###, **) 없이 일반 문장과 · 불릿만 사용.
"""


def _build_source_corpus(results: list[ParseResult], max_chars: int = 24000) -> str:
    parts: list[str] = []
    total = 0
    for r in results:
        if not r.ok and not r.full_text.strip():
            continue
        header = f"## {r.filename} ({r.file_type})"
        body = (r.full_text or "")[: max_chars - total - len(header) - 20]
        if not body.strip():
            continue
        chunk = f"{header}\n{body}"
        parts.append(chunk)
        total += len(chunk)
        if total >= max_chars:
            break
    return "\n\n".join(parts)


def _fallback_summary(results: list[ParseResult], filenames: list[str]) -> str:
    """Ollama 없을 때 규칙 기반 짧은 요약."""
    lines = [
        "연구노트 요약 (자동 추출)",
        "",
        "1. 사용한 자료 및 파일",
        "· " + ", ".join(filenames) if filenames else "· 확인 필요",
        "",
        "2. 주요 작업 내용",
    ]
    for r in results[:5]:
        if r.paragraphs:
            preview = r.paragraphs[0][:120]
            lines.append(f"· [{r.filename}] {preview}")
        elif r.full_text:
            lines.append(f"· [{r.filename}] {r.full_text[:120].strip()}…")
    lines.extend([
        "",
        "3. 분석 또는 구현 결과",
        "· 문서 추출 완료 — 상세는 Q&A 탭에서 확인",
        "",
        "4. 확인된 문제점",
        "· " + ("; ".join(r.errors[:3]) if any(r.errors for r in results) else "확인 필요"),
        "",
        "5. 향후 작업 계획",
        "· 확인 필요",
    ])
    return "\n".join(lines)[:3500]


def generate_research_note_summary(
    results: list[ParseResult],
    *,
    model: str = "gemma4",
    ollama_url: str = "http://localhost:11434",
    use_llm: bool = True,
) -> tuple[str, str]:
    """
    Returns (summary_text, error_message).
    error_message empty on success.
    """
    ensure_hwp_paths()
    filenames = [r.filename for r in results]
    corpus = _build_source_corpus(results)
    if not corpus.strip():
        return "", "추출된 문서 내용이 없습니다. 파일 형식과 파싱 오류를 확인하세요."

    if not use_llm:
        return _fallback_summary(results, filenames), ""

    from hwp_core.llm_client import generate

    prompt = f"""다음 자료들을 읽고 연구노트에 넣을 통합 요약을 작성하세요.

{RESEARCH_NOTE_SECTIONS}

[자료]
{corpus[:18000]}
"""
    result = generate(
        prompt,
        model,
        ollama_url,
        temperature=0.25,
        num_predict=1200,
        num_ctx=16384,
        timeout=180,
    )
    if result.get("error"):
        fb = _fallback_summary(results, filenames)
        return fb, f"LLM: {result['error']} (규칙 요약으로 대체)"

    text = (result.get("text") or "").strip()
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    if not text:
        return _fallback_summary(results, filenames), "LLM이 빈 응답 — 규칙 요약으로 대체"
    return text, ""


def extract_keywords(results: list[ParseResult], summary: str, limit: int = 8) -> list[str]:
    """파일명 + 요약에서 간단 키워드."""
    kws: list[str] = []
    for r in results:
        stem = re.sub(r"\.[^.]+$", "", r.filename)
        if stem and stem not in kws:
            kws.append(stem)
    for m in re.finditer(r"[가-힣]{2,8}", summary[:800]):
        w = m.group(0)
        if w not in kws and len(kws) < limit:
            kws.append(w)
    return kws[:limit]


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
