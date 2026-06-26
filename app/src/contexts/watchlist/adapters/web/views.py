"""[HAND-WRITTEN] watchlist DRF 뷰 (web adapter).

§2: 비즈니스 로직 금지 — application 유스케이스만 호출. 도메인 직접 import 금지(boundary).
GET 조회 / POST 등록 / DELETE 해제 한 엔드포인트(/items/).
"""

from rest_framework.response import Response
from rest_framework.views import APIView

from contexts.watchlist.adapters.web.composition import get_watchlist_service
from contexts.watchlist.adapters.web.serializers import WatchlistItemSerializer


class WatchlistItemsView(APIView):
    """GET/POST/DELETE /api/watchlist/items/ — 관심 단지 목록·등록·해제."""

    def get(self, request):
        return Response({"items": get_watchlist_service().list()})

    def post(self, request):
        s = WatchlistItemSerializer(data=request.data)
        if not s.is_valid():
            return Response(s.errors, status=400)
        created = get_watchlist_service().add(**s.validated_data)
        return Response({"created": created}, status=201 if created else 200)

    def delete(self, request):
        complex_id = request.query_params.get("complex_id", "")
        if not complex_id:
            return Response({"detail": "complex_id 필수"}, status=400)
        removed = get_watchlist_service().remove(complex_id)
        return Response({"removed": removed})
