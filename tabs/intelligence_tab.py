"""탭 1: Product A Intelligence + 연구노트 요약."""

from __future__ import annotations

import streamlit as st

from apps.intelligence.ui import get_last_assistant_answer, render_intelligence_tab
from hwp_core.knowledge_mode import KnowledgeMode
from services.session_bridge import save_analysis_to_writer
from services.summarizer import (
    RESEARCH_NOTE_SECTIONS,
    parse_research_note_fields,
    suggest_title,
)


def _init_summary_state():
    if "da_short_summary" not in st.session_state:
        st.session_state.da_short_summary = ""


def _apply_pending_summary_edits():
    """text_area 위젯 생성 전에 session_state 반영 (Streamlit key 충돌 방지)."""
    pending = st.session_state.pop("da_pending_research_summary", None)
    if pending is not None:
        st.session_state["da_research_summary_edit"] = pending

    transfer = st.session_state.pop("da_pending_qa_transfer", None)
    if transfer is not None:
        st.session_state["da_summary_text"] = transfer
        st.session_state["da_summary_ready"] = True
        st.session_state["da_research_summary_edit"] = transfer
        st.session_state["da_transfer_ok"] = True


def _active_filenames() -> list[str]:
    names = [
        key[len("file_active_"):]
        for key, val in st.session_state.items()
        if key.startswith("file_active_") and val
    ]
    if names:
        return names
    return [
        key[len("upload_bytes_"):]
        for key in st.session_state
        if key.startswith("upload_bytes_")
    ]


def _collect_active_qa_documents() -> list[dict]:
    """Product A와 동일한 doc_payload (TableSummary 포함)."""
    documents: list[dict] = []
    for storage_id in _active_filenames():
        raw = st.session_state.get(f"upload_bytes_{storage_id}")
        if raw is None:
            continue
        cached = st.session_state.get(f"parsed_{storage_id}_{len(raw)}")
        if not cached:
            continue
        doc = cached["doc"]
        from additional.intelligence_adapter import display_filename

        label = display_filename(storage_id)
        documents.append({
            "id": storage_id,
            "filename": label,
            "name": label,
            "paragraphs": list(doc.paragraphs or []),
            "full_text": doc.full_text or "",
            "tables": cached.get("tables") or [],
            "text_numbers": cached.get("text_numbers") or [],
            "table_numbers": cached.get("table_numbers") or [],
            "doc": doc,
            "intel": cached.get("intel"),
        })
    return documents


def _get_summary_qa_engine(documents: list[dict]):
    from hwp_core.qa_engine import QAEngine

    ids = "_".join(sorted(d["id"] for d in documents))
    key = f"da_summary_qa_{ids}"
    if key not in st.session_state:
        st.session_state[key] = QAEngine(documents=documents)
    return st.session_state[key]


def _active_chat_key() -> str:
    target = st.session_state.get("active_file_chat_target")
    if target:
        return f"workspace_chat_{target}"
    for key in st.session_state:
        if key.startswith("workspace_chat_") and key != "workspace_chat_ALL":
            return key
    return "workspace_chat_ALL"


def _get_last_qa_answer(documents: list[dict]) -> str:
    """여러 문서일 때 「전체」 채팅 답변 우선."""
    if len(documents) > 1:
        all_ans = get_last_assistant_answer("workspace_chat_ALL")
        if all_ans:
            return all_ans
    return (
        get_last_assistant_answer(_active_chat_key())
        or get_last_assistant_answer("workspace_chat_ALL")
        or ""
    )


def _all_files_question(documents: list[dict], base: str) -> str:
    names = ", ".join(d["filename"] for d in documents)
    return (
        f"다음 {len(documents)}개 파일 전체를 통합하여 답하세요: {names}\n\n"
        f"{base}"
    )


def _run_qa_summary(
    documents: list[dict],
    question: str,
    *,
    model: str,
    ollama_url: str,
    use_llm: bool,
) -> str:
    qa = _get_summary_qa_engine(documents)
    ans = qa.answer(
        question=question,
        use_llm=use_llm,
        model=model,
        ollama_url=ollama_url,
        stage1_model=model,
        knowledge_mode="document_only",
    )
    return (ans.get("answer") or "").strip()


def _rn_form_has_core_fields() -> bool:
    """주제·내용·연구결과가 이미 채워졌으면 재생성 시 폼을 덮지 않음.
    내용이 비어 있으면 미완료로 보고 다시 자동 채움을 허용."""
    store = st.session_state.get("da_rn_persist") or {}
    content = str(store.get("rn_content") or st.session_state.get("rn_content") or "").strip()
    if store.get("da_rn_form_seeded") or st.session_state.get("da_rn_form_seeded"):
        return bool(content)
    topic = str(store.get("rn_topic") or st.session_state.get("rn_topic") or "").strip()
    results = str(store.get("rn_results") or st.session_state.get("rn_results") or "").strip()
    return bool(topic and content and results)


def _render_summary_section(
    *,
    model: str,
    ollama_url: str,
    use_llm: bool,
):
    _apply_pending_summary_edits()

    documents = _collect_active_qa_documents()
    if not documents:
        return

    filenames = [d["filename"] for d in documents]

    st.markdown("---")
    st.subheader("연구노트용 요약")
    st.caption(
        f"왼쪽 사이드바에서 **활성화된 {len(documents)}개 파일 전체**를 대상으로 요약합니다: "
        + ", ".join(filenames)
    )

    if st.session_state.pop("da_transfer_ok", False):
        st.success(
            "작성 탭으로 전달했습니다. 「연구노트 작성 및 문서 생성」 탭을 열어 주세요."
        )
    if st.session_state.pop("da_rn_fields_kept", False):
        st.info(
            "통합 요약을 요약문에 넣었습니다. **작성 탭 폼(주제·내용·연구결과)은 유지**됩니다. "
            "폼을 바꾸려면 작성 탭에서 **「연구노트로 변환」**을 누르세요."
        )
    if st.session_state.pop("da_rn_fields_seeded_ok", False):
        st.success(
            "통합 요약을 만들었습니다. 작성 탭을 열면 **주제·내용·연구결과**가 처음 한 번 자동으로 채워집니다."
        )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("문서 요약 (짧게)", use_container_width=True, key="da_btn_short"):
            with st.spinner("전체 문서 요약 생성…"):
                text = _run_qa_summary(
                    documents,
                    _all_files_question(
                        documents,
                        "모든 파일의 핵심 내용을 통합하여 10줄 이내로 요약해 주세요.",
                    ),
                    model=model,
                    ollama_url=ollama_url,
                    use_llm=use_llm,
                )
            st.session_state.da_short_summary = text
            if not text:
                st.warning("요약이 비어 있습니다. Ollama 연결을 확인하세요.")
            st.rerun()
    with col2:
        if st.button(
            "연구노트용 통합 요약",
            type="primary",
            use_container_width=True,
            key="da_btn_research",
            help="전체 템플릿 요약 + 주제/내용/연구결과는 작성 탭 폼에 반영(처음만 자동).",
        ):
            with st.spinner("연구노트용 통합 요약 생성…"):
                text = _run_qa_summary(
                    documents,
                    _all_files_question(
                        documents,
                        f"연구노트용 통합 요약을 작성하세요.\n\n{RESEARCH_NOTE_SECTIONS}",
                    ),
                    model=model,
                    ollama_url=ollama_url,
                    use_llm=use_llm,
                )
            # 전체 템플릿 → 요약문. 주제/내용/연구결과만 폼(처음만 자동).
            st.session_state.da_pending_research_summary = text
            fields = parse_research_note_fields(text)
            if not text.strip():
                st.warning("요약이 비어 있습니다. Ollama 연결을 확인하세요.")
            elif _rn_form_has_core_fields():
                st.session_state.pop("da_pending_rn_fields", None)
                st.session_state.da_rn_fields_kept = True
            else:
                st.session_state.da_pending_rn_fields = {
                    "rn_topic": fields.get("topic") or "",
                    "rn_content": fields.get("content") or "",
                    "rn_results": fields.get("results") or "",
                }
                st.session_state.da_rn_fields_seeded_ok = True
            st.rerun()

    if st.session_state.get("da_short_summary"):
        with st.expander("짧은 요약", expanded=True):
            st.write(st.session_state.da_short_summary)

    st.markdown("**연구노트용 요약문**")
    edited = st.text_area(
        "수정 가능",
        height=320,
        key="da_research_summary_edit",
        placeholder="「연구노트용 통합 요약」으로 생성하거나 직접 입력하세요.",
        label_visibility="collapsed",
    )

    title = suggest_title(filenames, edited)
    keywords = extract_keywords_from_docs(documents, edited)

    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("작성 탭으로 가져오기", type="primary", use_container_width=True):
            if not (edited or "").strip():
                st.error("가져올 요약문이 없습니다. 요약을 생성하거나 입력하세요.")
            else:
                save_analysis_to_writer(
                    st.session_state,
                    summary=edited.strip(),
                    filenames=filenames,
                    title=title,
                    keywords=keywords,
                )
                st.session_state.da_summary_text = edited.strip()
                st.session_state.da_summary_ready = True
                st.success(
                    "작성 탭 **요약문**으로 전달했습니다. "
                    "(주제·내용·연구결과는 첫 생성 시 자동, 이후에는 **「연구노트로 변환」**)"
                )
    with btn_col2:
        last = _get_last_qa_answer(documents)
        if st.button("마지막 Q&A 답변 → 작성 탭으로", use_container_width=True):
            if not last:
                st.warning("Q&A 답변이 없습니다. 먼저 채팅에서 질문해 주세요.")
            else:
                st.session_state.da_pending_qa_transfer = last
                st.rerun()


def extract_keywords_from_docs(documents: list[dict], summary: str, limit: int = 8) -> list[str]:
    """파일명 + 요약에서 간단 키워드."""
    import re

    kws: list[str] = []
    for d in documents:
        stem = re.sub(r"\.[^.]+$", "", d.get("filename") or d.get("id") or "")
        if stem and stem not in kws:
            kws.append(stem)
    for m in re.finditer(r"[가-힣]{2,8}", summary[:800]):
        w = m.group(0)
        if w not in kws and len(kws) < limit:
            kws.append(w)
    return kws[:limit]


def render_intelligence_tab_embedded(
    *,
    model: str,
    ollama_url: str,
    use_llm: bool,
    knowledge_mode: KnowledgeMode,
):
    _init_summary_state()

    render_intelligence_tab(
        model_name=model,
        stage1_model=model,
        use_llm=use_llm,
        use_streaming=use_llm,
        ollama_url=ollama_url,
        knowledge_mode=knowledge_mode,
        show_hero=False,
        extended_formats=True,
    )

    _render_summary_section(model=model, ollama_url=ollama_url, use_llm=use_llm)
