import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.session_bridge import (
    parse_summary_into_fields,
    save_analysis_to_writer,
    load_from_analyzer,
    has_analysis_data,
)


class FakeState(dict):
    pass


def test_save_and_load_bridge():
    s = FakeState()
    save_analysis_to_writer(
        s,
        summary="1. 연구 목적\n테스트 목적\n2. 주요 작업\n코드 작성",
        filenames=["a.py", "b.pdf"],
        title="연구노트 — test",
        keywords=["test"],
    )
    assert has_analysis_data(s)
    fields = load_from_analyzer(s)
    assert fields is not None
    assert fields.title == "연구노트 — test"
    assert "a.py" in fields.reference_files


def test_parse_summary_fields():
    f = parse_summary_into_fields(
        "연구 목적: 자동화\n주요 작업 내용: 파서 연결",
        filenames=["x.hwpx"],
    )
    assert f.purpose or f.body
