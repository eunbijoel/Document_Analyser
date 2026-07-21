"""다형식 문서 파싱 — A 파서 + reference_parser 재사용."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from services._hwp_path import ensure_hwp_paths


@dataclass
class ParseResult:
    filename: str
    file_type: str
    full_text: str = ""
    paragraphs: list[str] = field(default_factory=list)
    tables: list[list[list[str]]] = field(default_factory=list)
    char_count: int = 0
    ok: bool = False
    errors: list[str] = field(default_factory=list)

    def to_qa_document(self) -> dict[str, Any]:
        """QAEngine 호환 dict."""
        return {
            "filename": self.filename,
            "name": self.filename,
            "paragraphs": self.paragraphs,
            "full_text": self.full_text,
            "tables": [
                {"document_id": self.filename, "rows": rows, "table_index": i}
                for i, rows in enumerate(self.tables)
            ],
        }


def parse_upload(file_bytes: bytes, filename: str) -> ParseResult:
    ensure_hwp_paths()
    ext = os.path.splitext(filename)[1].lower()
    result = ParseResult(filename=filename, file_type=ext.lstrip("."))

    try:
        if ext in (".hwp", ".hwpx"):
            from hwp_core.hwp_parser import parse_document
            from hwp_core.table_extractor import extract_tables

            doc = parse_document(file_bytes=file_bytes, filename=filename)
            result.full_text = doc.full_text or ""
            result.paragraphs = list(doc.paragraphs or [])
            result.errors = list(doc.errors or [])
            tables = extract_tables(doc, document_id=filename)
            result.tables = [t.get("rows", []) for t in tables if t.get("rows")]
            result.file_type = getattr(doc, "file_type", None) or ext.lstrip(".")
        elif ext == ".py":
            from additional.reference_parser import parse_reference

            ref = parse_reference(file_bytes, filename.replace(".py", ".txt"))
            if not ref.full_text.strip():
                try:
                    text = file_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    text = file_bytes.decode("cp949", errors="ignore")
                ref.full_text = f"[Python 소스: {filename}]\n{text}"
                ref.paragraphs = [ln for ln in text.splitlines() if ln.strip()]
            result.full_text = ref.full_text
            result.paragraphs = list(ref.paragraphs)
            result.tables = list(ref.tables)
            result.errors = list(ref.errors)
            result.file_type = "py"
        elif ext in (".txt", ".md", ".csv", ".pdf", ".docx", ".xlsx", ".xls"):
            from additional.reference_parser import parse_reference

            ref = parse_reference(file_bytes, filename)
            result.full_text = ref.full_text
            result.paragraphs = list(ref.paragraphs)
            result.tables = list(ref.tables)
            result.errors = list(ref.errors)
            result.file_type = ref.file_type or ext.lstrip(".")
        else:
            result.errors.append(f"지원하지 않는 형식: {ext}")
            return result
    except Exception as e:
        result.errors.append(str(e))
        return result

    result.char_count = len(result.full_text or "")
    result.ok = bool(result.full_text.strip()) and not any(
        "오류" in e or "미설치" in e for e in result.errors
    )
    if result.full_text.strip() and not result.ok and not result.errors:
        result.ok = True
    return result
