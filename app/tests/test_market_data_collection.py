"""market_data 수집 슬라이스 테스트 — 도메인 생명주기 + 유스케이스 + MOLIT 파서.

검증 포인트: 상태전이(방어선A), CD-G01 실패경로, CD-INV01 동시성 차단(스토어),
idempotent upsert, 그리고 국토부 XML → Trade 정규화.
"""

import unittest
from datetime import date

from contexts.market_data.domain.collection_job import CollectionJob
from contexts.market_data.domain.collection_job_state import CollectionJobState
from contexts.market_data.domain.exceptions import IllegalTransition
from contexts.market_data.domain.trade import Trade
from contexts.market_data.application import CollectionJobService
from contexts.market_data.adapters.in_memory_job_store import InMemoryJobStore
from contexts.market_data.adapters.molit_source import MolitTradesSource


class JobLifecycle(unittest.TestCase):
    def test_happy_path(self):
        job = CollectionJob.create("trades", "202605")
        self.assertEqual(job.state, CollectionJobState.PENDING)
        job.start(); job.succeed(12)
        self.assertEqual(job.state, CollectionJobState.DONE)
        self.assertEqual(job.fetched_count, 12)

    def test_fail_then_retry(self):
        job = CollectionJob.create("trades", "202605")
        job.start(); job.fail("API 503")               # CD-G01
        self.assertEqual(job.state, CollectionJobState.FAILED)
        self.assertEqual(job.error, "API 503")
        job.retry()
        self.assertEqual(job.state, CollectionJobState.PENDING)

    def test_cannot_succeed_without_running(self):
        job = CollectionJob.create("trades", "202605")  # PENDING
        with self.assertRaises(IllegalTransition):
            job.succeed(1)                               # PENDING→DONE 불허


class CollectionUseCase(unittest.TestCase):
    def _svc(self, fetchers, store=None):
        return CollectionJobService(store=store or InMemoryJobStore(), fetchers=fetchers)

    def test_run_success_and_idempotent(self):
        rows = [
            Trade("11680-은마", "은마", "11680", "대치동", 84.97, 1_200_000_000, 15, date(2026, 5, 20)),
            Trade("11680-은마", "은마", "11680", "대치동", 76.79, 1_050_000_000, 3, date(2026, 5, 18)),
        ]
        store = InMemoryJobStore()
        svc = self._svc({"trades": lambda td: rows}, store)
        job = svc.run("trades", "202605")
        self.assertEqual(job.state.name, "DONE")
        self.assertEqual(job.fetched_count, 2)
        # 같은 행 재수집 → 0건(idempotent), 점유도 해제됨
        job2 = svc.run("trades", "202605")
        self.assertEqual(job2.fetched_count, 0)

    def test_fetch_error_marks_failed(self):
        def boom(td):
            raise RuntimeError("쿼터 초과")
        job = self._svc({"trades": boom}).run("trades", "202605")
        self.assertEqual(job.state.name, "FAILED")        # CD-G01 경로
        self.assertIn("쿼터 초과", job.error)

    def test_duplicate_running_blocked(self):
        store = InMemoryJobStore()
        store._running.add(("trades", "202605"))          # 이미 진행 중 상황
        svc = self._svc({"trades": lambda td: []}, store)
        with self.assertRaises(CollectionJobService.DuplicateCollection):
            svc.run("trades", "202605")                   # CD-INV01


class MolitParser(unittest.TestCase):
    # 현행 Dev API 실응답 구조(영문 태그 + header). 정상 1건 + 해제거래 1건(제외돼야 함).
    SAMPLE = """<response>
      <header><resultCode>000</resultCode><resultMsg>OK</resultMsg></header>
      <body><items>
        <item>
          <aptNm>은마</aptNm><dealAmount> 120,000</dealAmount><excluUseAr>84.97</excluUseAr>
          <floor>15</floor><dealYear>2026</dealYear><dealMonth>5</dealMonth><dealDay>20</dealDay>
          <sggCd>11680</sggCd><umdNm>대치동</umdNm><buildYear>1979</buildYear><cdealType></cdealType>
        </item>
        <item>
          <aptNm>래미안</aptNm><dealAmount>350,000</dealAmount><excluUseAr>94.5</excluUseAr>
          <floor>20</floor><dealYear>2026</dealYear><dealMonth>5</dealMonth><dealDay>22</dealDay>
          <sggCd>11680</sggCd><umdNm>대치동</umdNm><cdealType>O</cdealType><cdealDay>26</cdealDay>
        </item>
      </items><totalCount>2</totalCount></body></response>"""

    ERROR_RESP = """<response>
      <header><resultCode>22</resultCode><resultMsg>LIMITED NUMBER OF SERVICE REQUESTS EXCEEDS</resultMsg></header>
      <body></body></response>"""

    def test_parse_skips_cancelled(self):
        trades = MolitTradesSource.parse(self.SAMPLE)
        self.assertEqual(len(trades), 1)                   # 해제거래(cdealType=O) 제외
        t = trades[0]
        self.assertEqual(t.complex_id, "11680-은마")
        self.assertEqual(t.apt_name, "은마")
        self.assertEqual(t.region_code, "11680")
        self.assertEqual(t.legal_dong, "대치동")
        self.assertEqual(t.price, 1_200_000_000)           # 120,000만원 → 12억원
        self.assertEqual(t.area_m2, 84.97)
        self.assertEqual(t.floor, 15)
        self.assertEqual(t.contract_date, date(2026, 5, 20))

    def test_result_code_error_raises(self):
        # 쿼터초과 등 resultCode 오류 → 예외 → 수집 FAILED(CD-G01)로 이어짐
        with self.assertRaises(ValueError):
            MolitTradesSource.parse(self.ERROR_RESP)


if __name__ == "__main__":
    unittest.main()
