"""탭 1: 문서 분석 및 요약."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import streamlit as st

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from services._hwp_path import ensure_hwp_paths
from services.document_parser import ParseResult, parse_upload
from services.session_bridge import save_analysis_to_writer
from services.summarizer import (
    extract_keywords,
    generate_research_note_summary,
    suggest_title,
)


def _init_state():
    if "da_parse_results" not in st.session_state:
        st.session_state.da_parse_results = {}
    if "da_qa_documents" not in st.session_state:
        st.session_state.da_qa_documents = []
    if "da_research_summary" not in st.session_state:
        st.session_state.da_research_summary = ""
    if "da_analyzer_chat" not in st.session_state:
        st.session_state.da_analyzer_chat = []


def _process_uploads(uploaded_files) -> list[ParseResult]:
    results: list[ParseResult] = []
    for uf in uploaded_files:
        raw = uf.read()
        h = hashlib.sha256(raw).hexdigest()
        key = f"da_file_{uf.name}"
        if st.session_state.get(f"{key}_hash") != h:
            st.session_state[f"{key}_hash"] = h
            st.session_state[f"{key}_bytes"] = raw
            pr = parse_upload(raw, uf.name)
            st.session_state.da_parse_results[uf.name] = pr
        else:
            pr = st.session_state.da_parse_results.get(uf.name)
            if pr is None:
                pr = parse_upload(st.session_state[f"{key}_bytes"], uf.name)
                st.session_state.da_parse_results[uf.name] = pr
        results.append(st.session_state.da_parse_results[uf.name])
    return results


def _render_parse_table(results: list[ParseResult]):
    if not results:
        return
    rows = []
    for r in results:
        rows.append({
            "파일": r.filename,
            "형식": r.file_type,
            "추출": "성공" if r.ok else "실패",
            "글자 수": r.char_count,
            "오류": "; ".join(r.errors[:2]) if r.errors else "",
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_qa(
    documents: list[dict],
    *,
    model: str,
    stage1_model: str,
    ollama_url: str,
    use_llm: bool,
    knowledge_mode: str,
):
    ensure_hwp_paths()
    from hwp_core.analysis.intent_route import (
        analysis_chat_reply_for_edit_intent,
        route_analysis_intent,
    )
    from hwp_core.knowledge_mode import DEFAULT_KNOWLEDGE_MODE, normalize_knowledge_mode
    from hwp_core.qa_engine import QAEngine

    km = normalize_knowledge_mode(knowledge_mode or DEFAULT_KNOWLEDGE_MODE)
    chat_key = "da_analyzer_chat"
    with st.expander("문서 Q&A", expanded=True):
        for msg in st.session_state.get(chat_key, []):
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
        q = st.chat_input("문서에 질문…", key="da_analyzer_chat_input")
        if not q:
            return
        st.session_state[chat_key].append({"role": "user", "content": q})
        route = route_analysis_intent(q)
        if route != "qa":
            st.session_state[chat_key].append({
                "role": "assistant",
                "content": analysis_chat_reply_for_edit_intent(route),
            })
            st.rerun()
        qa = QAEngine(documents=documents)
        with st.spinner("분석 중…"):
            ans = qa.answer(
                question=q,
                use_llm=use_llm,
                model=model,
                ollama_url=ollama_url,
                stage1_model=stage1_model,
                knowledge_mode=km,
            )
        st.session_state[chat_key].append({
            "role": "assistant",
            "content": ans.get("answer") or "답변 없음",
        })
        st.rerun()


def render_analyzer_tab(
    *,
    model: str,
    stage1_model: str,
    ollama_url: str,
    use_llm: bool,
    knowledge_mode: str,
):
    _init_state()
    st.header("문서 분석 및 요약")
    st.caption("HWP · HWPX · PDF · TXT · PY 업로드 → 추출 · Q&A · 연구노트용 요약")

    uploaded = st.file_uploader(
        "문서 추가",
        type=["hwp", "hwpx", "pdf", "txt", "py", "md"],
        accept_multiple_files=True,
        key="da_uploader",
    )

    if not uploaded:
        st.info("파일을 업로드하면 내용 추출과 요약을 시작할 수 있습니다.")
        return

    results = _process_uploads(uploaded)
    st.subheader("추출 상태")
    _render_parse_table(results)

    documents = [r.to_qa_document() for r in results if r.full_text.strip()]
    st.session_state.da_qa_documents = documents

    col1, col2 = st.columns(2)
    with col1:
        if st.button("문서 요약 (짧게)", use_container_width=True):
            ensure_hwp_paths()
            from hwp_core.qa_engine import QAEngine
            qa = QAEngine(documents=documents)
            with st.spinner("요약 생성…"):
                ans = qa.answer(
                    question="이 문서들의 핵심 내용을 10줄 이내로 요약해 주세요.",
                    use_llm=use_llm,
                    model=model,
                    ollama_url=ollama_url,
                    knowledge_mode="document_only",
                )
            st.session_state.da_short_summary = ans.get("answer") or ""
    with col2:
        if st.button("연구노트용 통합 요약 (20줄)", type="primary", use_container_width=True):
            with st.spinner("연구노트 요약 생성…"):
                summary, err = generate_research_note_summary(
                    results,
                    model=model,
                    ollama_url=ollama_url,
                    use_llm=use_llm,
                )
                st.session_state.da_research_summary = summary
                if err:
                    st.warning(err)

    if st.session_state.get("da_short_summary"):
        with st.expander("짧은 요약"):
            st.write(st.session_state.da_short_summary)

    summary = st.session_state.get("da_research_summary") or ""
    st.subheader("연구노트용 요약문")
    edited = st.text_area(
        "수정 가능",
        value=summary,
        height=320,
        key="da_research_summary_edit",
        placeholder="「연구노트용 통합 요약」 버튼으로 생성하거나 직접 입력하세요.",
    )
    st.session_state.da_research_summary = edited

    _render_qa(
        documents,
        model=model,
        stage1_model=stage1_model,
        ollama_url=ollama_url,
        use_llm=use_llm,
        knowledge_mode=knowledge_mode,
    )

    st.markdown("---")
    filenames = [r.filename for r in results]
    title = suggest_title(filenames, edited)
    keywords = extract_keywords(results, edited)

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
            st.success("작성 탭으로 전달했습니다. 상단 「연구노트 작성 및 문서 생성」 탭을 여세요.")
            st.balloons()
