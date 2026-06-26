"""집계 스냅샷 캐시 검증 — '내려주는 값을 대체'하므로 라이브와 동일함을 증명.

핵심 보장:
  ① 동등성: cached == live (저장값=라이브출력, 재구현 없음)
  ② 캐시 서빙: 버전 일치 시 저장된 payload를 그대로(변조 sentinel로 증명)
  ③ 데이터 변경 무효화: 새 수집(fetched_count>0)→data_version 변경→재계산
  ④ 로직 변경 무효화: AGG_LOGIC_VERSION ↑ → 재계산
  ⑤ 폴백: 버전 포트 없는 스토어 → 라이브, 저장 안 함, 크래시 없음
"""
import json
from datetime import date
from unittest import mock

from django.test import TestCase

import contexts.market_data.application.trade_query_service as tqs
from contexts.market_data.adapters.db.django_store import DjangoTradeStore
from contexts.market_data.adapters.db.models import (
    AggregateSnapshot, CollectionJobRecord, TradeRecord)
from contexts.market_data.application.trade_query_service import TradeQueryService

KEY = "rankings|m=12|mt=10|lim=100"


def _norm(o) -> str:
    return json.dumps(o, sort_keys=True, default=str, ensure_ascii=False)


class AggregateSnapshotTest(TestCase):
    def setUp(self):
        # 한 단지 12건(6개월×2, 같은 평형 84㎡, 상승 추세) → 표본 게이트 통과
        for i, (y, m) in enumerate([(2026, 1), (2026, 2), (2026, 3),
                                    (2026, 4), (2026, 5), (2026, 6)]):
            for j in range(2):
                TradeRecord.objects.create(
                    complex_id="11680-테스트", apt_name="테스트", region_code="11680",
                    legal_dong="대치동", area_m2=84.0,
                    price=1_000_000_000 + i * 50_000_000 + j * 1_000_000,
                    floor=10 + j, contract_date=date(y, m, 10 + j), build_year=2010)
        CollectionJobRecord.objects.create(
            job_type="trades", target_date="202606", state="DONE", fetched_count=12)
        self.q = TradeQueryService(DjangoTradeStore())

    def test_cached_equals_live(self):
        pairs = [
            (self.q.rank_complexes(12, 10, 100), self.q.rankings_cached(12, 10, 100)),
            (self.q.region_summary(12, 10), self.q.region_summary_cached(12, 10)),
            (self.q.candidate_metrics(12, 10, 2000), self.q.candidates_cached(12, 10, 2000)),
            (self.q._ticker_payload(), self.q.ticker()),
        ]
        for live, cached in pairs:
            self.assertEqual(_norm(cached), _norm(live))
        # 의미 있는 검증이도록 실제로 단지 1개가 랭킹에 올랐는지 확인
        self.assertEqual(self.q.rank_complexes(12, 10, 100)["total_qualified"], 1)

    def test_cache_hit_serves_stored(self):
        self.q.rankings_cached(12, 10, 100)                  # 스냅샷 생성(v 일치)
        row = AggregateSnapshot.objects.get(cache_key=KEY)
        row.payload = {"ranked": ["TAMPERED"]}; row.save()   # 버전 그대로 변조
        self.assertEqual(self.q.rankings_cached(12, 10, 100), {"ranked": ["TAMPERED"]})

    def test_data_version_change_recomputes(self):
        self.q.rankings_cached(12, 10, 100)
        row = AggregateSnapshot.objects.get(cache_key=KEY)
        row.payload = {"ranked": ["STALE"]}; row.save()
        # 새 수집(fetched_count>0) → data_version 변경 → 재계산
        CollectionJobRecord.objects.create(
            job_type="trades", target_date="209901", state="DONE", fetched_count=1)
        out = self.q.rankings_cached(12, 10, 100)
        self.assertEqual(_norm(out), _norm(self.q.rank_complexes(12, 10, 100)))
        self.assertNotEqual(out, {"ranked": ["STALE"]})

    def test_empty_refresh_does_not_invalidate(self):
        self.q.rankings_cached(12, 10, 100)
        row = AggregateSnapshot.objects.get(cache_key=KEY)
        row.payload = {"ranked": ["KEPT"]}; row.save()
        # 빈 갱신(fetched_count=0) → 버전 불변 → 캐시 유지(헛 재계산 없음)
        CollectionJobRecord.objects.create(
            job_type="trades", target_date="209902", state="DONE", fetched_count=0)
        self.assertEqual(self.q.rankings_cached(12, 10, 100), {"ranked": ["KEPT"]})

    def test_logic_version_change_recomputes(self):
        self.q.rankings_cached(12, 10, 100)
        row = AggregateSnapshot.objects.get(cache_key=KEY)
        row.payload = {"ranked": ["OLD_LOGIC"]}; row.save()
        with mock.patch.object(tqs, "AGG_LOGIC_VERSION", tqs.AGG_LOGIC_VERSION + 1):
            out = self.q.rankings_cached(12, 10, 100)
        self.assertNotEqual(out, {"ranked": ["OLD_LOGIC"]})

    def test_store_without_version_port_falls_back(self):
        class NoVer:                       # data_version 등 포트 없는 스토어
            def __init__(self, inner): self._i = inner
            def __getattr__(self, n):
                if n in ("data_version", "agg_snapshot", "save_agg_snapshot"):
                    raise AttributeError(n)
                return getattr(self._i, n)
        q2 = TradeQueryService(NoVer(DjangoTradeStore()))
        self.assertEqual(_norm(q2.rankings_cached(12, 10, 100)),
                         _norm(q2.rank_complexes(12, 10, 100)))
        self.assertEqual(AggregateSnapshot.objects.count(), 0)   # 저장도 안 함
