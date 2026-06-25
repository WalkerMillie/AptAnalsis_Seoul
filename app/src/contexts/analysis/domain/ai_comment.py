"""[HAND-WRITTEN] AI 코멘트 도메인 — 순수(프롬프트 빌드 + 응답 파싱).

§2: I/O 없음. LLM 호출은 어댑터(llm_cli) 책임. 여기선 '무엇을 묻고, 응답을 어떻게 신뢰하는가'만.
우리가 RS 4분면·전세가율을 이미 계산해 넘기므로 LLM은 '예측'이 아니라 '해설'만 한다(환각 최소화).
"""

from __future__ import annotations

import json

# 페르소나·가드레일. 거시는 방향만(수치 단정 금지), 원인은 '가능성'으로만.
SYSTEM_PROMPT = (
    "너는 서울 아파트 실거래 데이터를 해설하는 차분한 분석가다.\n"
    "규칙:\n"
    "- 제공된 수치만 사용한다. 없는 정보(세대수·학군·재건축 연한·정확한 금리 수치 등)는 절대 지어내지 않는다.\n"
    "- 미래 가격이나 상승률을 예측하지 않는다. 매수·매도를 권유하지 않는다(데이터 해석만).\n"
    "- 상승/하락의 원인은 단정하지 말고 '~일 수 있다'는 가능성으로만 제시한다.\n"
    "- 거시 환경(금리 국면 등)은 일반적 방향만 가볍게 언급할 수 있으나 구체 수치는 단정하지 않는다.\n"
    "- 담백한 한국어. 과장·감탄사·이모지 금지. 투자 조언이 아님을 전제로 한다.\n"
    "- 반드시 아래 JSON 객체 하나만 출력한다(다른 설명·코드펜스 금지):\n"
    '  {"headline":"20자 이내 한 줄 요약","reading":"2~3문장 해석","caution":"1문장 유의점"}'
)


def _eok(won: float | None) -> str:
    if won is None:
        return "정보 없음"
    return f"{won / 1e8:.1f}억"


def _pct(x: float | None) -> str:
    if x is None:
        return "정보 없음"
    return f"{'+' if x >= 0 else ''}{x * 100:.1f}%"


def build_payload(ctx: dict) -> str:
    """FE가 넘긴 계산값을 LLM이 읽을 한국어 컨텍스트로 직렬화(우리 판정 포함)."""
    g = ctx.get("growth")
    dong_g = ctx.get("dong_growth")
    rs = (g - dong_g) if (g is not None and dong_g is not None) else None
    lines = [
        f"단지: {ctx.get('complex_name', '-')}",
        f"위치: {ctx.get('gu', '-')} {ctx.get('dong', '-')}",
        f"분석기간: 최근 {ctx.get('months', '-')}개월",
        f"단지 상승률: {_pct(g)}",
        f"동 중앙값 상승률: {_pct(dong_g)}",
        f"구 중앙값 상승률: {_pct(ctx.get('gu_growth'))}",
        f"지역 대비 상대강도(단지−동): {_pct(rs)}",
        f"우리 판정(4분면): {ctx.get('verdict_label', '-')}",
    ]
    jr = ctx.get("jeonse_ratio")
    if jr is not None:
        lines.append(f"전세가율: {_pct(jr)}")
    if ctx.get("recent_price") is not None:
        lines.append(f"최근 실거래가: {_eok(ctx.get('recent_price'))}")
    if ctx.get("area_py"):
        lines.append(f"평형: {ctx['area_py']}")
    if ctx.get("build_year"):
        lines.append(f"건축년도: {ctx['build_year']}년")
    if ctx.get("confidence_tier"):
        lines.append(f"데이터 신뢰도: {ctx['confidence_tier']}")
    if ctx.get("window_trades") is not None:
        lines.append(f"표본 거래수: {ctx['window_trades']}건")
    return (
        "다음 단지의 실거래 추세를 위 규칙에 맞게 해설해줘.\n\n"
        + "\n".join(lines)
    )


def parse_comment(raw: str) -> dict:
    """LLM 원문에서 JSON 객체를 추출·검증. 실패 시 ValueError(서비스가 친절 메시지로 변환)."""
    if not raw or not raw.strip():
        raise ValueError("빈 응답")
    s = raw.strip()
    # 코드펜스/잡텍스트 제거 — 첫 '{' ~ 마지막 '}' 구간만.
    start, end = s.find("{"), s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("JSON 객체를 찾을 수 없음")
    obj = json.loads(s[start : end + 1])
    out = {}
    for k in ("headline", "reading", "caution"):
        v = obj.get(k)
        if not isinstance(v, str) or not v.strip():
            raise ValueError(f"필드 누락/형식 오류: {k}")
        out[k] = v.strip()
    return out
