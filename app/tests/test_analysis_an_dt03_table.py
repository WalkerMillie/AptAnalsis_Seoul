"""[GENERATED] an_dt03 flag 결정표 테스트 — 정확매칭 룩업. 스펙에서 생성."""

import unittest
from datetime import date
from contexts.analysis.domain.an_dt03_table import AnDt03Rule, AnDt03Table
from contexts.analysis.domain.exceptions import NoMatchingRow

_V = dict(version="v1", effective_date=date(2026, 1, 1))

class AnDt03TableTest(unittest.TestCase):
    def test_lookup_hit_and_miss(self):
        t = AnDt03Table([
            AnDt03Rule(**_V, holding_years="k1", residency_years="k2", house_count="k3", capital_gains_tax_exempt="OUT"),
        ])
        self.assertEqual(
            t.lookup("k1", "k2", "k3", as_of=date(2026, 6, 1)),
            "OUT",
        )
        with self.assertRaises(NoMatchingRow):
            t.lookup("nope1", "nope2", "nope3", as_of=date(2026, 6, 1))


if __name__ == "__main__":
    unittest.main()
