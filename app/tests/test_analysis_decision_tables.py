"""규제 결정표(AN-DT01 대출한도 range, AN-DT02 토허제 flag) 데이터 테스트.

평가기는 생성물(직접수정 금지). 여기선 채운 CSV 룰이 정책(planning §5.3)대로
완전하고 올바르게 룩업되는지 검증한다.
"""

import unittest
from datetime import date

from contexts.analysis.adapters.an_dt01_loader import load_an_dt01_table
from contexts.analysis.adapters.an_dt02_loader import load_an_dt02_table
from contexts.analysis.domain.exceptions import NoMatchingRow

AS_OF = date(2026, 6, 20)


class LoanLimitRange(unittest.TestCase):
    def setUp(self):
        self.t = load_an_dt01_table()

    def test_completeness(self):
        # [0, ∞) 빈틈/겹침 없이 타일링 — 아니면 IncompleteDecisionTable
        self.t.assert_complete()
        self.assertEqual(self.t.check_completeness(), [])

    def test_lookup_bands(self):
        self.assertEqual(self.t.lookup(1_000_000_000, AS_OF), "600000000")   # 10억 → 6억
        self.assertEqual(self.t.lookup(2_000_000_000, AS_OF), "400000000")   # 20억 → 4억
        self.assertEqual(self.t.lookup(3_000_000_000, AS_OF), "200000000")   # 30억 → 2억

    def test_boundary_belongs_to_upper_band(self):
        # 반개구간 [min,max): 정확히 15억은 상위(4억) 구간
        self.assertEqual(self.t.lookup(1_500_000_000, AS_OF), "400000000")

    def test_no_version_before_effective_date(self):
        with self.assertRaises(NoMatchingRow):
            self.t.lookup(1_000_000_000, date(2020, 1, 1))


class LtzFlag(unittest.TestCase):
    def setUp(self):
        self.t = load_an_dt02_table()

    def test_designated_zone_true(self):
        self.assertEqual(self.t.lookup("GANGNAM-DAECHI-001", AS_OF), "true")
        self.assertEqual(self.t.lookup("NOWON-SANGGYE-001", AS_OF), "false")

    def test_unlisted_complex_raises(self):
        # 미등재 단지는 규제결론을 단정하지 않고 NoMatchingRow → 응용계층이 '확인 필요' 처리
        with self.assertRaises(NoMatchingRow):
            self.t.lookup("UNKNOWN-999", AS_OF)


if __name__ == "__main__":
    unittest.main()
