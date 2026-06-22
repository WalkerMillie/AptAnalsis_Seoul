"""분석 유스케이스(application) 테스트 — DRF 없이 순수 조합 로직 검증.

B안(총비용 모델): breakeven_rate=모든 비용 메우는 손익분기, interest_breakeven=이자만(참고).
"""

import unittest
from datetime import date

from contexts.analysis.application import AnalysisService
from contexts.analysis.adapters.an_dt01_loader import load_an_dt01_table
from contexts.analysis.adapters.an_dt02_loader import load_an_dt02_table

AS_OF = date(2026, 6, 20)


class AnalysisServiceTest(unittest.TestCase):
    def setUp(self):
        self.svc = AnalysisService(load_an_dt01_table(), load_an_dt02_table())

    def test_total_cost_breakeven_is_above_interest_only(self):
        r = self.svc.analyze(
            purchase_price=1e9, loan_amount=6e8, equity=4e8,
            effective_rate=0.05, assumed_growth=0.05,
            complex_id="GANGNAM-DAECHI-001", as_of=AS_OF,
        )
        self.assertAlmostEqual(r.interest_breakeven, 0.03)      # 0.6 × 0.05 (이자만)
        self.assertGreater(r.breakeven_rate, r.interest_breakeven)  # 총비용 손익분기가 더 높음
        self.assertAlmostEqual(r.stress_rate, 0.08)             # 0.05 + 0.03
        self.assertEqual(r.max_loan_amount, 600_000_000)        # 10억 → 6억
        self.assertTrue(r.ltz_applies)                          # 토허구역
        # 비용 내역이 모두 들어있다
        for k in ("acquisition_tax", "buy_brokerage", "sell_brokerage",
                  "capital_gains_tax", "interest", "holding_tax", "opportunity_cost"):
            self.assertIn(k, r.costs)

    def test_profitable_flag_tracks_total_breakeven(self):
        # 매우 높은 가정 상승률이면 총비용 손익분기를 넘어 이익.
        hi = self.svc.analyze(
            purchase_price=1e9, loan_amount=6e8, equity=4e8,
            effective_rate=0.05, assumed_growth=0.20,
            complex_id="X", as_of=AS_OF)
        self.assertTrue(hi.is_profitable)
        self.assertGreater(hi.breakeven_margin, 0)
        # 0% 상승이면 비용 때문에 손해.
        lo = self.svc.analyze(
            purchase_price=1e9, loan_amount=6e8, equity=4e8,
            effective_rate=0.05, assumed_growth=0.0,
            complex_id="X", as_of=AS_OF)
        self.assertFalse(lo.is_profitable)
        self.assertLess(lo.net_profit, 0)

    def test_first_home_exemption_helps(self):
        # 1주택 비과세(2년+·12억↓) vs 다주택 — 비과세면 양도세 0, 손익분기 더 낮다.
        base = dict(purchase_price=8e8, loan_amount=4e8, equity=4e8,
                    effective_rate=0.04, assumed_growth=0.05,
                    complex_id="X", as_of=AS_OF, holding_years=3.0)
        first = self.svc.analyze(is_first_home=True, **base)
        multi = self.svc.analyze(is_first_home=False, **base)
        self.assertTrue(first.first_home_exempt)
        self.assertFalse(multi.first_home_exempt)
        self.assertLess(first.breakeven_rate, multi.breakeven_rate)


if __name__ == "__main__":
    unittest.main()
