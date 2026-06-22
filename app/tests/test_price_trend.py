"""실거래 가격추세(A안) 단위테스트 — 순수, 네트워크/Django 불필요.

도메인: period_change(기간 상승률) · confidence_score(신뢰도).
application: TradeQueryService.price_growth/scores/rank (끝점 견고화 + 표본 게이트 + 신뢰도).
"""

import unittest
from datetime import date

from contexts.market_data.domain.price_trend import (
    period_change, confidence_score,
)
from contexts.market_data.domain.trade import Trade
from contexts.market_data.adapters.in_memory_job_store import InMemoryJobStore
from contexts.market_data.application.trade_query_service import TradeQueryService


class PeriodChangeTest(unittest.TestCase):
    def test_growth(self):
        self.assertAlmostEqual(period_change(100.0, 110.0), 0.10, places=6)

    def test_decline_negative(self):
        self.assertLess(period_change(100.0, 90.0), 0)

    def test_guard(self):
        with self.assertRaises(ValueError):
            period_change(0.0, 100.0)


class ConfidenceTest(unittest.TestCase):
    def test_monotonic_and_bounded(self):
        lo = confidence_score(5, 3, 3)
        hi = confidence_score(40, 12, 12)
        self.assertTrue(0 <= lo <= hi <= 1.0)

    def test_more_endpoint_trades_raises_confidence(self):
        self.assertLess(confidence_score(20, 6, 3), confidence_score(20, 6, 8))


def _t(complex_id, ym, ppm2, *, dong="대치동", region="11680", area=100.0, floor=5):
    y, m = ym // 100, ym % 100
    return Trade(complex_id=complex_id, apt_name=complex_id.split("-")[-1],
                 region_code=region, legal_dong=dong, area_m2=area,
                 price=int(ppm2 * area), floor=floor, contract_date=date(y, m, 1))


def _series(cid, p_early, p_late, **kw):
    """첫 달(202603)·끝 달(202605) 각 3건 + 중간(202604) 1건 = 끝점 견고(양끝 ≥3)."""
    out = []
    for f in (1, 5, 9):
        out.append(_t(cid, 202603, p_early, floor=f, **kw))
        out.append(_t(cid, 202605, p_late, floor=f, **kw))
    out.append(_t(cid, 202604, (p_early + p_late) // 2, **kw))
    return out


class PriceGrowthQueryTest(unittest.TestCase):
    def setUp(self):
        self.store = InMemoryJobStore()
        self.q = TradeQueryService(self.store)

    def test_growth_has_value_endpoints_and_confidence(self):
        self.store.upsert("trades", _series("11680-A", 1_000_000, 1_100_000))
        g = self.q.price_growth("11680-A", months=6)
        self.assertGreater(g["growth"], 0)
        self.assertEqual(g["first"]["n"], 3)        # 첫 구간 3건(끝점 견고)
        self.assertEqual(g["last"]["n"], 3)
        self.assertIn("confidence", g)
        self.assertIn(g["confidence_tier"], ("높음", "보통", "낮음"))

    def test_sparse_endpoint_is_rejected(self):
        # 끝 달 단 1건 → 끝 구간 < 3건 → 표본부족(외딴 끝점 차단).
        rows = [_t("11680-B", 202603, 1_000_000, floor=f) for f in (1, 5, 9)]
        rows += [_t("11680-B", 202604, 1_000_000), _t("11680-B", 202605, 2_000_000)]
        self.store.upsert("trades", rows)
        g = self.q.price_growth("11680-B", months=6)
        self.assertIsNone(g["growth"])
        self.assertIn("표본", g["reason"])

    def test_scores_sorted_with_confidence(self):
        self.store.upsert("trades",
            _series("11680-A", 1_000_000, 1_020_000)       # 완만
            + _series("11680-C", 1_000_000, 1_200_000)     # 가파름
            + [_t("11680-D", 202605, 1_000_000)])          # 표본부족
        scores = self.q.complex_growth_scores("11680", "대치동", months=6)
        self.assertEqual(scores[0]["complex_id"], "11680-C")
        self.assertIsNotNone(scores[0]["confidence"])
        self.assertIsNone(scores[-1]["growth"])        # 표본부족 맨 뒤

    def test_mix_does_not_inflate_growth(self):
        # 같은 평형(84㎡)은 거의 횡보인데, 첫 구간엔 싼 59㎡(저㎡가)·끝 구간엔 비싼 59㎡가 섞여도
        # 평형 정규화로 84㎡ 기준만 보므로 상승률이 폭증하지 않아야 한다.
        rows = [_t("11680-MIX", 202604, 1_005_000, area=84.0)]  # 중간 달(거래월 ≥3 충족)
        for f in (1, 5, 9):                                   # 84㎡: 1000→1010만(거의 횡보)
            rows.append(_t("11680-MIX", 202603, 1_000_000, area=84.0, floor=f))
            rows.append(_t("11680-MIX", 202605, 1_010_000, area=84.0, floor=f))
        # 끝 구간에만 고㎡가 소형 59㎡ 다수 — 정규화 안 하면 평균 ㎡가 폭등 유발
        for f in (2, 6):
            rows.append(_t("11680-MIX", 202605, 2_000_000, area=59.0, floor=f))
        self.store.upsert("trades", rows)
        g = self.q.price_growth("11680-MIX", months=6)
        self.assertEqual(g["band_m2"], 84)                    # 대표 평형 = 84
        self.assertLess(g["growth"], 0.20)                # 폭증 아님(84㎡ 횡보 반영)

    def test_rank_includes_confidence(self):
        self.store.upsert("trades",
            _series("11680-C", 1_000_000, 1_200_000)
            + _series("11650-E", 1_000_000, 1_050_000, region="11650", dong="반포동"))
        r = self.q.rank_complexes(months=6, min_trades=5, limit=10)
        self.assertEqual(r["ranked"][0]["complex_id"], "11680-C")
        self.assertIn("confidence", r["ranked"][0])
        self.assertIn("n", r["ranked"][0]["first"])


if __name__ == "__main__":
    unittest.main()
