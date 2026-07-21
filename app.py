"""
Document_Analyser — 통합 Streamlit 앱

탭 1: Product A (Intelligence) 그대로
탭 2: Q&A 요약 → HWPX (Step 2)

실행:
  cd /home/eunbi/Document_Analyser && PORT=8503 ./run_app.sh
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_DA = Path(__file__).resolve().parent
if str(_DA) not in sys.path:
    sys.path.insert(0, str(_DA))

try:
    from services._hwp_path import ensure_hwp_paths

    ensure_hwp_paths()
    from hwp_core.knowledge_mode import DEFAULT_KNOWLEDGE_MODE
    from hwp_core.llm_client import check_ollama_status
    from ui.brand import inject_theme
except Exception as _boot_err:
    st.error(f"초기화 오류: {_boot_err}")
    st.stop()

from tabs.intelligence_tab import render_intelligence_tab_embedded
from tabs.writer_tab import render_writer_tab

st.set_page_config(
    page_title="Document Analyser",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_theme()

st.title("Document Analyser")
st.caption("탭 1 = Product A · 탭 2 = 요약 → HWPX (단계별 구현)")

with st.sidebar:
    st.markdown("### 연결")
    ollama_url = st.text_input("Ollama URL", value="http://localhost:11434", key="da_ollama_url")
    status = check_ollama_status(ollama_url)
    use_llm = status.get("status") == "running"
    if use_llm:
        models = status.get("models") or ["gemma4"]
        gemma4_first = [m for m in models if "gemma4" in m] + [m for m in models if "gemma4" not in m]
        model = st.selectbox("모델", gemma4_first, index=0, key="da_model")
    else:
        st.warning("Ollama 미연결 — 규칙 검토만 사용")
        model = "gemma4"
        st.session_state["da_model"] = model

tab_analyze, tab_write = st.tabs([
    "문서 분석 및 요약",
    "연구노트 작성 및 문서 생성",
])

with tab_analyze:
    try:
        render_intelligence_tab_embedded(
            model=model,
            ollama_url=ollama_url,
            use_llm=use_llm,
            knowledge_mode=DEFAULT_KNOWLEDGE_MODE,
        )
    except Exception as e:
        st.error(f"분석 탭 오류: {e}")
        st.exception(e)

with tab_write:
    try:
        render_writer_tab()
    except Exception as e:
        st.error(f"작성 탭 오류: {e}")
