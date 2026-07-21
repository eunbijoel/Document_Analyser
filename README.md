# Document Analyser

A와 B(HWP analysis)를 **한 Streamlit 앱·두 탭**으로 연결합니다. 기존 `/home/eunbi/HWP analysis` 코드는 수정하지 않고 `hwp_core` 등을 재사용합니다.

## 실행

```bash
cd /home/eunbi/Document_Analyser
chmod +x run_app.sh
./run_app.sh
```

브라우저: http://127.0.0.1:8502 (포트는 `PORT` 환경변수로 변경)

### 사전 조건

- Python 3.10+
- `pip install -r requirements.txt`
- HWP analysis repo: `/home/eunbi/HWP analysis` (또는 `HWP_ANALYSIS_ROOT`)
- (선택) Ollama — LLM 요약·Q&A

## 탭 구성

| 탭 | 기능 |
|----|------|
| **문서 분석 및 요약** | HWP/HWPX/PDF/TXT/PY 업로드, 추출, Q&A, 20줄 연구노트 요약, 작성 탭으로 가져오기 |
| **연구노트 작성 및 문서 생성** | 분석 결과 불러오기, 필드 편집, HWPX 생성, 미리보기·AI 편집·다운로드 |

탭 간 데이터는 `st.session_state` (`analysis_summary`, `research_note_fields` 등).

## 폴더 구조

```
Document_Analyser/
├── app.py
├── tabs/analyzer_tab.py, writer_tab.py
├── services/document_parser.py, summarizer.py, session_bridge.py,
│         hwp_generator.py, editor_service.py
├── templates/
├── tests/
├── run_app.sh
└── INTEGRATION_DESIGN.md
```

## 구현 완료

- 다형식 파싱 (HWP/HWPX/PDF/TXT/PY)
- A `QAEngine` + knowledge mode Q&A
- 연구노트 20줄 통합 요약 (LLM + 규칙 fallback)
- session_state 브릿지
- 연구노트 HWPX 생성 (`make_minimal_hwpx`)
- B 편집: 미리보기, propose/accept, 채팅 편집, 표 계산·채우기 (간소 UI)

## 제한 사항

- **B 전체 UX** (클릭 선택, 멀티 문서 워크스페이스, Completion Planner, Evidence Fill 전체)는 Flask `HWP_v2/server.py` (:8765) 사용 권장 — 작성 탭 하단 안내
- HWP 업로드는 `convert_hwp` (hwpilot/LibreOffice) 필요할 수 있음
- `templates/research_note_template.hwpx`가 비어 있으면 최소 HWPX 코드 생성 사용

## 테스트

```bash
cd /home/eunbi/Document_Analyser
PYTHONPATH=.:/home/eunbi/HWP\ analysis pytest tests/ -q
```

## 시나리오

1. PDF+TXT 업로드 → 통합 요약 → 작성 탭 가져오기 → HWPX 생성 → 다운로드  
2. PY+문서 업로드 → Q&A → 요약에 문제점/향후 계획 확인  
3. 작성 탭에서 기존 HWPX 업로드 → 편집 채팅  
4. 분석 탭 Q&A + 지식 모드 전환
