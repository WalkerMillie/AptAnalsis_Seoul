"""[HAND-WRITTEN] region DRF 뷰 (web adapter).

§2: application 유스케이스만 호출, 도메인 직접 import 금지(check boundary).
"""

from rest_framework.response import Response
from rest_framework.views import APIView

from contexts.region.application import RegionQueryService

_service = RegionQueryService()


class DistrictListView(APIView):
    """GET /api/region/districts/ — 서울 자치구 목록(드릴다운 1단계)."""

    def get(self, request):
        return Response({"districts": _service.districts()})
