"""Product B 편집 로직 Streamlit용 래퍼 — server.py 패턴 재사용."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from services._hwp_path import ensure_hwp_paths


@dataclass
class EditorState:
    filename: str = "document.hwpx"
    file_bytes: Optional[bytes] = None
    ollama_url: str = "http://localhost:11434"
    model: str = "gemma4"
    chat: list[dict] = field(default_factory=list)
    selected_cell: Optional[tuple[int, int, int]] = None
    selected_para: Optional[int] = None

    _editor: Any = field(default=None, repr=False)

    @property
    def editor(self):
        return self._editor

    def load_hwpx(self, file_bytes: bytes, filename: str = "document.hwpx") -> str:
        ensure_hwp_paths()
        from hwp_core.hwpx_editor import HWPXEditor

        self.file_bytes = file_bytes
        self.filename = filename
        self._editor = HWPXEditor(file_bytes)
        self.chat = []
        return ""

    def preview_html(self) -> str:
        if not self._editor:
            return "<p>문서가 없습니다.</p>"
        from hwp_core.editing.preview_layer import build_preview_html

        return build_preview_html(
            self._editor,
            filename=self.filename,
            selected_cell=self.selected_cell,
            selected_para=self.selected_para,
        )

    def get_pending(self) -> list:
        if not self._editor:
            return []
        return self._editor.get_pending_changes()

    def accept_all(self) -> int:
        if not self._editor:
            return 0
        n = len(self.get_pending())
        self._editor.accept_all_pending()
        self.file_bytes = self._editor.save()
        return n

    def reject_all(self) -> int:
        if not self._editor:
            return 0
        n = len(self.get_pending())
        self._editor.reject_all_pending()
        return n

    def accept_one(self, change_id: str) -> bool:
        if not self._editor:
            return False
        ok = self._editor.accept_change(change_id)
        if ok:
            self.file_bytes = self._editor.save()
        return ok

    def reject_one(self, change_id: str) -> bool:
        if not self._editor:
            return False
        return self._editor.reject_change(change_id)

    def export_bytes(self) -> bytes:
        if not self._editor:
            return b""
        self.file_bytes = self._editor.save()
        return self.file_bytes

    def chat_message(self, user_msg: str) -> str:
        """B chat_route + server 핸들러 경로."""
        if not self._editor:
            return "편집 문서를 먼저 불러오거나 생성하세요."
        ensure_hwp_paths()
        from chat_route import decide_chat_route, resolve_search_edit

        has_selection = self.selected_cell is not None or self.selected_para is not None
        decision = decide_chat_route(
            message=user_msg,
            has_selection=has_selection,
            has_editor=True,
            has_docs=True,
        )
        self.chat.append({"role": "user", "content": user_msg})

        reply = self._dispatch(decision, user_msg, resolve_search_edit)
        self.chat.append({"role": "assistant", "content": reply})
        self.file_bytes = self._editor.save() if self._editor else self.file_bytes
        return reply

    def _dispatch(self, decision, user_msg: str, resolve_search_edit) -> str:
        from chat_route import compute_label_total

        action = decision.action
        if action == "fill":
            return self._run_fill(user_msg)
        if action == "rewrite_selection":
            return self._rewrite_selection(user_msg)
        if action == "answer_selection":
            return self._answer_selection(user_msg)
        if action == "explain_pending":
            return self._explain_pending()
        if action == "search_edit":
            resolved = resolve_search_edit(self._editor, user_msg, decision.spec)
            if resolved.action == "propose_replace" and resolved.targets:
                tg = resolved.targets[0]
                new_text = (decision.spec.new if decision.spec else "") or ""
                if tg.kind == "cell" and tg.table_index is not None:
                    self._editor.propose_cell_change(
                        tg.table_index, tg.row, tg.col, new_text, context=tg.label,
                    )
                    return f"제안: {tg.label} → {new_text}"
            return resolved.message or "처리하지 못했습니다."
        if action == "compute_edit":
            label = (decision.spec.label if decision.spec else "") or "합계"
            value, note = compute_label_total(self._editor, label)
            return f"{note}: {value}" if value else note
        if action == "redirect_a":
            return decision.message or "분석 질문은 「문서 분석 및 요약」 탭을 사용하세요."
        if action == "complete_plan":
            return "「완성해줘」는 Flask B 전체 워크스페이스에서 지원합니다. 여기서는 선택 편집·채우기를 사용하세요."
        return decision.message or "문단 또는 표 셀을 선택한 뒤 지시해 주세요."

    def _run_fill(self, command: str) -> str:
        """간소화 Fill — 선택 칸 계산 우선."""
        from cell_ai import (
            extract_literal_cell_value,
            extract_value_from_recent_chat,
        )

        selected = [self.selected_cell] if self.selected_cell else []
        if selected and self._editor:
            literal = extract_literal_cell_value(command)
            if literal:
                t, r, c = selected[0]
                self._editor.propose_cell_change(int(t), int(r), int(c), literal, context=literal)
                return f"선택 칸에 「{literal}」 제안을 올렸습니다."
            from hwp_core.doc_agent.table_calc_fill import try_table_cell_calculation

            t, r, c = selected[0]
            calc = try_table_cell_calculation(self._editor, int(t), int(r), int(c))
            if calc.ok:
                self._editor.propose_cell_change(
                    int(t), int(r), int(c), calc.value, context=calc.formula,
                )
                return f"표 계산 제안: {calc.value} ({calc.formula})"
            chat_val = extract_value_from_recent_chat(self.chat)
            if chat_val:
                self._editor.propose_cell_change(
                    int(t), int(r), int(c), chat_val, context=f"직전 계산: {chat_val}",
                )
                return f"직전 답변 값 「{chat_val}」 제안을 올렸습니다."
        return "채울 빈 칸을 표에서 선택(좌표 입력)하거나, 값을 명시해 주세요. (예: 30,000으로 채워)"

    def _rewrite_selection(self, user_msg: str) -> str:
        from cell_ai import build_cell_prompt, detect_cell_intent
        from hwp_core.llm_client import generate

        if self.selected_cell is not None:
            t, r, c = self.selected_cell
            rows = self._editor.get_table_as_rows(t) or []
            old = rows[r][c] if r < len(rows) and c < len(rows[r]) else ""
            intent = detect_cell_intent(user_msg)
            prompt = build_cell_prompt(
                filename=self.filename, t=t, r=r, c=c, old=old,
                user_msg=user_msg, intent=intent,
            )
            result = generate(prompt, self.model, self.ollama_url, temperature=0.2, num_predict=800)
            if result.get("error"):
                return f"LLM 오류: {result['error']}"
            import json
            import re
            raw = result.get("text") or ""
            m = re.search(r"\{[\s\S]*\}", raw)
            rewritten = old
            if m:
                try:
                    data = json.loads(m.group(0))
                    rewritten = (data.get("rewritten") or old).strip()
                except json.JSONDecodeError:
                    rewritten = raw.strip()[:500]
            self._editor.propose_cell_change(t, r, c, rewritten, context="리라이트")
            return f"셀 수정 제안: {rewritten[:200]}"
        if self.selected_para is not None:
            paras = self._editor.get_paragraphs()
            idx = self.selected_para
            if 0 <= idx < len(paras):
                old = paras[idx]["text"]
                self._editor.propose_paragraph_change(idx, old + " " + user_msg[:100])
                return "문단 수정 제안을 올렸습니다."
        return "셀 또는 문단을 선택해 주세요."

    def _answer_selection(self, user_msg: str) -> str:
        from cell_ai import is_calc_question
        from hwp_core.doc_agent.table_calc_fill import try_table_cell_calculation

        if self.selected_cell and is_calc_question(user_msg):
            t, r, c = self.selected_cell
            calc = try_table_cell_calculation(self._editor, int(t), int(r), int(c))
            if calc.ok:
                self._editor.propose_cell_change(
                    int(t), int(r), int(c), calc.value, context=calc.formula,
                )
                return f"합계는 {calc.value}입니다. 제안을 올렸습니다. ({calc.formula})"
        return "설명 질문은 분석 탭 Q&A를 사용하세요. 편집 탭에서는 수정·채우기 지시를 입력하세요."

    def _explain_pending(self) -> str:
        pending = self.get_pending()
        if not pending:
            return "대기 중인 제안이 없습니다."
        lines = [f"대기 {len(pending)}건:"]
        for ch in pending[:15]:
            lines.append(f"· {ch.location}: 「{ch.old_text[:30]}」→「{ch.new_text[:40]}」")
        return "\n".join(lines)
