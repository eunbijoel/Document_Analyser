"""탭 1 ↔ 탭 2 session_state 브릿지."""

from __future__ import annotations

import os
import os
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any


# --- session keys (명세) ---
ANALYSIS_SUMMARY = "analysis_summary"
RESEARCH_NOTE_CONTENT = "research_note_content"
UPLOADED_FILE_NAMES = "uploaded_file_names"
RESEARCH_NOTE_TITLE = "research_note_title"
ANALYSIS_KEYWORDS = "analysis_keywords"
ANALYSIS_COMPLETED = "analysis_completed"
ANALYSIS_DATE = "analysis_date"
RESEARCH_NOTE_FIELDS = "research_note_fields"


@dataclass
class ResearchNoteFields:
    title: str = "연구노트"
    written_date: str = ""
    author: str = ""
    project_name: str = ""
    purpose: str = ""
    materials: str = ""
    main_work: str = ""
    results: str = ""
    issues: str = ""
    future_plan: str = ""
    reference_files: str = ""
    body: str = ""
    keywords: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "written_date": self.written_date,
            "author": self.author,
            "project_name": self.project_name,
            "purpose": self.purpose,
            "materials": self.materials,
            "main_work": self.main_work,
            "results": self.results,
            "issues": self.issues,
            "future_plan": self.future_plan,
            "reference_files": self.reference_files,
            "body": self.body,
            "keywords": self.keywords,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ResearchNoteFields":
        kw = d.get("keywords") or []
        if isinstance(kw, str):
            kw = [k.strip() for k in kw.split(",") if k.strip()]
        return cls(
            title=d.get("title") or "연구노트",
            written_date=d.get("written_date") or "",
            author=d.get("author") or "",
            project_name=d.get("project_name") or "",
            purpose=d.get("purpose") or "",
            materials=d.get("materials") or "",
            main_work=d.get("main_work") or "",
            results=d.get("results") or "",
            issues=d.get("issues") or "",
            future_plan=d.get("future_plan") or "",
            reference_files=d.get("reference_files") or "",
            body=d.get("body") or "",
            keywords=list(kw),
        )


_SECTION_PATTERNS: list[tuple[str, str]] = [
    (r"(?:연구\s*목적|작업\s*목적|목적)\s*[:：]?\s*", "purpose"),
    (r"(?:사용\s*자료|참고\s*파일|자료)\s*[:：]?\s*", "materials"),
    (r"(?:주요\s*작업|작업\s*내용|주요\s*작업\s*내용)\s*[:：]?\s*", "main_work"),
    (r"(?:분석|구현)\s*결과|결과\s*[:：]?\s*", "results"),
    (r"(?:문제점|확인\s*사항|이슈)\s*[:：]?\s*", "issues"),
    (r"(?:향후|다음)\s*(?:계획|작업)\s*[:：]?\s*", "future_plan"),
]


def parse_summary_into_fields(
    summary: str,
    *,
    filenames: list[str] | None = None,
    title_hint: str = "",
    keywords: list[str] | None = None,
) -> ResearchNoteFields:
    """요약문에서 섹션 키워드로 필드 분리 (없으면 body 전체)."""
    text = (summary or "").strip()
    fields = ResearchNoteFields(
        title=title_hint or "연구노트",
        written_date=date.today().isoformat(),
        reference_files=", ".join(filenames or []),
        keywords=list(keywords or []),
        body=text,
    )
    if not text:
        return fields

    # 번호 목록 형태 (1. 기본 정보 등) 간단 파싱
    blocks = re.split(r"\n(?=\d+\.\s)", text)
    for block in blocks:
        b = block.strip()
        low = b.lower()
        if re.match(r"1\.\s*기본", b):
            continue
        for pat, attr in _SECTION_PATTERNS:
            m = re.search(pat, b, re.I)
            if m:
                content = b[m.end():].strip()
                content = re.sub(r"^\d+\.\s*", "", content).strip()
                setattr(fields, attr, content[:2000])
                break

    # 키워드가 비었으면 파일명에서
    if not fields.keywords and filenames:
        fields.keywords = [Path(f).stem for f in filenames[:5]]

    return fields


def save_analysis_to_writer(
    session_state: Any,
    *,
    summary: str,
    filenames: list[str],
    title: str = "",
    keywords: list[str] | None = None,
) -> None:
    """탭 1 → 탭 2 전달."""
    kw = keywords or []
    fields = parse_summary_into_fields(
        summary,
        filenames=filenames,
        title_hint=title or "연구노트",
        keywords=kw,
    )
    session_state[ANALYSIS_SUMMARY] = summary
    session_state[RESEARCH_NOTE_CONTENT] = summary
    session_state[UPLOADED_FILE_NAMES] = list(filenames)
    session_state[RESEARCH_NOTE_TITLE] = fields.title
    session_state[ANALYSIS_KEYWORDS] = kw
    session_state[ANALYSIS_COMPLETED] = True
    session_state[ANALYSIS_DATE] = date.today().isoformat()
    session_state[RESEARCH_NOTE_FIELDS] = fields.to_dict()


def has_analysis_data(session_state: Any) -> bool:
    return bool(session_state.get(ANALYSIS_COMPLETED) and (
        session_state.get(ANALYSIS_SUMMARY) or session_state.get(RESEARCH_NOTE_CONTENT)
    ))
