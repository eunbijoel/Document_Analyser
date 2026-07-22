"""요약/연구노트 → 한글에서 열리는 HWPX·DOCX 생성."""

from __future__ import annotations

import io
from typing import Sequence


def _paragraph_lines(text: str) -> list[str]:
    lines = [ln.rstrip() for ln in (text or "").splitlines()]
    out: list[str] = []
    for ln in lines:
        if ln.strip() == "" and out and out[-1] == "":
            continue
        out.append(ln)
    if not any(x.strip() for x in out):
        return [" "]
    return out


def build_hwpx_from_text(text: str) -> bytes:
    """평문 → HWPX (왼쪽 요약 미리보기용)."""
    from hwpx import HwpxDocument

    doc = HwpxDocument.new()
    lines = _paragraph_lines(text)
    paras = list(getattr(doc, "paragraphs", None) or [])
    if paras:
        try:
            paras[0].text = lines[0]
            start = 1
        except Exception:
            start = 0
    else:
        start = 0
    for ln in lines[start:]:
        doc.add_paragraph(ln if ln.strip() else " ")
    raw = doc.to_bytes()
    if not raw or raw[:2] != b"PK":
        raise RuntimeError("HWPX 생성 실패")
    return raw


def build_docx_from_text(text: str) -> bytes:
    """평문 → DOCX."""
    from docx import Document

    d = Document()
    for ln in _paragraph_lines(text):
        d.add_paragraph(ln)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def _normalize_note_rows(rows: Sequence[tuple[str, str]]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for label, val in rows:
        out.append((str(label or ""), str(val or "")))
    if not out:
        out = [("내 용", " ")]
    return out


def _strip_md_noise(text: str) -> str:
    """한글 표 셀용: 마크다운 기호만 가볍게 제거 (내용은 유지)."""
    import re

    out_lines: list[str] = []
    for ln in (text or "").splitlines():
        s = ln.rstrip()
        s = re.sub(r"^#{1,6}\s*", "", s)
        s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
        s = re.sub(r"__(.+?)__", r"\1", s)
        s = re.sub(r"`([^`]+)`", r"\1", s)
        if re.fullmatch(r"-{3,}|_{3,}|\*{3,}", s.strip()):
            continue
        out_lines.append(s)
    return "\n".join(out_lines)


def build_research_note_hwpx(rows: Sequence[tuple[str, str]], *, title: str = "연구노트") -> bytes:
    """연구노트 2열 표 형식 HWPX (미리보기와 동일 구조)."""
    from hwpx import HwpxDocument

    # python-hwpx 기본 표 폭(14400)은 A4에서 너무 좁음 → authoring 기본(~45000) 사용
    _TABLE_WIDTH = 45_000

    note_rows = _normalize_note_rows(rows)
    doc = HwpxDocument.new()
    paras = list(getattr(doc, "paragraphs", None) or [])
    if paras:
        try:
            paras[0].text = title
        except Exception:
            doc.add_paragraph(title)
    else:
        doc.add_paragraph(title)

    table = doc.add_table(rows=len(note_rows), cols=2, width=_TABLE_WIDTH)
    try:
        # 라벨 ~22% / 값 ~78%
        table.set_column_widths([2200, 7800])
    except Exception:
        pass

    tall = {"내 용", "연구결과", "기타내용", "내용"}
    for i, (label, val) in enumerate(note_rows):
        clean = _strip_md_noise(val)
        table.set_cell_text(i, 0, label)
        table.set_cell_text(
            i, 1, clean if clean.strip() else " ", split_paragraphs=True
        )
        try:
            table.set_cell_shading(i, 0, "#F0F0F0")
        except Exception:
            pass
        # 긴 내용 행은 셀 높이 확보 (HWPUNIT)
        try:
            cell = table.cell(i, 1)
            lines = max(1, clean.count("\n") + 1)
            if label.strip() in tall or label.replace(" ", "") in tall:
                cell.set_size(height=max(3600, min(lines * 900, 40_000)))
            else:
                cell.set_size(height=3600)
            # 라벨 셀도 같은 높이
            table.cell(i, 0).set_size(height=cell.height)
        except Exception:
            pass

    raw = doc.to_bytes()
    if not raw or raw[:2] != b"PK":
        raise RuntimeError("연구노트 HWPX 생성 실패")
    return raw


def build_research_note_docx(rows: Sequence[tuple[str, str]], *, title: str = "연구노트") -> bytes:
    """연구노트 2열 표 형식 DOCX."""
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    from docx.shared import Cm, Pt, RGBColor

    note_rows = _normalize_note_rows(rows)
    d = Document()
    h = d.add_paragraph(title)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if h.runs:
        h.runs[0].bold = True
        h.runs[0].font.size = Pt(16)

    table = d.add_table(rows=len(note_rows), cols=2)
    table.style = "Table Grid"
    table.autofit = False
    table.columns[0].width = Cm(3.2)
    table.columns[1].width = Cm(13.0)

    tall_labels = {"내 용", "연구결과", "기타내용", "내용"}

    for i, (label, val) in enumerate(note_rows):
        c0, c1 = table.rows[i].cells
        c0.text = label
        c1.text = _strip_md_noise(val)
        # 라벨 셀 회색 배경
        try:
            shading = OxmlElement("w:shd")
            shading.set(qn("w:fill"), "F0F0F0")
            shading.set(qn("w:val"), "clear")
            c0._tc.get_or_add_tcPr().append(shading)
        except Exception:
            pass
        for p in c0.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in p.runs:
                run.bold = True
        # 내용 행 높이
        if label.strip() in tall_labels or label.replace(" ", "") in {"내용", "연구결과", "기타내용"}:
            try:
                from docx.shared import Twips
                table.rows[i].height = Twips(1800)
            except Exception:
                pass

    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def build_hwp_from_text(text: str) -> tuple[bytes | None, str]:
    try:
        return build_docx_from_text(text), "docx_for_hangul"
    except Exception as e:
        return None, str(e)
