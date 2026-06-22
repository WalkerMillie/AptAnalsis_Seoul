"""[HAND-WRITTEN] analysis DRF 뷰 (web adapter).

§2: 비즈니스 로직 금지 — application 유스케이스만 호출한다.
도메인 직접 import 금지(check의 boundary가 막는다). 표 로딩은 어댑터 로더로 주입.
"""

from dataclasses import asdict
from datetime import date

from rest_framework.response import Response
from rest_framework.views import APIView

from contexts.analysis.application import AnalysisService
from contexts.analysis.adapters.an_dt01_loader import load_an_dt01_table
from contexts.analysis.adapters.an_dt02_loader import load_an_dt02_table
from contexts.analysis.adapters.web.serializers import (
    AnalyzeRequestSerializer,
    AnalyzeResponseSerializer,
)

# 합성 루트: 어댑터 로더로 표를 만들어 유스케이스에 주입(한 번만 로드).
_service = None


def get_service() -> AnalysisService:
    global _service
    if _service is None:
        _service = AnalysisService(load_an_dt01_table(), load_an_dt02_table())
    return _service


class AnalysisView(APIView):
    def post(self, request):
        req = AnalyzeRequestSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        d = req.validated_data
        result = get_service().analyze(
            purchase_price=d["purchase_price"],
            loan_amount=d["loan_amount"],
            equity=d["equity"],
            effective_rate=d["effective_rate"],
            assumed_growth=d["assumed_growth"],
            complex_id=d["complex_id"],
            as_of=d.get("as_of") or date.today(),
            holding_years=d.get("holding_years", 2.0),
            opportunity_rate=d.get("opportunity_rate", 0.03),
            is_first_home=d.get("is_first_home", True),
        )
        return Response(AnalyzeResponseSerializer(asdict(result)).data)
