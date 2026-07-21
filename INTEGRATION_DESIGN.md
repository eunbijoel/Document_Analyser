# Document_Analyser 통합 설계

## A 프로젝트 구조 (HWP analysis — Product A)

| 경로 | 역할 |
|------|------|
| `apps/intelligence/app.py` | Streamlit 진입점 (분석·Q&A) |
| `ui/brand.py`, `ui/review_home.py`, `ui/issue_panel.py` | UI |
| `hwp_core/hwp_parser.py` | HWP/HWPX 파싱 |
| `hwp_core/qa_engine.py` | 문서 Q&A |
| `hwp_core/knowledge_mode.py` | 문서/일반지식 모드 |
| `hwp_core/intel_pipeline.py` | 검토·이슈 |
| `additional/reference_parser.py` | PDF/TXT/DOCX 등 참고 파서 |

실행: `streamlit run apps/intelligence/app.py` (repo: `/home/eunbi/HWP analysis`)

## B 프로젝트 구조 (HWP_v2 — Product B)

| 경로 | 역할 |
|------|------|
| `HWP_v2/server.py` | Flask 세션·API·채팅 디스패치 |
| `HWP_v2/chat_route.py` | Rewrite/Fill/Update/Explain 라우팅 |
| `HWP_v2/cell_ai.py` | 선택 셀 리라이트 |
| `hwp_core/hwpx_editor.py` | propose/accept/export |
| `hwp_core/doc_agent/*` | Fill·표 계산 |
| `hwp_core/editing/preview_layer.py` | 편집 미리보기 HTML |

실행: `python3 HWP_v2/server.py` → `:8765`

## 재사용할 파일 (수정 없이 import)

- `hwp_core/*` 전체 (파서, QA, HWPX 편집, Fill, preview)
- `additional/reference_parser.py` (PDF/TXT)
- `ui/brand.py` (선택적 테마)
- `HWP_v2/chat_route.py`, `cell_ai.py`, `workspace_docs.py` (편집 서비스)
- `hwp_core/doc_agent/fixtures.make_minimal_hwpx` (HWPX 생성)

## 새로 만들 파일

```
Document_Analyser/
├── app.py
├── tabs/analyzer_tab.py, writer_tab.py
├── services/document_parser.py, summarizer.py, session_bridge.py,
│         hwp_generator.py, editor_service.py
├── templates/ (placeholder — HWPX는 코드 생성)
├── requirements.txt, run_app.sh, README.md
└── tests/test_session_bridge.py, test_hwp_generator.py
```

## 충돌 가능성

| 항목 | 대응 |
|------|------|
| `sys.path` | `HWP_ANALYSIS_ROOT` 환경변수로 repo 루트 주입 |
| Streamlit vs Flask 세션 | B Flask 세션 대신 `st.session_state` + `EditorService` |
| B 클릭 선택 UX | Streamlit 탭에서는 셀 좌표 입력 + iframe 미리보기; 고급 편집은 B iframe 옵션 |
| A 업로드 형식 | A는 HWP만; 통합 앱은 PDF/TXT/PY 추가 (`reference_parser` + PY) |
| Ollama 설정 | sidebar 단일 설정을 두 탭 공유 |

## 통합 작업 순서 (완료 기준)

1. ✅ 구조 분석 및 설계 문서
2. ✅ `Document_Analyser` 디렉토리 생성
3. ✅ services 모듈 (파서·요약·브릿지·HWPX 생성·편집)
4. ✅ 탭 1 — 분석·Q&A·연구노트 요약·가져오기
5. ✅ 탭 2 — 불러오기·양식·HWPX 생성·편집·다운로드
6. ✅ session_state 브릿지
7. README / run_app.sh / 테스트
