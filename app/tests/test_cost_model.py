"""총비용 모델(cost_model) 단위테스트 — 순수, 네트워크/Django 불필요."""

import unittest

from contexts.analysis.domain.cost_model import (
    acquisition_tax_rate, brokerage_rate, annual_holding_tax,
    capital_gains_tax, taxable_fraction, total_net_profit, breakeven_growth,
)

_EOK = 100_000_000.0


class RateTableTest(unittest.TestCase):
    def test_acquisition_tax_brackets(self):
        self.assertAlmostEqual(acquisition_tax_rate(5e8), 0.01 * 1.1)      # 6억↓ 1%
        self.assertAlmostEqual(acquisition_tax_rate(20e8), 0.03 * 1.1)     # 9억↑ 3%
        mid = acquisition_tax_rate(7.5e8)                                  # 6~9억 선형
        self.assertTrue(0.01 * 1.1 < mid < 0.03 * 1.1)

    def test_multi_home_acquisition_is_heavier(self):
        # 다주택 취득세 중과 > 동일가격 1주택 실효율
        self.assertGreater(acquisition_tax_rate(10e8, is_first_home=False),
                           acquisition_tax_rate(10e8, is_first_home=True))

    def test_brokerage_brackets(self):
        self.assertAlmostEqual(brokerage_rate(5e8), 0.004)   # 2~9억
        self.assertAlmostEqual(brokerage_rate(13e8), 0.006)  # 12~15억
        self.assertAlmostEqual(brokerage_rate(20e8), 0.007)  # 15억↑

    def test_holding_tax_increases_with_price(self):
        self.assertLess(annual_holding_tax(5e8), annual_holding_tax(20e8))


class CapitalGainsTest(unittest.TestCase):
    def test_first_home_under_12eok_exempt(self):
        # 1주택·2년+·매도가 10억(≤12억) → 전액 비과세
        self.assertEqual(capital_gains_tax(3e8, 10e8, 3, is_first_home=True), 0.0)

    def test_no_gain_zero(self):
        self.assertEqual(capital_gains_tax(-1e7, 8e8, 3, is_first_home=False), 0.0)

    def test_taxed_when_multi_home(self):
        tax = capital_gains_tax(3e8, 8e8, 3, is_first_home=False)
        self.assertGreater(tax, 0)
        self.assertLess(tax, 3e8)        # 차익보다 작아야

    def test_first_home_only_excess_over_12eok_taxed(self):
        # 1주택 매도가 13억: (13−12)/13 만 과세 → 다주택 전액과세보다 훨씬 적다
        gain = 3e8
        tax_1home = capital_gains_tax(gain, 13e8, 3, is_first_home=True)
        tax_multi = capital_gains_tax(gain, 13e8, 3, is_first_home=False)
        self.assertGreater(tax_1home, 0)              # 12억 초과분은 과세
        self.assertLess(tax_1home, tax_multi * 0.3)   # 안분 + 우대공제로 훨씬 가벼움

    def test_taxable_fraction_continuous_at_12eok(self):
        # 12억 경계에서 과세비율 연속(0 → 0에서 미세 상승). 절벽 없음.
        self.assertEqual(taxable_fraction(12e8, 3, is_first_home=True), 0.0)
        just_above = taxable_fraction(12e8 + 1e6, 3, is_first_home=True)
        self.assertGreater(just_above, 0.0)
        self.assertLess(just_above, 0.01)            # 경계 직후엔 거의 0


class TotalAndBreakevenTest(unittest.TestCase):
    BASE = dict(purchase_price=1e9, loan_amount=6e8, equity=4e8,
                effective_rate=0.05, holding_years=2.0,
                opportunity_rate=0.03, is_first_home=True)

    def test_net_increases_with_growth(self):
        lo = total_net_profit(growth=0.0, **self.BASE)["net_profit"]
        hi = total_net_profit(growth=0.10, **self.BASE)["net_profit"]
        self.assertLess(lo, hi)
        self.assertLess(lo, 0)           # 0% 상승 → 비용 탓 손해

    def test_breakeven_zeroes_net(self):
        be = breakeven_growth(**self.BASE)
        net = total_net_profit(growth=be, **self.BASE)["net_profit"]
        self.assertAlmostEqual(net, 0.0, delta=1e6)   # 손익분기에서 순익≈0
        # 손익분기보다 높으면 +, 낮으면 −
        self.assertGreater(total_net_profit(growth=be + 0.02, **self.BASE)["net_profit"], 0)
        self.assertLess(total_net_profit(growth=be - 0.02, **self.BASE)["net_profit"], 0)

    def test_breakeven_above_pure_interest(self):
        # 총비용 손익분기 > 이자만 손익분기(0.6×0.05=0.03).
        self.assertGreater(breakeven_growth(**self.BASE), 0.03)

    def test_net_monotone_across_12eok_cliff(self):
        # 절벽 회귀 테스트: 매도가가 12억을 넘나드는 성장률 구간에서 순익이 단조증가(불연속 없음).
        # 13억 1주택을 2년 보유 → 성장률을 0~12% 훑으며 매도가가 12억 경계를 통과.
        base = dict(purchase_price=13e8, loan_amount=7e8, equity=6e8,
                    effective_rate=0.045, holding_years=2.0,
                    opportunity_rate=0.03, is_first_home=True)
        prev = None
        for g in [i / 100 for i in range(-5, 13)]:
            net = total_net_profit(growth=g, **base)["net_profit"]
            if prev is not None:
                self.assertGreater(net, prev)   # 단조증가 — 절벽이면 여기서 깨짐
            prev = net


if __name__ == "__main__":
    unittest.main()
