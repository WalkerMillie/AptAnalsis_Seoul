"""[GENERATED 골격] watchlist DRF 뷰 (web adapter).

§2: 비즈니스 로직 금지 — application 유스케이스만 호출한다.
도메인 직접 import 금지(check의 boundary가 막는다). 반드시 서비스를 통해서.
"""

from rest_framework.response import Response
from rest_framework.views import APIView

from contexts.watchlist.application import (
    WatchlistItemService,
)
from contexts.watchlist.adapters.web.serializers import (
    WatchlistItemSerializer,
)


class WatchlistItemView(APIView):
    # >>> impl: editable (요청 파싱 → 서비스 호출 → 응답. 판단/계산 금지)
    def post(self, request):
        raise NotImplementedError
    # <<< impl
