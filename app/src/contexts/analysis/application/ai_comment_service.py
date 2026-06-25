"""[HAND-WRITTEN] AI 코멘트 유스케이스 — 프롬프트 빌드(도메인) + LLM 호출(주입) + 파싱(도메인).

핵심: 어떤 실패도 예외로 새지 않는다 → 항상 AICommentResult(ok=False, ...) 로 흡수.
뷰는 이걸 200으로 내려 FE가 '지금은 어렵다'를 부드럽게 노출(500·행 없음).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from contexts.analysis.domain.ai_comment import (
    SYSTEM_PROMPT,
    build_payload,
    parse_comment,
)

log = logging.getLogger(__name__)

_FRIENDLY = "지금은 AI 코멘트를 만들기 어려워요. 잠시 후 다시 시도해 주세요."


@dataclass(frozen=True)
class AICommentResult:
    ok: bool
    headline: str = ""
    reading: str = ""
    caution: str = ""
    message: str = ""   # ok=False일 때 FE 노출용 친절 메시지


class AICommentService:
    """LLM 클라이언트(generate(system, user)->str)를 주입받아 조율만 한다."""

    def __init__(self, llm_client):
        self._llm = llm_client

    def comment(self, ctx: dict) -> AICommentResult:
        try:
            user = build_payload(ctx)
            raw = self._llm.generate(SYSTEM_PROMPT, user)
            parsed = parse_comment(raw)
        except Exception as e:  # noqa: BLE001 — 의도적 광역 흡수(절대 새지 않음)
            log.warning("AI 코멘트 생성 실패: %s", e, exc_info=True)
            return AICommentResult(ok=False, message=_FRIENDLY)
        return AICommentResult(ok=True, **parsed)
