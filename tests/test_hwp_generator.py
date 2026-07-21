import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HWP = Path("/home/eunbi/HWP analysis")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HWP))

from services.session_bridge import ResearchNoteFields
from services.hwp_generator import build_research_note_hwpx, build_research_note_filename


def test_build_hwpx():
    fields = ResearchNoteFields(
        title="테스트 연구노트",
        written_date="2026-07-21",
        author="홍길동",
        purpose="통합 앱 검증",
        main_work="Document_Analyser 구현",
        results="HWPX 생성 성공",
    )
    data = build_research_note_hwpx(fields)
    assert data[:2] == b"PK"
    assert build_research_note_filename(fields.title).endswith(".hwpx")
