"""탭 1: Product A Intelligence + 연구노트 요약."""

from __future__ import annotations

import streamlit as st

from apps.intelligence.ui import get_last_assistant_answer, render_intelligence_tab
from hwp_core.knowledge_mode import KnowledgeMode
from services.session_bridge import save_analysis_to_writer
from services.summarizer import (
    RESEARCH_NOTE_SECTIONS,
    extract_keywords,
    suggest_title,
)


def _init_summary_state():
    if "da_short_summary" not in st.session_state:
        st.session_state.da_short_summary = ""
    if "da_research_summary_edit" not in st.session_state:
        st.session_state.da_research_summary_edit = ""


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
    for filename in _active_filenames():
        raw = st.session_state.get(f"upload_bytes_{filename}")
        if raw is None:
            continue
        cached = st.session_state.get(f"parsed_{filename}_{len(raw)}")
        if not cached:
            continue
        doc = cached["doc"]
        documents.append({
            "id": filename,
            "filename": filename,
            "name": filename,
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


def _render_summary_section(
    *,
    model: str,
    ollama_url: str,
    use_llm: bool,
):
    documents = _collect_active_qa_documents()
    if not documents:
        return

    filenames = [d["filename"] for d in documents]

    st.markdown("---")
    st.subheader("연구노트용 요약")
    st.caption("채팅 Q&A와 같은 엔진으로 요약합니다.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("문서 요약 (짧게)", use_container_width=True, key="da_btn_short"):
            with st.spinner("요약 생성…"):
                text = _run_qa_summary(
                    documents,
                    "이 문서들의 핵심 내용을 10줄 이내로 요약해 주세요.",
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
            "연구노트용 통합 요약 (20줄)",
            type="primary",
            use_container_width=True,
            key="da_btn_research",
        ):
            with st.spinner("연구노트 요약 생성…"):
                text = _run_qa_summary(
                    documents,
                    f"다음 자료들을 읽고 연구노트에 넣을 통합 요약을 작성하세요.\n\n{RESEARCH_NOTE_SECTIONS}",
                    model=model,
                    ollama_url=ollama_url,
                    use_llm=use_llm,
                )
            st.session_state.da_research_summary_edit = text
            if not text:
                st.warning("요약이 비어 있습니다. Ollama 연결을 확인하세요.")
            st.rerun()

    if st.session_state.get("da_short_summary"):
        with st.expander("짧은 요약", expanded=True):
            st.write(st.session_state.da_short_summary)

    st.markdown("**연구노트용 요약문**")
    edited = st.text_area(
        "수정 가능",
        height=320,
        key="da_research_summary_edit",
        placeholder="「연구노트용 통합 요약」 버튼으로 생성하거나 직접 입력하세요.",
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
                    "작성 탭으로 전달했습니다. 「연구노트 작성 및 문서 생성」 탭을 열어 주세요."
                )
    with btn_col2:
        last = get_last_assistant_answer(_active_chat_key())
        if not last:
            last = get_last_assistant_answer("workspace_chat_ALL")
        if st.button("마지막 Q&A 답변 → 작성 탭으로", use_container_width=True):
            if not last:
                st.warning("Q&A 답변이 없습니다. 먼저 채팅에서 질문해 주세요.")
            else:
                st.session_state.da_summary_text = last
                st.session_state.da_research_summary_edit = last
                st.session_state.da_summary_ready = True
                st.success(
                    "작성 탭으로 전달했습니다. 「연구노트 작성 및 문서 생성」 탭을 열어 주세요."
                )


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
    )

    _render_summary_section(model=model, ollama_url=ollama_url, use_llm=use_llm)
