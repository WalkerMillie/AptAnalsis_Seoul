"""[GENERATED 골격] market_data DRF 뷰 (web adapter).

§2: 비즈니스 로직 금지 — application 유스케이스만 호출한다.
도메인 직접 import 금지(check의 boundary가 막는다). 반드시 서비스를 통해서.
"""

from rest_framework.response import Response
from rest_framework.views import APIView

from contexts.market_data.application import (
    CollectionJobService,
)
from contexts.market_data.adapters.web.serializers import (
    CollectionJobSerializer,
)


class CollectionJobView(APIView):
    # >>> impl: editable (요청 파싱 → 서비스 호출 → 응답. 판단/계산 금지)
    def post(self, request):
        # 합성 루트(포트 구현체 주입)는 web 어댑터의 별도 모듈에서 — 도메인 직접 import 안 함.
        from contexts.market_data.adapters.web.composition import get_service
        req = CollectionJobSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        d = req.validated_data
        try:
            job = get_service().run(d["job_type"], d["target_date"])
        except CollectionJobService.DuplicateCollection as exc:
            return Response({"detail": str(exc)}, status=409)
        return Response({
            "job_type": job.job_type,
            "target_date": job.target_date,
            "state": job.state.name,
            "fetched_count": job.fetched_count,
            "error": job.error,
        })
    # <<< impl
