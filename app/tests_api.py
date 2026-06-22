"""분석 API 엔드포인트 스모크 테스트 (DRF).

Django 설정이 필요하므로 `manage.py test tests_api` 로 실행한다(.venv).
DB 미사용 → SimpleTestCase + APIRequestFactory(URL 라우팅·미들웨어 우회).
web→application→domain 경계로 호출돼 같은 결과가 나오는지 확인.
"""

import os

from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIRequestFactory

from contexts.market_data.adapters.web import composition


def _force_fake_sources():
    """테스트는 네트워크 없이 fake 소스로 — 실키가 .env에 있어도 무시, 스토어 격리."""
    os.environ.pop("MOLIT_SERVICE_KEY", None)
    composition._store = None

from contexts.analysis.adapters.web.views import AnalysisView
from contexts.market_data.adapters.web.views import CollectionJobView
from contexts.market_data.adapters.web.query_views import (
    ComplexListView, DongListView, TradeListView,
)
from contexts.region.adapters.web.views import DistrictListView


class AnalysisAPITest(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_evaluate_ok(self):
        payload = {
            "purchase_price": 1_000_000_000, "loan_amount": 600_000_000,
            "equity": 400_000_000, "effective_rate": 0.05, "assumed_growth": 0.05,
            "complex_id": "GANGNAM-DAECHI-001", "as_of": "2026-06-20",
        }
        request = self.factory.post("/api/analysis/evaluate/", payload, format="json")
        response = AnalysisView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertAlmostEqual(response.data["interest_breakeven"], 0.03)   # 이자만(참고)
        self.assertGreater(response.data["breakeven_rate"], 0.03)           # 총비용은 더 높음
        self.assertEqual(response.data["max_loan_amount"], 600_000_000)
        self.assertTrue(response.data["ltz_applies"])
        self.assertIn("costs", response.data)
        self.assertFalse(response.data["is_profitable"])   # 연5%는 총비용 손익분기(~6.5%) 미만

    def test_validation_error_returns_400(self):
        request = self.factory.post(
            "/api/analysis/evaluate/", {"purchase_price": -1}, format="json")
        response = AnalysisView.as_view()(request)
        self.assertEqual(response.status_code, 400)


class CollectionAPITest(TestCase):   # DB 사용(영속 스토어) → TestCase(테스트DB, 트랜잭션 롤백)
    def setUp(self):
        self.factory = APIRequestFactory()
        _force_fake_sources()

    def test_trigger_collection_ok(self):
        request = self.factory.post(
            "/api/market_data/collection_job/",
            {"job_type": "trades", "target_date": "202605"}, format="json")
        response = CollectionJobView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["state"], "DONE")
        self.assertGreaterEqual(response.data["fetched_count"], 1)

    def test_bad_job_type_returns_400(self):
        request = self.factory.post(
            "/api/market_data/collection_job/",
            {"job_type": "nope", "target_date": "202605"}, format="json")
        response = CollectionJobView.as_view()(request)
        self.assertEqual(response.status_code, 400)


class DrilldownAPITest(TestCase):    # 수집→DB→드릴다운 → TestCase
    def setUp(self):
        self.factory = APIRequestFactory()
        _force_fake_sources()

    def test_districts(self):
        response = DistrictListView.as_view()(self.factory.get("/api/region/districts/"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["districts"]), 25)

    def test_drilldown_after_collection(self):
        # 수집을 먼저 돌려야 동·단지가 파생된다(같은 인메모리 스토어 공유).
        CollectionJobView.as_view()(self.factory.post(
            "/api/market_data/collection_job/",
            {"job_type": "trades", "target_date": "202605"}, format="json"))
        dongs = DongListView.as_view()(
            self.factory.get("/api/market_data/dongs/", {"region_code": "11680"}))
        self.assertEqual(dongs.status_code, 200)
        self.assertIn("대치동", dongs.data["dongs"])
        comps = ComplexListView.as_view()(self.factory.get(
            "/api/market_data/complexes/", {"region_code": "11680", "dong": "대치동"}))
        self.assertEqual(comps.status_code, 200)
        self.assertEqual(comps.data["complexes"][0]["apt_name"], "은마")  # 거래빈도 최다

    def test_dongs_requires_region_code(self):
        response = DongListView.as_view()(self.factory.get("/api/market_data/dongs/"))
        self.assertEqual(response.status_code, 400)

    def test_trades_for_complex(self):
        # 수집 → 단지의 최근 실거래가 계약일 내림차순으로 나온다.
        CollectionJobView.as_view()(self.factory.post(
            "/api/market_data/collection_job/",
            {"job_type": "trades", "target_date": "202605"}, format="json"))
        comps = ComplexListView.as_view()(self.factory.get(
            "/api/market_data/complexes/", {"region_code": "11680", "dong": "대치동"}))
        cid = comps.data["complexes"][0]["complex_id"]
        trades = TradeListView.as_view()(self.factory.get(
            "/api/market_data/trades/", {"complex_id": cid}))
        self.assertEqual(trades.status_code, 200)
        self.assertGreaterEqual(len(trades.data["trades"]), 1)
        dates = [t["contract_date"] for t in trades.data["trades"]]
        self.assertEqual(dates, sorted(dates, reverse=True))   # 계약일 내림차순

    def test_trades_requires_complex_id(self):
        response = TradeListView.as_view()(self.factory.get("/api/market_data/trades/"))
        self.assertEqual(response.status_code, 400)
