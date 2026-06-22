"""[GENERATED 골격] LeverageROE — 무상태 calculation (순수 함수). I/O·상태 없음.

각 수식을 아래 impl 슬롯에 순수 함수로 구현한다(시그니처는 자유). 분기 규칙이 필요하면 결정표로 뺀다.
"""

from __future__ import annotations

# >>> impl: editable — AN-F02: 순익 = 매매가 × 가정상승률 − 대출액 × 실효금리
def an_f02(purchase_price: float, assumed_growth: float,
           loan_amount: float, effective_rate: float) -> float:
    """세전 순익(원) = 매매가 × 가정상승률 − 대출액 × 실효금리.

    상승분(자본이득)에서 1년치 이자비용을 뺀 값. 금액=원, 비율=소수.
    예) 1e9×0.05 − 6e8×0.05 = 5e7 − 3e7 = 2e7 (2,000만원).
    """
    capital_gain = purchase_price * assumed_growth
    interest_cost = loan_amount * effective_rate
    return capital_gain - interest_cost
# <<< impl

# >>> impl: editable — AN-F03: ROE = 순익 / 자기자본
def roe(net_profit: float, equity: float) -> float:
    """레버리지 ROE(소수) = 순익 / 자기자본.

    예) 순익 2e7 / 자기자본 4e8 → 0.05 (5%).
    """
    if equity <= 0:
        raise ValueError("equity must be > 0")
    return net_profit / equity
# <<< impl

