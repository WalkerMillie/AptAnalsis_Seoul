"""총비용 모델(cost_model) 단위테스트 — 순수, 네트워크/Django 불필요."""

import unittest

from contexts.analysis.domain.cost_model import (
    acquisition_tax_rate, brokerage_rate, annual_holding_tax,
    capital_gains_tax, total_net_profit, breakeven_growth,
)

_EOK = 100_000_000.0


class RateTableTest(unittest.TestCase):
    def test_acquisition_tax_brackets(self):
        self.assertAlmostEqual(acquisition_tax_rate(5e8), 0.01 * 1.1)      # 6억↓ 1%
        self.assertAlmostEqual(acquisition_tax_rate(20e8), 0.03 * 1.1)     # 9억↑ 3%
        mid = acquisition_tax_rate(7.5e8)                                  # 6~9억 선형
        self.assertTrue(0.01 * 1.1 < mid < 0.03 * 1.1)

    def test_brokerage_brackets(self):
        self.assertAlmostEqual(brokerage_rate(5e8), 0.004)   # 2~9억
        self.assertAlmostEqual(brokerage_rate(13e8), 0.006)  # 12~15억
        self.assertAlmostEqual(brokerage_rate(20e8), 0.007)  # 15억↑

    def test_holding_tax_increases_with_price(self):
        self.assertLess(annual_holding_tax(5e8), annual_holding_tax(20e8))


class CapitalGainsTest(unittest.TestCase):
    def test_first_home_exempt_zero(self):
        self.assertEqual(capital_gains_tax(3e8, 3, first_home_exempt=True), 0.0)

    def test_no_gain_zero(self):
        self.assertEqual(capital_gains_tax(-1e7, 3, first_home_exempt=False), 0.0)

    def test_taxed_when_not_exempt(self):
        tax = capital_gains_tax(3e8, 3, first_home_exempt=False)
        self.assertGreater(tax, 0)
        self.assertLess(tax, 3e8)        # 차익보다 작아야


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


if __name__ == "__main__":
    unittest.main()
