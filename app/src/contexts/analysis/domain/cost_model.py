"""[HAND-WRITTEN] 매매 총비용·총수익 모델 — 무상태 calculation (순수 함수). I/O·상태 없음.

기존 손익분기(an_f01)는 '이자만' 메우는 약한 모델이었다. 여기서는 실제 의사결정에 필요한
거래·보유·청산 비용을 모두 반영한 '총비용 손익분기'와 순익/ROE를 계산한다.

반영 비용: 취득세(+교육세 근사) · 매수/매도 중개보수 · 보유세(근사) · 대출이자 · 양도소득세
           · 자기자본 기회비용.  금액=원, 비율=소수.

정책값(세율·요율)은 2026 기준 법정 구간을 아래 상수로 둔다(자주 바뀜 → 추후 결정표로 분리 가능,
AN-F04 스트레스버퍼가 도메인 상수인 것과 같은 처리). 보유세/양도세는 명시한 근사이며,
정밀 산식(공시가·종부세 공제·장특공 세분)은 후속 정밀화 대상.
"""

from __future__ import annotations

_EOK = 100_000_000.0   # 1억(원)

# ── 취득세: 주택 1주택 기준. 6억↓ 1%, 6~9억 1→3% 선형, 9억↑ 3%. (+지방교육세 ≈ ×1.1) ──
def acquisition_tax_rate(price: float) -> float:
    """실효 취득세율(소수, 지방교육세 포함 근사). 농특세(전용85㎡초과 0.2%)는 면적 미입력이라 제외."""
    eok = price / _EOK
    if eok <= 6:
        base = 0.01
    elif eok <= 9:
        base = 0.01 + (eok - 6) * (0.02 / 3)   # 6억 1% → 9억 3% 선형
    else:
        base = 0.03
    return base * 1.1                          # 지방교육세 근사 가산


# ── 중개보수 상한요율(매매, 서울 2021 개편): 구간별 ──
def brokerage_rate(price: float) -> float:
    eok = price / _EOK
    if eok < 0.5:
        return 0.006
    if eok < 2:
        return 0.005
    if eok < 9:
        return 0.004
    if eok < 12:
        return 0.005
    if eok < 15:
        return 0.006
    return 0.007


# ── 보유세(재산세+종부세) 연간, 매매가 대비 근사율. 1주택 기준 대략값. ──
def annual_holding_tax(price: float) -> float:
    eok = price / _EOK
    if eok <= 9:
        rate = 0.001
    elif eok <= 15:
        rate = 0.0025
    elif eok <= 25:
        rate = 0.005
    else:
        rate = 0.008
    return price * rate


# ── 양도소득세(근사): 1주택 비과세 토글 + 일반 장기보유특별공제 + 기본세율 누진(+지방소득세 10%) ──
_CGT_BRACKETS = [   # (과세표준 상한(원), 한계세율)
    (14_000_000, 0.06), (50_000_000, 0.15), (88_000_000, 0.24),
    (150_000_000, 0.35), (300_000_000, 0.38), (500_000_000, 0.40),
    (1_000_000_000, 0.42), (float("inf"), 0.45),
]


def _progressive_cgt(base: float) -> float:
    """과세표준 → 누진 산출세액(지방소득세 제외)."""
    if base <= 0:
        return 0.0
    tax, lo = 0.0, 0.0
    for hi, rate in _CGT_BRACKETS:
        if base > hi:
            tax += (hi - lo) * rate
            lo = hi
        else:
            tax += (base - lo) * rate
            break
    return tax


def capital_gains_tax(gain: float, holding_years: float, *, first_home_exempt: bool) -> float:
    """양도소득세 근사(원). first_home_exempt면 0(1주택 2년+·12억↓는 호출측에서 판정).

    일반 장기보유특별공제: 보유 3년부터 연 2%, 최대 30%. 기본공제 연 250만.
    """
    if first_home_exempt or gain <= 0:
        return 0.0
    ltd = min(0.30, holding_years * 0.02) if holding_years >= 3 else 0.0
    base = gain * (1 - ltd) - 2_500_000
    return _progressive_cgt(base) * 1.1        # 지방소득세 10% 가산


def _first_home_exempt(is_first_home: bool, sale_price: float, holding_years: float) -> bool:
    """1주택 비과세 요건 근사: 1주택 & 보유 2년+ & 양도가 12억 이하."""
    return bool(is_first_home and holding_years >= 2 and sale_price <= 12 * _EOK)


def total_net_profit(*, purchase_price: float, loan_amount: float, equity: float,
                     effective_rate: float, growth: float, holding_years: float,
                     opportunity_rate: float, is_first_home: bool) -> dict:
    """보유기간 H년·연상승률 growth 가정 시 모든 비용 차감 순익(원)과 비용 내역.

    매도가 S = 매매가 × (1+growth)^H (복리). 순익 = 자본이득 − 모든비용.
    ROE 분모 = 투입 자기자본(equity + 취득부대비용).
    """
    P, L, H = purchase_price, loan_amount, holding_years
    buy_tax = P * acquisition_tax_rate(P)
    buy_fee = P * brokerage_rate(P)
    sale = P * (1 + growth) ** H
    gain = sale - P
    sell_fee = sale * brokerage_rate(sale)
    exempt = _first_home_exempt(is_first_home, sale, H)
    cgt = capital_gains_tax(gain, H, first_home_exempt=exempt)
    interest = L * effective_rate * H
    holding_tax = annual_holding_tax(P) * H
    invested = equity + buy_tax + buy_fee
    opportunity = invested * opportunity_rate * H
    net = gain - buy_tax - buy_fee - sell_fee - cgt - interest - holding_tax - opportunity
    return {
        "net_profit": net,
        "sale_price": sale,
        "capital_gain": gain,
        "invested_equity": invested,
        "roe": net / invested if invested > 0 else 0.0,
        "first_home_exempt": exempt,
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
                     opportunity_rate: float, is_first_home: bool) -> float:
    """순익=0 이 되는 연상승률(소수)을 이분탐색. 순익은 growth에 단조증가.

    이 값을 넘는 연상승률이면 모든 비용을 메우고 남는다(=진짜 손익분기).
    """
    def net(g: float) -> float:
        return total_net_profit(
            purchase_price=purchase_price, loan_amount=loan_amount, equity=equity,
            effective_rate=effective_rate, growth=g, holding_years=holding_years,
            opportunity_rate=opportunity_rate, is_first_home=is_first_home)["net_profit"]

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
