"""탭 2: 요약 편집(좌) · 연구노트 변환(중) · 연구노트 폼(우)."""

from __future__ import annotations

from datetime import date
from html import escape

import streamlit as st
import streamlit.components.v1 as components

from services.editor_service import EditorState
from services.session_bridge import has_analysis_data
from services.text_hwpx_builder import (
    build_docx_from_text,
    build_hwpx_from_text,
    build_research_note_docx,
    build_research_note_hwpx,
)


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


_RN_FIELD_KEYS = (
    "rn_topic",
    "rn_owner",
    "rn_author",
    "rn_content",
    "rn_results",
    "rn_etc",
    "rn_date",
)


def _rn_persist_store() -> dict:
    return st.session_state.setdefault("da_rn_persist", {})


def _save_rn_fields_to_persist():
    """위젯이 언마운트되어도 값이 남도록 별도 저장."""
    store = _rn_persist_store()
    for k in _RN_FIELD_KEYS:
        if k in st.session_state:
            store[k] = st.session_state[k]
    if "da_rn_converted" in st.session_state:
        store["da_rn_converted"] = st.session_state["da_rn_converted"]


def _restore_rn_fields_from_persist():
    store = st.session_state.get("da_rn_persist") or {}
    for k in _RN_FIELD_KEYS:
        if k in store and k not in st.session_state:
            st.session_state[k] = store[k]
    if "da_rn_converted" in store and "da_rn_converted" not in st.session_state:
        st.session_state["da_rn_converted"] = store["da_rn_converted"]


def _on_rn_field_change():
    _save_rn_fields_to_persist()


def _init_research_note_fields():
    _restore_rn_fields_from_persist()
    defaults = {
        "rn_topic": "",
        "rn_owner": "",
        "rn_author": "",
        "rn_content": "",
        "rn_results": "",
        "rn_etc": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    if "rn_date" not in st.session_state:
        st.session_state.rn_date = date.today()
    _save_rn_fields_to_persist()


def _apply_pending_convert():
    """위젯 생성 전에 변환 결과 반영."""
    pending = st.session_state.pop("da_rn_pending_content", None)
    if pending is not None:
        st.session_state["rn_content"] = pending
        st.session_state["da_rn_converted"] = True
        _save_rn_fields_to_persist()


def _research_note_rows() -> list[tuple[str, str]]:
    d = st.session_state.get("rn_date")
    date_s = d.isoformat() if hasattr(d, "isoformat") else str(d or "")
    return [
        ("주 제", st.session_state.get("rn_topic") or ""),
        ("책 임 자", st.session_state.get("rn_owner") or ""),
        ("일 시", date_s),
        ("작 성 자", st.session_state.get("rn_author") or ""),
        ("내 용", st.session_state.get("rn_content") or ""),
        ("연구결과", st.session_state.get("rn_results") or ""),
        ("기타내용", st.session_state.get("rn_etc") or ""),
    ]


def _research_note_plain() -> str:
    d = st.session_state.get("rn_date")
    date_s = d.isoformat() if hasattr(d, "isoformat") else str(d or "")
    parts = [
        "연구노트",
        "",
        f"주제: {st.session_state.get('rn_topic') or ''}",
        f"책임자: {st.session_state.get('rn_owner') or ''}",
        f"일시: {date_s}",
        f"작성자: {st.session_state.get('rn_author') or ''}",
        "",
        "내용",
        st.session_state.get("rn_content") or "",
        "",
        "연구결과",
        st.session_state.get("rn_results") or "",
        "",
        "기타내용",
        st.session_state.get("rn_etc") or "",
    ]
    return "\n".join(parts)


def _research_note_preview_html() -> str:
    rows = _research_note_rows()
    tall = {"내 용", "연구결과", "기타내용"}
    body = []
    for label, val in rows:
        min_h = "140px" if label == "내 용" else ("90px" if label in tall else "36px")
        body.append(
            f"""<tr>
  <th style="width:22%;background:#f0f0f0;text-align:center;vertical-align:middle;
             border:1px solid #333;padding:8px;font-weight:600;letter-spacing:0.2em;">{escape(label)}</th>
  <td style="border:1px solid #333;padding:8px;vertical-align:top;min-height:{min_h};
             white-space:pre-wrap;">{escape(val)}</td>
</tr>"""
        )
    return f"""
<div style="font-family:'Malgun Gothic','맑은 고딕',sans-serif;color:#111;">
  <div style="text-align:center;font-size:22px;font-weight:700;margin:8px 0 14px;">연구노트</div>
  <table style="width:100%;border-collapse:collapse;table-layout:fixed;">
    {''.join(body)}
  </table>
</div>
"""


def _ensure_built(text: str) -> tuple[bytes, bytes]:
    key = "da_writer_last_built_text"
    if text != st.session_state.get(key):
        st.session_state.da_writer_hwpx = build_hwpx_from_text(text)
        st.session_state.da_writer_docx = build_docx_from_text(text)
        st.session_state[key] = text
    return (
        st.session_state.get("da_writer_hwpx") or b"",
        st.session_state.get("da_writer_docx") or b"",
    )


def render_writer_tab():
    st.header("연구노트 작성 및 문서 생성")
    _init_research_note_fields()
    _apply_pending_convert()

    summary = _source_summary()
    has_source = bool(
        (st.session_state.get("da_summary_ready") or has_analysis_data(st.session_state)) and summary
    )
    has_draft = any(
        str((_rn_persist_store().get(k) or "")).strip()
        for k in ("rn_topic", "rn_owner", "rn_author", "rn_content", "rn_results", "rn_etc")
    ) or bool(_rn_persist_store().get("da_rn_converted"))

    if not has_source and not has_draft:
        st.info(
            "1. **문서 분석 및 요약** 탭에서 문서 업로드\n"
            "2. 요약 생성 후 **「작성 탭으로 가져오기」**\n"
            "3. 왼쪽에서 수정 → **연구노트로 변환** → 오른쪽 작성 → 다운로드"
        )
        return

    if has_source:
        src_hash = hash(summary)
        if st.session_state.get("da_writer_source_hash") != src_hash:
            st.session_state.da_writer_source_hash = src_hash
            # 사용자가 이미 편집 중이면 덮어쓰지 않음
            if not st.session_state.get("da_writer_text"):
                st.session_state.da_writer_text = summary
            elif st.session_state.get("da_writer_text") == st.session_state.get("da_writer_prev_summary"):
                st.session_state.da_writer_text = summary
            st.session_state.da_writer_prev_summary = summary
            st.session_state.da_writer_last_built_text = None

    files = st.session_state.get("uploaded_file_names") or []
    if files:
        st.caption(f"참고 파일: {', '.join(files)}")

    left, mid, right = st.columns([5, 1.2, 5], gap="medium")

    # ----- 왼쪽: 요약 편집 + 미리보기 -----
    with left:
        st.subheader("요약문")
        if "da_writer_text" not in st.session_state and summary:
            st.session_state.da_writer_text = summary
        edited = st.text_area(
            "요약문 직접 편집",
            key="da_writer_text",
            height=280,
            label_visibility="collapsed",
        )
        try:
            left_hwpx, _ = _ensure_built(edited)
        except Exception as e:
            st.error(f"미리보기 문서 생성 실패: {e}")
            left_hwpx = b""

        editor = _get_editor()
        if left_hwpx and st.session_state.get("da_writer_loaded_hash") != hash(left_hwpx):
            try:
                editor.load_hwpx(left_hwpx, "summary_preview.hwpx")
                st.session_state.da_writer_loaded_hash = hash(left_hwpx)
            except Exception as e:
                st.caption(f"미리보기 로드 제한: {e}")

        st.markdown("**미리보기**")
        try:
            if editor.editor:
                components.html(editor.preview_html(), height=360, scrolling=True)
            else:
                st.text(edited)
        except Exception as e:
            st.warning(f"미리보기 오류: {e}")

    # ----- 가운데: 변환 버튼 -----
    with mid:
        st.write("")
        st.write("")
        st.write("")
        if st.button("연구노트로\n변환", type="primary", use_container_width=True, key="da_rn_convert"):
            st.session_state.da_rn_pending_content = st.session_state.get("da_writer_text") or ""
            st.rerun()
        if st.session_state.get("da_rn_converted"):
            st.caption("변환됨 →")

    # ----- 오른쪽: 연구노트 폼 + 템플릿 미리보기 -----
    with right:
        st.subheader("연구노트")
        st.text_input("주제", key="rn_topic", on_change=_on_rn_field_change)
        st.text_input("책임자", key="rn_owner", on_change=_on_rn_field_change)
        st.date_input("일시", key="rn_date", on_change=_on_rn_field_change)
        st.text_input("작성자", key="rn_author", on_change=_on_rn_field_change)
        st.text_area("내용", key="rn_content", height=160, on_change=_on_rn_field_change)
        st.text_area("연구결과", key="rn_results", height=100, on_change=_on_rn_field_change)
        st.text_area("기타내용", key="rn_etc", height=80, on_change=_on_rn_field_change)
        _save_rn_fields_to_persist()

        st.markdown("**연구노트 미리보기**")
        components.html(_research_note_preview_html(), height=420, scrolling=True)

    st.markdown("---")
    st.subheader("다운로드")

    # 연구노트 변환 후에는 미리보기와 같은 표 형식으로 저장
    try:
        if st.session_state.get("da_rn_converted"):
            rows = _research_note_rows()
            hwpx_bytes = build_research_note_hwpx(rows)
            docx_bytes = build_research_note_docx(rows)
        else:
            export_text = st.session_state.get("da_writer_text") or ""
            hwpx_bytes = build_hwpx_from_text(export_text)
            docx_bytes = build_docx_from_text(export_text)
    except Exception as e:
        st.error(f"다운로드 파일 생성 실패: {e}")
        return

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
    if not st.session_state.get("da_rn_converted"):
        st.caption("연구노트 표 형식으로 받으려면 먼저 「연구노트로 변환」을 눌러 주세요.")
