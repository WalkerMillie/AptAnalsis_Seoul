"""[HAND-WRITTEN] 분석 유스케이스 (application). §2: 판단/계산은 도메인에, 여기선 조율만.

analysis 컨텍스트는 애그리거트가 없어 generator가 application을 안 깔았다(의도된 결과).
손익분기·ROE·스트레스 계산(도메인)과 대출한도·토허제 규제표(도메인)를 '조합만' 한다.
규칙을 if로 재구현하지 않는다. 표 로딩(I/O)은 어댑터 로더에서 받은 도메인 객체를 주입받는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from contexts.analysis.domain.breakeven_calc import an_f01
from contexts.analysis.domain.stress_d_s_r import an_f04
from contexts.analysis.domain.cost_model import breakeven_growth, total_net_profit
from contexts.analysis.domain.exceptions import NoMatchingRow


@dataclass(frozen=True)
class AnalysisResult:
    breakeven_rate: float        # 총비용 손익분기 상승률(소수) — 모든 비용 메우는 연상승률
    interest_breakeven: float    # 이자만 메우는 손익분기(소수, 참고) = an_f01
    net_profit: float            # 모든 비용 차감 순익(원, 보유기간 전체)
    roe: float                   # 투입 자기자본 대비 ROE(소수, 보유기간 전체)
    stress_rate: float           # 스트레스 금리(소수)
    max_loan_amount: int         # 규제 대출 한도(원)
    ltz_applies: bool | None     # 토허제 여부. None = 데이터 없음(확인 필요)
    is_profitable: bool          # 가정상승률 ≥ 총비용 손익분기 (조합 판정, 규칙 아님)
    breakeven_margin: float      # 초과상승률(%p, 소수) = 가정상승률 − 총비용 손익분기
    first_home_exempt: bool      # 1주택 양도세 비과세 적용 여부
    costs: dict                  # 비용 내역(취득세·중개·보유세·이자·양도세·기회비용, 원)
    jeonse_ratio: float | None   # 적용된 전세가율(소수). None = 전세 데이터 없음
    residence_value: float       # 보유기간 누적 거주가치(원, 자택 거주효용)
    net_profit_residence: float  # 거주가치 포함 순익(원) — 자택 관점
    roe_residence: float         # 거주가치 포함 ROE(소수)
    breakeven_rate_residence: float  # 거주가치 포함 손익분기 상승률(소수)
    is_profitable_residence: bool    # 가정상승률 ≥ 거주가치 포함 손익분기


class AnalysisService:
    """대출한도표(range)·토허제표(flag)는 도메인 객체로 주입(어댑터 로더가 만든다)."""

    def __init__(self, loan_limit_table, ltz_table):
        self._loan_limit = loan_limit_table
        self._ltz = ltz_table

    def analyze(self, *, purchase_price: float, loan_amount: float, equity: float,
                effective_rate: float, assumed_growth: float,
                complex_id: str, as_of: date,
                holding_years: float = 2.0, opportunity_rate: float = 0.03,
                is_first_home: bool = True,
                jeonse_ratio: float | None = None) -> AnalysisResult:
        # 총비용 모델(B안): 거래·보유·청산 비용 모두 반영. 가정상승률은 '연' 기준.
        outcome = total_net_profit(
            purchase_price=purchase_price, loan_amount=loan_amount, equity=equity,
            effective_rate=effective_rate, growth=assumed_growth,
            holding_years=holding_years, opportunity_rate=opportunity_rate,
            is_first_home=is_first_home)
        total_breakeven = breakeven_growth(
            purchase_price=purchase_price, loan_amount=loan_amount, equity=equity,
            effective_rate=effective_rate, holding_years=holding_years,
            opportunity_rate=opportunity_rate, is_first_home=is_first_home)
        # 자택 관점: 전세가율 거주가치 포함(없으면 0 → 투자관점과 동일).
        jr = jeonse_ratio or 0.0
        outcome_res = total_net_profit(
            purchase_price=purchase_price, loan_amount=loan_amount, equity=equity,
            effective_rate=effective_rate, growth=assumed_growth,
            holding_years=holding_years, opportunity_rate=opportunity_rate,
            is_first_home=is_first_home, jeonse_ratio=jr)
        breakeven_res = breakeven_growth(
            purchase_price=purchase_price, loan_amount=loan_amount, equity=equity,
            effective_rate=effective_rate, holding_years=holding_years,
            opportunity_rate=opportunity_rate, is_first_home=is_first_home,
            jeonse_ratio=jr)
        interest_be = an_f01(loan_amount, purchase_price, effective_rate)  # 이자만(참고)
        stress = an_f04(effective_rate)
        max_loan = int(self._loan_limit.lookup(purchase_price, as_of))
        try:
            ltz = self._ltz.lookup(complex_id, as_of) == "true"
        except NoMatchingRow:
            ltz = None   # 미등재 → 규제결론 단정 않고 '확인 필요'로 전달
        return AnalysisResult(
            breakeven_rate=total_breakeven,
            interest_breakeven=interest_be,
            net_profit=outcome["net_profit"],
            roe=outcome["roe"],
            stress_rate=stress,
            max_loan_amount=max_loan,
            ltz_applies=ltz,
            is_profitable=assumed_growth >= total_breakeven,
            breakeven_margin=assumed_growth - total_breakeven,
            first_home_exempt=outcome["first_home_exempt"],
            costs=outcome["costs"],
            jeonse_ratio=(jeonse_ratio if jeonse_ratio else None),
            residence_value=outcome_res["residence_value"],
            net_profit_residence=outcome_res["net_profit"],
            roe_residence=outcome_res["roe"],
            breakeven_rate_residence=breakeven_res,
            is_profitable_residence=assumed_growth >= breakeven_res,
        )
