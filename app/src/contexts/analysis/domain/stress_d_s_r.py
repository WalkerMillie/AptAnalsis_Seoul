"""[GENERATED 골격] StressDSR — 무상태 calculation (순수 함수). I/O·상태 없음.

각 수식을 아래 impl 슬롯에 순수 함수로 구현한다(시그니처는 자유). 분기 규칙이 필요하면 결정표로 뺀다.
"""

from __future__ import annotations

# >>> impl: editable — AN-F04: 스트레스 금리 = 실효금리 + 3.0%p (DSR 3.0 스트레스 버퍼 가산)
# 버퍼는 규제값이라 자주 바뀐다(기획서 §5.3) → 코드 상수가 아닌 인자(설정값)로 분리.
STRESS_DSR_BUFFER = 0.03  # 2026 스트레스 DSR 3.0%p 기본값. 운영에선 config로 주입.


def an_f04(effective_rate: float, buffer: float = STRESS_DSR_BUFFER) -> float:
    """스트레스 금리(소수) = 실효금리 + 스트레스 버퍼(기본 3.0%p).

    대출 한도 심사용으로 실제 금리에 버퍼를 얹는다. 예) 0.05 + 0.03 → 0.08.
    """
    if effective_rate < 0 or buffer < 0:
        raise ValueError("rate/buffer must be >= 0")
    return effective_rate + buffer
# <<< impl

