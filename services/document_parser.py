"""다형식 문서 파싱 — intelligence_adapter 재사용."""

from __future__ import annotations

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
        """QAEngine 호환 dict (TableSummary는 adapter 경로에서 별도 제공)."""
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
    from additional.intelligence_adapter import process_file_for_intelligence

    entry = process_file_for_intelligence(file_bytes, filename)
    doc = entry.doc
    tables_raw = getattr(doc, "tables_raw", []) or []
    table_rows = [t.get("rows", []) for t in tables_raw if isinstance(t, dict) and t.get("rows")]
    if not table_rows and entry.tables:
        for ts in entry.tables:
            df = getattr(ts, "dataframe", None)
            if df is not None and not df.empty:
                table_rows.append(df.astype(str).values.tolist())

    result = ParseResult(
        filename=filename,
        file_type=entry.status.file_type,
        full_text=doc.full_text or "",
        paragraphs=list(doc.paragraphs or []),
        tables=table_rows,
        char_count=entry.status.char_count,
        ok=entry.status.ok,
        errors=list(doc.errors or []),
    )
    if entry.status.error and not result.ok:
        result.errors.append(entry.status.error)
    return result
