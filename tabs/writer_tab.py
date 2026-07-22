"""탭 2: 요약문 편집 + HWPX/DOCX 다운로드."""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from services.editor_service import EditorState
from services.session_bridge import has_analysis_data
from services.text_hwpx_builder import build_docx_from_text, build_hwpx_from_text


def _get_editor() -> EditorState:
    if "da_writer_editor" not in st.session_state:
        st.session_state.da_writer_editor = EditorState()
    ed: EditorState = st.session_state.da_writer_editor
    ed.ollama_url = st.session_state.get("da_ollama_url", ed.ollama_url)
    ed.model = st.session_state.get("da_model", ed.model)
    return ed


def _source_summary() -> str:
    return (
        st.session_state.get("da_summary_text")
        or st.session_state.get("analysis_summary")
        or st.session_state.get("research_note_content")
        or ""
    )


def _ensure_built(text: str) -> bytes:
    """편집 텍스트 → HWPX bytes (다운로드용 원본, 에디터 save 거치지 않음)."""
    if text != st.session_state.get("da_writer_last_built_text"):
        st.session_state.da_writer_hwpx = build_hwpx_from_text(text)
        st.session_state.da_writer_docx = build_docx_from_text(text)
        st.session_state.da_writer_last_built_text = text
    return st.session_state.get("da_writer_hwpx") or b""


def render_writer_tab():
    st.header("연구노트 작성 및 문서 생성")
    summary = _source_summary()
    if not ((st.session_state.get("da_summary_ready") or has_analysis_data(st.session_state)) and summary):
        st.info(
            "1. **문서 분석 및 요약** 탭에서 문서 업로드\n"
            "2. 요약 생성 후 **「작성 탭으로 가져오기」**\n"
            "3. 이 탭에서 수정 → HWPX / DOCX 다운로드"
        )
        return

    src_hash = hash(summary)
    if st.session_state.get("da_writer_source_hash") != src_hash:
        st.session_state.da_writer_source_hash = src_hash
        st.session_state.da_writer_text = summary
        st.session_state.da_writer_last_built_text = None

    files = st.session_state.get("uploaded_file_names") or []
    if files:
        st.caption(f"참고 파일: {', '.join(files)}")

    edited = st.text_area(
        "요약문 직접 편집",
        key="da_writer_text",
        height=320,
    )

    try:
        hwpx_bytes = _ensure_built(edited)
    except Exception as e:
        st.error(f"문서 생성 실패: {e}")
        return

    if not hwpx_bytes:
        st.warning("생성할 내용이 없습니다.")
        return

    # 미리보기만 에디터 사용 (다운로드는 python-hwpx 원본 bytes)
    editor = _get_editor()
    if st.session_state.get("da_writer_loaded_hash") != hash(hwpx_bytes):
        try:
            editor.load_hwpx(hwpx_bytes, "research_note.hwpx")
            st.session_state.da_writer_loaded_hash = hash(hwpx_bytes)
        except Exception as e:
            st.caption(f"미리보기 로드 제한: {e}")

    st.subheader("미리보기")
    try:
        if editor.editor:
            components.html(editor.preview_html(), height=480, scrolling=True)
        else:
            st.text(edited)
    except Exception as e:
        st.warning(f"미리보기 오류: {e}")
        st.text_area("내용", value=edited, height=200, disabled=True)

    docx_bytes = st.session_state.get("da_writer_docx") or b""

    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "HWPX로 다운로드",
            data=hwpx_bytes,
            file_name="research_note.hwpx",
            mime="application/hwp+zip",
            use_container_width=True,
            key="da_dl_hwpx",
            type="primary",
        )
    with c2:
        st.download_button(
            "DOCX로 다운로드",
            data=docx_bytes,
            file_name="research_note.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
            key="da_dl_docx",
        )
    st.caption(
        "HWPX는 한글에서 바로 여는 형식입니다. "
        "HWP(.hwp) 바이너리는 이 환경에서 안정 생성이 어려워, 대신 DOCX를 제공합니다. "
        "한글에서 연 뒤 「다른 이름으로 저장 → HWP」하면 됩니다."
    )
