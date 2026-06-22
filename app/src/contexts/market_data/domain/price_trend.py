"""[HAND-WRITTEN] 실거래 가격추세 — 무상태 calculation (순수 함수). I/O·상태 없음.

수집한 실거래에서 '단지가 측정 기간 동안 몇 % 올랐나'를 산출한다(㎡당가 기준).
판정 규칙은 없다 — 숫자만 낸다. 표본/윈도우/평형 집계는 application에서.

설계 교훈(실측으로 폐기한 것): 짧은 구간을 연환산(×12÷간격)하면 ㎡당가 노이즈가 폭증한다
(2개월 +10%→연 77~24000%). 그래서 연환산을 버리고 '기간 상승률'(period_change)만 쓴다.
평형 믹스 왜곡은 application에서 같은 전용(밴드)끼리만 비교해 제거한다.
"""

from __future__ import annotations


def confidence_score(n_total: int, months_covered: int, min_endpoint: int) -> float:
    """표본 신뢰도(0~1) = 총거래·커버개월·약한쪽 끝구간 거래수의 가중 결합.

    상승률 '절대값'과 함께 보여주는 신뢰도. 셋 다 클수록 1에 가깝다(각 상한에서 만점).
    - 총거래 30건, 커버 8개월, 양끝 약한쪽 8건이면 해당 항목 만점.
    가중치는 끝점 견고성(min_endpoint)·총량(n_total)을 커버리지보다 약간 더 본다.
    """
    t = min(1.0, n_total / 30.0)
    m = min(1.0, months_covered / 8.0)
    e = min(1.0, min_endpoint / 8.0)
    return 0.4 * t + 0.25 * m + 0.35 * e


def period_change(early_ppm2: float, late_ppm2: float) -> float:
    """기간 상승률(소수) = 끝 구간/첫 구간 − 1. 측정 윈도우(개월) 동안의 실제 변화.

    연 단위로 확대(연환산)하지 않는다 — 짧은 구간을 12로 나눠 과장하는 폭주를 피하기 위함.
    12개월 윈도우면 사실상 연간 상승률과 같다. 하락이면 음수.
    """
    if early_ppm2 <= 0:
        raise ValueError("early_ppm2 must be > 0")
    return late_ppm2 / early_ppm2 - 1.0
