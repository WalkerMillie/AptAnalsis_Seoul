"""구→동→단지 드릴다운 테스트 (DRF 없이).

구=정적 시드(region), 동·단지=수집 실거래 파생(market_data, 거래빈도순).
"""

import unittest
from datetime import date

from contexts.region.application import RegionQueryService
from contexts.market_data.application.trade_query_service import TradeQueryService
from contexts.market_data.adapters.in_memory_job_store import InMemoryJobStore
from contexts.market_data.domain.trade import Trade


class Districts(unittest.TestCase):
    def setUp(self):
        self.svc = RegionQueryService()

    def test_25_seoul_districts(self):
        ds = self.svc.districts()
        self.assertEqual(len(ds), 25)
        self.assertIn({"code": "11680", "name": "강남구"}, ds)

    def test_district_validity(self):
        self.assertTrue(self.svc.is_valid_district("11680"))
        self.assertFalse(self.svc.is_valid_district("99999"))


class DongComplexFromTrades(unittest.TestCase):
    def setUp(self):
        self.store = InMemoryJobStore()
        self.store.upsert("trades", [
            Trade("11680-은마", "은마", "11680", "대치동", 84.97, 1_200_000_000, 15, date(2026, 5, 20)),
            Trade("11680-은마", "은마", "11680", "대치동", 76.79, 1_050_000_000, 3, date(2026, 5, 18)),
            Trade("11680-래미안", "래미안", "11680", "대치동", 94.5, 3_500_000_000, 20, date(2026, 5, 22)),
            Trade("11680-개포자이", "개포자이", "11680", "개포동", 59.9, 1_800_000_000, 7, date(2026, 5, 11)),
        ])
        self.q = TradeQueryService(self.store)

    def test_dongs_for_district(self):
        self.assertEqual(self.q.dongs("11680"), ["개포동", "대치동"])
        self.assertEqual(self.q.dongs("11110"), [])      # 거래 없는 구

    def test_complexes_sorted_by_trade_count(self):
        rows = self.q.complexes("11680", "대치동")
        self.assertEqual([r["apt_name"] for r in rows], ["은마", "래미안"])  # 2건 > 1건
        self.assertEqual(rows[0]["trade_count"], 2)


if __name__ == "__main__":
    unittest.main()
