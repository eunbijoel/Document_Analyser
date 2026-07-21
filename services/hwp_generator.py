"""연구노트 HWPX 생성 — make_minimal_hwpx 재사용."""

from __future__ import annotations

from pathlib import Path

from services._hwp_path import ensure_hwp_paths
from services.session_bridge import ResearchNoteFields

_TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "templates" / "research_note_template.hwpx"


def _fields_to_paragraphs(fields: ResearchNoteFields) -> list[str]:
    lines: list[str] = [
        fields.title or "연구노트",
        "",
        "1. 기본 정보",
        f"- 작성일: {fields.written_date or '확인 필요'}",
        f"- 작성자: {fields.author or '확인 필요'}",
        f"- 연구과제명: {fields.project_name or '확인 필요'}",
        f"- 참고 파일: {fields.reference_files or '확인 필요'}",
        "",
        "2. 연구 목적",
        fields.purpose or fields.body[:400] if fields.body else "확인 필요",
        "",
        "3. 주요 작업 내용",
        fields.main_work or "확인 필요",
        "",
        "4. 분석 및 구현 결과",
        fields.results or "확인 필요",
        "",
        "5. 문제점 및 확인 사항",
        fields.issues or "확인 필요",
        "",
        "6. 향후 계획",
        fields.future_plan or "확인 필요",
    ]
    if fields.materials:
        lines.insert(8, f"- 사용 자료: {fields.materials}")
    if fields.keywords:
        lines.insert(8, f"- 키워드: {', '.join(fields.keywords)}")
    # 본문 전체가 있고 섹션이 비어 있으면 마지막에 부록
    if fields.body and not any([fields.main_work, fields.results]):
        lines.extend(["", "【통합 요약】", fields.body[:2500]])
    return [ln for ln in lines if ln is not None]


def build_research_note_hwpx(fields: ResearchNoteFields) -> bytes:
    """연구노트 양식 HWPX bytes."""
    ensure_hwp_paths()
    paragraphs = _fields_to_paragraphs(fields)

    if _TEMPLATE_PATH.is_file():
        raw = _TEMPLATE_PATH.read_bytes()
        if raw[:2] == b"PK":
            from hwp_core.hwpx_editor import HWPXEditor

            editor = HWPXEditor(raw)
            paras = editor.get_paragraphs()
            body = "\n".join(paragraphs)
            if paras:
                editor.propose_insert_after_anchor(paras[-1]["text"][:40] or "연구노트", body)
                for ch in list(editor.pending_changes):
                    editor.accept_change(ch.id)
            return editor.save()

    from hwp_core.doc_agent.fixtures import make_minimal_hwpx

    return make_minimal_hwpx(paragraphs=paragraphs)


def build_research_note_filename(title: str) -> str:
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in (title or "연구노트"))
    safe = safe[:60] or "research_note"
    return f"{safe}.hwpx"
