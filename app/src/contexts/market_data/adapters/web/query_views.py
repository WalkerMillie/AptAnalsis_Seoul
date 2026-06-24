"""[HAND-WRITTEN] market_data 드릴다운 조회 뷰 (동·단지, web adapter).

§2: application(TradeQueryService)만 호출, 도메인 직접 import 금지(check boundary).
수집(collection_job)과 같은 스토어를 합성루트에서 공유받는다.
"""

from rest_framework.response import Response
from rest_framework.views import APIView

from contexts.market_data.adapters.web.composition import get_trade_query


class DongListView(APIView):
    """GET /api/market_data/dongs/?region_code=11680 — 거래 있는 동(드릴다운 2단계)."""

    def get(self, request):
        region_code = request.query_params.get("region_code", "")
        if not region_code:
            return Response({"detail": "region_code 필수"}, status=400)
        return Response({"region_code": region_code,
                         "dongs": get_trade_query().dongs(region_code)})


class ComplexListView(APIView):
    """GET /api/market_data/complexes/?region_code=11680&dong=대치동 — 단지(거래빈도순, 3단계)."""

    def get(self, request):
        region_code = request.query_params.get("region_code", "")
        dong = request.query_params.get("dong", "")
        if not region_code or not dong:
            return Response({"detail": "region_code, dong 필수"}, status=400)
        return Response({"region_code": region_code, "dong": dong,
                         "complexes": get_trade_query().complexes(region_code, dong)})


class DongSearchView(APIView):
    """GET /api/market_data/search_dongs/?q=대치 — 전체 구 횡단 동 검색(거래빈도순)."""

    def get(self, request):
        q = request.query_params.get("q", "")
        if not q.strip():
            return Response({"detail": "q 필수"}, status=400)
        return Response({"q": q, "matches": get_trade_query().search_dongs(q)})


class TradeListView(APIView):
    """GET /api/market_data/trades/?complex_id=11680-은마 — 단지 최근 실거래(계약일 내림차순)."""

    def get(self, request):
        complex_id = request.query_params.get("complex_id", "")
        if not complex_id:
            return Response({"detail": "complex_id 필수"}, status=400)
        return Response({"complex_id": complex_id,
                         "trades": get_trade_query().trades(complex_id)})


def _months(request) -> int:
    """months 쿼리 파라미터(기본 3, 1~60으로 클램프). 장기 데이터(2~4년) 대비 상한 상향."""
    try:
        m = int(request.query_params.get("months", 3))
    except (TypeError, ValueError):
        m = 3
    return max(1, min(60, m))


class PriceSeriesView(APIView):
    """GET /api/market_data/price_series/?complex_id=..&months=12 — 월별 ㎡가 시계열(차트용)."""

    def get(self, request):
        complex_id = request.query_params.get("complex_id", "")
        if not complex_id:
            return Response({"detail": "complex_id 필수"}, status=400)
        return Response(get_trade_query().price_series(complex_id, _months(request)))


class PriceGrowthView(APIView):
    """GET /api/market_data/price_growth/?complex_id=..&months=6 — 단지 실제 연환산 상승률(A안)."""

    def get(self, request):
        complex_id = request.query_params.get("complex_id", "")
        if not complex_id:
            return Response({"detail": "complex_id 필수"}, status=400)
        return Response(get_trade_query().price_growth(complex_id, _months(request)))


class RegionSummaryView(APIView):
    """GET /api/market_data/region_summary/?months=12&min_trades=10 — 구별 상승률 중앙값(지도용)."""

    def get(self, request):
        try:
            mt = int(request.query_params.get("min_trades", 10))
        except (TypeError, ValueError):
            mt = 10
        return Response(get_trade_query().region_summary(_months(request), max(1, min(1000, mt))))


class RankingView(APIView):
    """GET /api/market_data/rankings/?months=12&min_trades=10&limit=100 — 서울 전 단지 상승률 랭킹."""

    def get(self, request):
        def _int(name, default, lo, hi):
            try:
                v = int(request.query_params.get(name, default))
            except (TypeError, ValueError):
                v = default
            return max(lo, min(hi, v))
        return Response(get_trade_query().rank_complexes(
            months=_months(request),
            min_trades=_int("min_trades", 10, 1, 1000),
            limit=_int("limit", 100, 1, 500)))


class JeonseRatioView(APIView):
    """GET /api/market_data/jeonse_ratio/?complex_id=..&months=12 — 단지 전세가율(평형 정규화)."""

    def get(self, request):
        complex_id = request.query_params.get("complex_id", "")
        if not complex_id:
            return Response({"detail": "complex_id 필수"}, status=400)
        return Response(get_trade_query().jeonse_ratio(complex_id, _months(request)))


class CandidateMetricsView(APIView):
    """GET /api/market_data/candidates/?months=12&min_trades=10 — 전 단지 다지표(가중치 랭킹용)."""

    def get(self, request):
        try:
            mt = int(request.query_params.get("min_trades", 10))
        except (TypeError, ValueError):
            mt = 10
        return Response(get_trade_query().candidate_metrics(
            _months(request), max(1, min(1000, mt))))


class JeonseSeriesView(APIView):
    """GET /api/market_data/jeonse_series/?complex_id=..&months=12 — 월별 전세 ㎡당 보증금 추세."""

    def get(self, request):
        complex_id = request.query_params.get("complex_id", "")
        if not complex_id:
            return Response({"detail": "complex_id 필수"}, status=400)
        return Response(get_trade_query().jeonse_series(complex_id, _months(request)))


class ComplexScoreView(APIView):
    """GET /api/market_data/complex_scores/?region_code=..&dong=..&months=6 — 단지별 상승률(비교/정렬)."""

    def get(self, request):
        region_code = request.query_params.get("region_code", "")
        dong = request.query_params.get("dong", "")
        if not region_code or not dong:
            return Response({"detail": "region_code, dong 필수"}, status=400)
        return Response({"region_code": region_code, "dong": dong, "months": _months(request),
                         "complexes": get_trade_query().complex_growth_scores(
                             region_code, dong, _months(request))})
