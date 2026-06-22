"""[GENERATED] an_dt01 range 결정표 테스트 — 완전성 + 룩업 (§9-④). 스펙에서 생성."""

import unittest
from datetime import date
from contexts.analysis.domain.an_dt01_table import AnDt01Rule, AnDt01Table
from contexts.analysis.domain.exceptions import IncompleteDecisionTable, NoMatchingRow

_V = dict(version="v1", effective_date=date(2026, 1, 1))

def _complete():
    return AnDt01Table([
        AnDt01Rule(**_V, purchase_price_min=0.0, purchase_price_max=10.0, max_loan_amount="A"),
        AnDt01Rule(**_V, purchase_price_min=10.0, purchase_price_max=None, max_loan_amount="B"),
    ])


class AnDt01TableTest(unittest.TestCase):
    def test_complete_passes(self):
        self.assertEqual(_complete().check_completeness(), [])
        _complete().assert_complete()

    def test_gap_detected(self):
        t = AnDt01Table([
            AnDt01Rule(**_V, purchase_price_min=0.0, purchase_price_max=10.0, max_loan_amount="A"),
            AnDt01Rule(**_V, purchase_price_min=20.0, purchase_price_max=None, max_loan_amount="B"),
        ])
        self.assertTrue(any("공백" in p for p in t.check_completeness()))
        with self.assertRaises(IncompleteDecisionTable):
            t.assert_complete()

    def test_lookup(self):
        self.assertEqual(_complete().lookup(5.0, date(2026, 6, 1)), "A")
        self.assertEqual(_complete().lookup(50.0, date(2026, 6, 1)), "B")
        with self.assertRaises(NoMatchingRow):
            _complete().lookup(-1.0, date(2026, 6, 1))


if __name__ == "__main__":
    unittest.main()
