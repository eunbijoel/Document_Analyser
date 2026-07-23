"""
Document_Analyser — 통합 Streamlit 앱

탭 1: Product A (Intelligence) 그대로
탭 2: Q&A 요약 → HWPX (Step 2)

"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

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
# brand CSS가 stToolbar 전체를 숨김 → 접힌 사이드바의 펼치기 버튼도 같이 사라짐
# brand가 라이트 색을 !important로 고정 → 다크 테마 시 data-da-theme으로 재정의
st.markdown(
    """
<style>
/* Deploy/상태만 숨기고, 사이드바 펼치기 버튼이 있는 툴바는 유지 */
[data-testid="stToolbar"] {
  display: flex !important;
  visibility: visible !important;
  min-height: 2.5rem;
}
.stAppDeployButton,
div[data-testid="stStatusWidget"],
[data-testid="stToolbarActions"] {
  display: none !important;
}

[data-testid="stSidebarCollapseButton"],
[data-testid="stExpandSidebarButton"] {
  visibility: visible !important;
  display: inline-flex !important;
  opacity: 1 !important;
  pointer-events: auto !important;
}
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stExpandSidebarButton"] {
  cursor: pointer !important;
  min-width: 2rem !important;
  min-height: 2rem !important;
}
[data-testid="stHeader"] {
  z-index: 999991 !important;
}
[data-testid="stExpandSidebarButton"] {
  position: relative;
  z-index: 999992 !important;
  margin: 0.35rem 0 0 0.5rem !important;
}

/* brand가 숨긴 오른쪽 위 ⋮ 메뉴 → 사이드바 하단으로 */
#MainMenu,
[data-testid="stMainMenu"] {
  visibility: visible !important;
}
[data-testid="stMainMenuButton"] {
  visibility: visible !important;
  opacity: 1 !important;
  position: fixed !important;
  left: 0.85rem;
  bottom: 1rem;
  z-index: 1000001 !important;
  width: 2.35rem !important;
  height: 2.35rem !important;
  border-radius: 8px !important;
  background: #ffffff !important;
  border: 1px solid #d5d8e0 !important;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08) !important;
}
[data-testid="stMainMenuButton"]:hover {
  background: #f3f4f7 !important;
}
body:has([data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stMainMenuButton"] {
  left: 0.85rem;
  bottom: 1rem;
}

/* Streamlit 1.57+ primary */
button[data-testid="stBaseButton-primary"],
.stButton > button[data-testid="stBaseButton-primary"],
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
  background-color: #1f4b99 !important;
  background-image: none !important;
  border-color: #1f4b99 !important;
  color: #ffffff !important;
}
button[data-testid="stBaseButton-primary"]:hover,
.stButton > button[data-testid="stBaseButton-primary"]:hover,
.stButton > button[kind="primary"]:hover {
  background-color: #183a78 !important;
  border-color: #183a78 !important;
  color: #ffffff !important;
}

/* ----- Dark theme overrides (brand CSS가 라이트를 강제해서 부분만 바뀌던 문제) ----- */
[data-testid="stApp"][data-da-theme="dark"] {
  --bg: #0e1117 !important;
  --paper: #262730 !important;
  --ink: #fafafa !important;
  --muted: #a3a8b4 !important;
  --line: #3d4450 !important;
  --accent: #6b9eff !important;
  --accent-soft: #1a2740 !important;
  --ok: #3dd68c !important;
  --ok-soft: #143529 !important;
  --warn: #f0b429 !important;
  --warn-soft: #3a2e14 !important;
  --danger: #ff6b6b !important;
  --shadow: 0 1px 2px rgba(0,0,0,.35), 0 12px 32px rgba(0,0,0,.35) !important;
  color: var(--ink) !important;
  background: var(--bg) !important;
}
[data-testid="stApp"][data-da-theme="dark"],
[data-testid="stApp"][data-da-theme="dark"] [data-testid="stAppViewContainer"],
[data-testid="stApp"][data-da-theme="dark"] [data-testid="stMain"],
[data-testid="stApp"][data-da-theme="dark"] section.main,
[data-testid="stApp"][data-da-theme="dark"] [data-testid="stMainBlockContainer"] {
  background: var(--bg) !important;
  color: var(--ink) !important;
}
[data-testid="stApp"][data-da-theme="dark"] [data-testid="stSidebar"] {
  background: #161b22 !important;
  border-right-color: var(--line) !important;
}
[data-testid="stApp"][data-da-theme="dark"] [data-testid="stSidebar"] > div:first-child {
  background: #161b22 !important;
}
[data-testid="stApp"][data-da-theme="dark"] .hx-topbar {
  background: #1c2330 !important;
  border-color: var(--line) !important;
}
[data-testid="stApp"][data-da-theme="dark"] .stMarkdown,
[data-testid="stApp"][data-da-theme="dark"] .stMarkdown p,
[data-testid="stApp"][data-da-theme="dark"] .stCaption,
[data-testid="stApp"][data-da-theme="dark"] label,
[data-testid="stApp"][data-da-theme="dark"] [data-testid="stWidgetLabel"],
[data-testid="stApp"][data-da-theme="dark"] h1,
[data-testid="stApp"][data-da-theme="dark"] h2,
[data-testid="stApp"][data-da-theme="dark"] h3 {
  color: var(--ink) !important;
}
[data-testid="stApp"][data-da-theme="dark"] .stButton > button {
  background: #262730 !important;
  color: var(--ink) !important;
  border-color: var(--line) !important;
}
[data-testid="stApp"][data-da-theme="dark"] button[data-testid="stBaseButton-primary"],
[data-testid="stApp"][data-da-theme="dark"] .stButton > button[data-testid="stBaseButton-primary"],
[data-testid="stApp"][data-da-theme="dark"] .stButton > button[kind="primary"] {
  background-color: #3d6fd4 !important;
  border-color: #3d6fd4 !important;
  color: #ffffff !important;
}
[data-testid="stApp"][data-da-theme="dark"] [data-testid="stMainMenuButton"] {
  background: #262730 !important;
  border-color: var(--line) !important;
  color: var(--ink) !important;
}
[data-testid="stApp"][data-da-theme="dark"] [data-testid="stMainMenuButton"]:hover {
  background: #323846 !important;
}
[data-testid="stApp"][data-da-theme="dark"] [data-testid="stSidebar"] .stCheckbox,
[data-testid="stApp"][data-da-theme="dark"] [data-testid="stSidebar"] .stExpander,
[data-testid="stApp"][data-da-theme="dark"] div[data-testid="stFileUploaderDropzone"] {
  background: #262730 !important;
  border-color: var(--line) !important;
}
[data-testid="stApp"][data-da-theme="dark"] .hx-kpi {
  background: var(--paper) !important;
  border-color: var(--line) !important;
}
[data-testid="stApp"][data-da-theme="dark"] .hx-next {
  background: var(--accent-soft) !important;
  border-color: #2a3f66 !important;
  color: #c9dcff !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# Streamlit 다크 전환을 data-da-theme 속성으로 동기화 (brand 라이트 고정 CSS 우회)
components.html(
    """
<script>
(() => {
  const doc = window.parent.document;
  const sync = () => {
    const app = doc.querySelector('[data-testid="stApp"]');
    if (!app) return;
    const dark = getComputedStyle(app).colorScheme === 'dark';
    const next = dark ? 'dark' : 'light';
    if (app.getAttribute('data-da-theme') !== next) {
      app.setAttribute('data-da-theme', next);
    }
  };
  sync();
  const obs = new MutationObserver(sync);
  obs.observe(doc.documentElement, { subtree: true, attributes: true, childList: true });
  setInterval(sync, 400);
})();
</script>
""",
    height=0,
)

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
