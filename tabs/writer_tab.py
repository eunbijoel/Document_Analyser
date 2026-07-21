"""탭 2: Q&A 요약 → 새 HWPX (Step 2에서 구현)."""

from __future__ import annotations

import streamlit as st

from services.session_bridge import has_analysis_data


def render_writer_tab():
    st.header("연구노트 작성 및 문서 생성")

    st.warning(
        "**Step 2 예정** — HWPX 파일 생성은 다음 단계에서 구현합니다. "
        "지금은 분석 탭에서 넘긴 요약을 확인할 수 있습니다."
    )

    summary = (
        st.session_state.get("da_summary_text")
        or st.session_state.get("analysis_summary")
        or st.session_state.get("research_note_content")
        or ""
    )
    if (st.session_state.get("da_summary_ready") or has_analysis_data(st.session_state)) and summary:
        st.subheader("분석 탭에서 받은 요약")
        st.text_area(
            "요약 내용",
            value=summary,
            height=320,
            disabled=True,
            key="da_preview_summary",
        )
        files = st.session_state.get("uploaded_file_names") or []
        if files:
            st.caption(f"참고 파일: {', '.join(files)}")
        st.caption("Step 2에서 이 내용으로 한글에서 열리는 HWPX 파일을 생성합니다.")
    else:
        st.info(
            "1. **문서 분석 및 요약** 탭에서 HWP/HWPX 업로드\n"
            "2. **「문서 요약」** 또는 **「연구노트용 통합 요약 (20줄)」** 생성\n"
            "3. **「작성 탭으로 가져오기」** 클릭 (또는 Q&A 답변 → 작성 탭)\n"
            "4. 이 탭에서 HWPX 생성 (Step 2)"
        )

    with st.expander("고급: Product B 전체 편집기 (Flask)"):
        st.caption("표 클릭 선택·멀티 문서·Completion Planner는 기존 B 편집기를 사용하세요.")
        st.code("cd '/home/eunbi/HWP analysis' && python3 HWP_v2/server.py", language="bash")
        st.markdown("[http://127.0.0.1:8765](http://127.0.0.1:8765)")
