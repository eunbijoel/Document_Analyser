# Document Analyser

A와 B(HWP analysis)를 **한 Streamlit 앱·두 탭**으로 연결합니다. 기존 `/home/eunbi/HWP analysis` 코드는 수정하지 않고 `hwp_core` 등을 재사용합니다.

## 실행

```bash
cd /home/eunbi/Document_Analyser
PORT=8503 ./run_app.sh
```

브라우저: http://127.0.0.1:8503 (포트는 `PORT` 환경변수로 변경)

### 사전 조건

- Python 3.10+
- `pip install -r requirements.txt` (`python-hwpx` 포함)
- HWP analysis repo: `/home/eunbi/HWP analysis` (또는 `HWP_ANALYSIS_ROOT`)
- (선택) Ollama — LLM 요약·Q&A

## 탭 구성

| 탭 | 기능 |
|----|------|
| **문서 분석 및 요약** | Product A Q&A + 다형식 업로드(HWP/HWPX/PDF/TXT/PY/XLSX/XLS/CSV), 요약 → 작성 탭 전달 |
| **연구노트 작성 및 문서 생성** | 요약문 직접 편집·미리보기, HWPX/DOCX 다운로드 (한글에서 열림) |

탭 간 데이터는 `st.session_state` (`da_summary_text`, `analysis_summary` 등).

## 폴더 구조

```
Document_Analyser/
├── app.py
├── tabs/intelligence_tab.py, writer_tab.py
├── services/document_parser.py, text_hwpx_builder.py, editor_service.py, …
├── templates/
├── tests/
└── run_app.sh
```

## 구현 완료

- Product A Intelligence UI 재사용 + 다형식 파싱
- 짧은 요약 / 20줄 연구노트 요약 / Q&A → 작성 탭
- 탭 2: 요약 편집 + 미리보기 + HWPX(`python-hwpx`) / DOCX 다운로드

## 제한 사항

- `.hwp` 바이너리 직접 생성은 한글 호환이 불안정 → DOCX 제공 후 한글에서 HWP로 저장 권장
- B 전체 UX(클릭 선택·Completion Planner 등)는 Flask `HWP_v2/server.py` (:8765)

## 테스트

```bash
cd /home/eunbi/Document_Analyser
PYTHONPATH=.:/home/eunbi/HWP\ analysis pytest tests/ -q
```
