"""분석 계산식(AN-F01~F04) 도메인 테스트 — 기획서 §5 예시 수치로 검증."""

import unittest

from contexts.analysis.domain.breakeven_calc import an_f01
from contexts.analysis.domain.leverage_r_o_e import an_f02, roe
from contexts.analysis.domain.stress_d_s_r import an_f04


class Formulas(unittest.TestCase):
    def test_breakeven_rate(self):
        # 대출 6억 / 매매 10억(비중 0.6) × 금리 5% → 연 3%
        self.assertAlmostEqual(an_f01(6e8, 1e9, 0.05), 0.03)

    def test_breakeven_rejects_zero_price(self):
        with self.assertRaises(ValueError):
            an_f01(6e8, 0, 0.05)

    def test_net_profit(self):
        # 10억×5% − 6억×5% = 5,000만 − 3,000만 = 2,000만
        self.assertAlmostEqual(an_f02(1e9, 0.05, 6e8, 0.05), 2e7)

    def test_roe(self):
        # 순익 2,000만 / 자기자본 4억 → 5%
        self.assertAlmostEqual(roe(2e7, 4e8), 0.05)

    def test_roe_rejects_zero_equity(self):
        with self.assertRaises(ValueError):
            roe(2e7, 0)

    def test_end_to_end_roe(self):
        # 매매 10억, 자기자본 4억, 대출 6억@5%, 상승 5% → ROE 5%
        price, equity, loan, rate, growth = 1e9, 4e8, 6e8, 0.05, 0.05
        profit = an_f02(price, growth, loan, rate)
        self.assertAlmostEqual(roe(profit, equity), 0.05)

    def test_stress_rate(self):
        self.assertAlmostEqual(an_f04(0.05), 0.08)         # 기본 버퍼 3%p
        self.assertAlmostEqual(an_f04(0.05, buffer=0.02), 0.07)


if __name__ == "__main__":
    unittest.main()
