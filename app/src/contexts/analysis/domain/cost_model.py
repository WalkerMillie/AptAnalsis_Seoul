"""[HAND-WRITTEN] 매매 총비용·총수익 모델 — 무상태 calculation (순수 함수). I/O·상태 없음.

기존 손익분기(an_f01)는 '이자만' 메우는 약한 모델이었다. 여기서는 실제 의사결정에 필요한
거래·보유·청산 비용을 모두 반영한 '총비용 손익분기'와 순익/ROE를 계산한다.

반영 비용: 취득세(+교육세 근사, 다주택 중과) · 매수/매도 중개보수 · 보유세(근사) · 대출이자
           · 양도소득세(1세대1주택 12억 초과분 안분 과세 + 보유/거주 장특공) · 자기자본 기회비용.
금액=원, 비율=소수.

정책값(세율·요율)은 tax_policy.py 결정표에 단일 출처로 분리했다(법 개정 시 거기만 수정).
거주연수는 별도 입력이 없어 1주택은 실거주(거주연수=보유연수)로 근사한다 — 명시한 근사.
"""

from __future__ import annotations

from contexts.analysis.domain import tax_policy as T

_EOK = T.EOK


# ── 취득세 ──
def acquisition_tax_rate(price: float, *, is_first_home: bool = True) -> float:
    """실효 취득세율(소수). 1주택은 6억↓1%/6~9억 선형/9억↑3% (+지방교육세 ×1.1).

    다주택(is_first_home=False)은 중과 근사율을 그대로 쓴다. 농특세(전용85㎡초과)는 면적
    미입력이라 제외.
    """
    if not is_first_home:
        return T.ACQ_MULTI_HOME
    eok = price / _EOK
    if eok <= T.ACQ_1HOME_LOW_EOK:
        base = T.ACQ_1HOME_LOW
    elif eok <= T.ACQ_1HOME_HIGH_EOK:
        span = T.ACQ_1HOME_HIGH_EOK - T.ACQ_1HOME_LOW_EOK
        base = T.ACQ_1HOME_LOW + (eok - T.ACQ_1HOME_LOW_EOK) * (
            (T.ACQ_1HOME_HIGH - T.ACQ_1HOME_LOW) / span)
    else:
        base = T.ACQ_1HOME_HIGH
    return base * T.ACQ_EDU_SURTAX


# ── 중개보수 ──
def brokerage_rate(price: float) -> float:
    """매매 중개보수 상한요율(소수). 구간표 첫 매칭."""
    eok = price / _EOK
    for upper, rate in T.BROKERAGE_TABLE:
        if eok < upper:
            return rate
    return T.BROKERAGE_TABLE[-1][1]


# ── 보유세 ──
def annual_holding_tax(price: float) -> float:
    """연간 보유세(원) 근사 = 매매가 × 구간 실효율."""
    eok = price / _EOK
    for upper, rate in T.HOLDING_TAX_TABLE:
        if eok <= upper:
            return price * rate
    return price * T.HOLDING_TAX_TABLE[-1][1]


# ── 양도소득세 ──
def _progressive_cgt(base: float) -> float:
    """과세표준 → 누진 산출세액(지방소득세 제외)."""
    if base <= 0:
        return 0.0
    tax, lo = 0.0, 0.0
    for hi, rate in T.CGT_BRACKETS:
        if base > hi:
            tax += (hi - lo) * rate
            lo = hi
        else:
            tax += (base - lo) * rate
            break
    return tax


def taxable_fraction(sale_price: float, holding_years: float, *, is_first_home: bool) -> float:
    """과세 대상 양도차익 비율(소수).

    1세대1주택(보유 2년+): 12억 이하 전액 비과세(0), 12억 초과 시 (양도가−12억)/양도가 안분.
    그 외(다주택·단기보유): 전액 과세(1.0).  → 12억 경계에서 연속(절벽 제거).
    """
    if is_first_home and holding_years >= T.ONE_HOME_MIN_HOLD:
        if sale_price <= T.HIGH_PRICE_THRESHOLD:
            return 0.0
        return (sale_price - T.HIGH_PRICE_THRESHOLD) / sale_price
    return 1.0


def _ltd_rate(holding_years: float, *, is_first_home: bool) -> float:
    """장기보유특별공제율(소수). 1주택=보유+거주(거주=보유 근사) 우대, 그 외=일반."""
    if holding_years < T.LTD_MIN_HOLD:
        return 0.0
    if is_first_home:
        per_dim = min(T.LTD_1HOME_MAX_EACH, holding_years * T.LTD_1HOME_PER_YEAR)
        return min(T.LTD_1HOME_MAX_TOTAL, per_dim * 2)   # 보유분 + 거주분
    return min(T.LTD_GENERAL_MAX, holding_years * T.LTD_GENERAL_PER_YEAR)


def capital_gains_tax(gain: float, sale_price: float, holding_years: float,
                      *, is_first_home: bool) -> float:
    """양도소득세 근사(원). 12억 초과분 안분 과세 + 장특공 + 기본공제 + 지방소득세."""
    if gain <= 0:
        return 0.0
    frac = taxable_fraction(sale_price, holding_years, is_first_home=is_first_home)
    if frac <= 0:
        return 0.0
    taxable_gain = gain * frac
    ltd = _ltd_rate(holding_years, is_first_home=is_first_home)
    base = taxable_gain * (1 - ltd) - T.CGT_BASIC_DEDUCTION
    return _progressive_cgt(base) * T.CGT_LOCAL_SURTAX


def _fully_exempt(sale_price: float, holding_years: float, *, is_first_home: bool) -> bool:
    """1세대1주택 '전액' 비과세 여부(12억 이하·2년+) — 표시용 플래그."""
    return bool(is_first_home and holding_years >= T.ONE_HOME_MIN_HOLD
                and sale_price <= T.HIGH_PRICE_THRESHOLD)


# ── 거주가치(자가 거주효용) ──
def residence_value_annual(purchase_price: float, jeonse_ratio: float,
                           conversion_rate: float = T.RENT_CONVERSION_RATE) -> float:
    """자가 거주의 연 거주가치(원) = 전세보증금 × 전월세전환율.

    "이 집에 전세로 살았다면 묶였을 보증금의 기회비용" = 자가가 점유로 누리는 임대 서비스.
    전세보증금 ≈ 매매가 × 전세가율. 자택(실거주) 손익에 더해야 현실적 판정이 된다.
    """
    if jeonse_ratio <= 0:
        return 0.0
    return purchase_price * jeonse_ratio * conversion_rate


def total_net_profit(*, purchase_price: float, loan_amount: float, equity: float,
                     effective_rate: float, growth: float, holding_years: float,
                     opportunity_rate: float, is_first_home: bool,
                     jeonse_ratio: float = 0.0,
                     conversion_rate: float = T.RENT_CONVERSION_RATE) -> dict:
    """보유기간 H년·연상승률 growth 가정 시 모든 비용 차감 순익(원)과 비용 내역.

    매도가 S = 매매가 × (1+growth)^H (복리). 순익 = 자본이득 − 모든비용 + 거주가치.
    ROE 분모 = 투입 자기자본(equity + 취득부대비용).
    jeonse_ratio>0이면 자가 거주효용(거주가치)을 순익에 더한다(실거주 관점). 0이면 순수 투자.
    """
    P, L, H = purchase_price, loan_amount, holding_years
    buy_tax = P * acquisition_tax_rate(P, is_first_home=is_first_home)
    buy_fee = P * brokerage_rate(P)
    sale = P * (1 + growth) ** H
    gain = sale - P
    sell_fee = sale * brokerage_rate(sale)
    cgt = capital_gains_tax(gain, sale, H, is_first_home=is_first_home)
    interest = L * effective_rate * H
    holding_tax = annual_holding_tax(P) * H
    invested = equity + buy_tax + buy_fee
    opportunity = invested * opportunity_rate * H
    residence = residence_value_annual(P, jeonse_ratio, conversion_rate) * H
    net = (gain - buy_tax - buy_fee - sell_fee - cgt - interest - holding_tax
           - opportunity + residence)
    return {
        "net_profit": net,
        "sale_price": sale,
        "capital_gain": gain,
        "invested_equity": invested,
        "roe": net / invested if invested > 0 else 0.0,
        "first_home_exempt": _fully_exempt(sale, H, is_first_home=is_first_home),
        "residence_value": residence,
        "costs": {
            "acquisition_tax": buy_tax,
            "buy_brokerage": buy_fee,
            "sell_brokerage": sell_fee,
            "capital_gains_tax": cgt,
            "interest": interest,
            "holding_tax": holding_tax,
            "opportunity_cost": opportunity,
        },
    }


def breakeven_growth(*, purchase_price: float, loan_amount: float, equity: float,
                     effective_rate: float, holding_years: float,
                     opportunity_rate: float, is_first_home: bool,
                     jeonse_ratio: float = 0.0,
                     conversion_rate: float = T.RENT_CONVERSION_RATE) -> float:
    """순익=0 이 되는 연상승률(소수)을 이분탐색. 순익은 growth에 단조증가.

    양도세 12억 안분이 연속이므로(절벽 제거) 순익은 growth에 대해 단조증가가 유지된다 —
    이분탐색의 전제. 이 값을 넘는 연상승률이면 모든 비용을 메우고 남는다(=진짜 손익분기).
    jeonse_ratio>0이면 거주가치 포함 손익분기(실거주 관점 — 더 낮아진다).
    """
    def net(g: float) -> float:
        return total_net_profit(
            purchase_price=purchase_price, loan_amount=loan_amount, equity=equity,
            effective_rate=effective_rate, growth=g, holding_years=holding_years,
            opportunity_rate=opportunity_rate, is_first_home=is_first_home,
            jeonse_ratio=jeonse_ratio, conversion_rate=conversion_rate)["net_profit"]

    lo, hi = -0.9, 2.0
    if net(lo) > 0:           # 폭락에도 이익(드묾) → 하한 반환
        return lo
    if net(hi) < 0:           # 폭등에도 손해 → 상한 반환
        return hi
    for _ in range(60):       # 이분탐색 수렴
        mid = (lo + hi) / 2
        if net(mid) >= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2
