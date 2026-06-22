"""[GENERATED] an_dt02 flag 결정표 테스트 — 정확매칭 룩업. 스펙에서 생성."""

import unittest
from datetime import date
from contexts.analysis.domain.an_dt02_table import AnDt02Rule, AnDt02Table
from contexts.analysis.domain.exceptions import NoMatchingRow

_V = dict(version="v1", effective_date=date(2026, 1, 1))

class AnDt02TableTest(unittest.TestCase):
    def test_lookup_hit_and_miss(self):
        t = AnDt02Table([
            AnDt02Rule(**_V, complex_id="k1", ltz_applies="OUT"),
        ])
        self.assertEqual(
            t.lookup("k1", as_of=date(2026, 6, 1)),
            "OUT",
        )
        with self.assertRaises(NoMatchingRow):
            t.lookup("nope1", as_of=date(2026, 6, 1))


if __name__ == "__main__":
    unittest.main()
