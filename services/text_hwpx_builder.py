"""요약 텍스트 → 한글에서 열리는 문서 생성.

hwpilot/ElementTree로 만든 HWPX는 필수 패키지(mimetype, Preview, container.xml 등)가
빠져 한글에서 「손상」되거나 ZIP 바이너리(PK…)로 보입니다.
python-hwpx 공식 템플릿을 사용합니다.
"""

from __future__ import annotations

import io
import re


def _paragraph_lines(text: str) -> list[str]:
    lines = [ln.rstrip() for ln in (text or "").splitlines()]
    # 연속 빈 줄 축소, 완전 빈 문서는 공백 한 줄
    out: list[str] = []
    for ln in lines:
        if ln.strip() == "" and out and out[-1] == "":
            continue
        out.append(ln)
    if not any(x.strip() for x in out):
        return [" "]
    return out


def build_hwpx_from_text(text: str) -> bytes:
    """한글 호환 HWPX (python-hwpx)."""
    from hwpx import HwpxDocument

    doc = HwpxDocument.new()
    lines = _paragraph_lines(text)
    # 템플릿 기본 문단이 있으면 첫 줄을 거기에 넣고 나머지를 추가
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
    """한글에서 열리는 DOCX (HWP 대체)."""
    from docx import Document

    d = Document()
    for ln in _paragraph_lines(text):
        d.add_paragraph(ln)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def build_hwp_from_text(text: str) -> tuple[bytes | None, str]:
    """
    한글 호환 HWP 바이너리는 Linux에서 안정적으로 만들기 어렵습니다.
    DOCX를 반환하고 note에 안내합니다. (확장자는 호출측에서 .docx 사용)
    """
    try:
        return build_docx_from_text(text), "docx_for_hangul"
    except Exception as e:
        return None, str(e)
