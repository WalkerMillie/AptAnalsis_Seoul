"""[GENERATED 골격] BreakevenCalc — 무상태 calculation (순수 함수). I/O·상태 없음.

각 수식을 아래 impl 슬롯에 순수 함수로 구현한다(시그니처는 자유). 분기 규칙이 필요하면 결정표로 뺀다.
"""

from __future__ import annotations

# >>> impl: editable — AN-F01: 손익분기 상승률 = 대출비중 × 실효금리
def an_f01(loan_amount: float, purchase_price: float, effective_rate: float) -> float:
    """손익분기 상승률(연, 소수) = 대출비중 × 실효금리.

    이자비용을 매매가 상승분으로 메우려면 집값이 연 몇 % 올라야 본전인가.
    금액 단위는 원, 금리/결과는 소수(0.05 == 5%).
    예) 대출 6e8 / 매매 1e9(비중 0.6) × 0.05 → 0.03 (연 3%).
    """
    if purchase_price <= 0:
        raise ValueError("purchase_price must be > 0")
    loan_ratio = loan_amount / purchase_price
    return loan_ratio * effective_rate
# <<< impl

