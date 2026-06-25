"""[HAND-WRITTEN] analysis DRF 뷰 (web adapter).

§2: 비즈니스 로직 금지 — application 유스케이스만 호출한다.
도메인 직접 import 금지(check의 boundary가 막는다). 표 로딩은 어댑터 로더로 주입.
"""

from dataclasses import asdict
from datetime import date

from rest_framework.response import Response
from rest_framework.views import APIView

from contexts.analysis.application import AICommentService, AnalysisService
from contexts.analysis.adapters.an_dt01_loader import load_an_dt01_table
from contexts.analysis.adapters.an_dt02_loader import load_an_dt02_table
from contexts.analysis.adapters.llm_cli import make_llm_client
from contexts.analysis.adapters.web.serializers import (
    AICommentRequestSerializer,
    AnalyzeRequestSerializer,
    AnalyzeResponseSerializer,
)

# 합성 루트: 어댑터 로더로 표를 만들어 유스케이스에 주입(한 번만 로드).
_service = None
_ai_service = None


def get_service() -> AnalysisService:
    global _service
    if _service is None:
        _service = AnalysisService(load_an_dt01_table(), load_an_dt02_table())
    return _service


def get_ai_service() -> AICommentService:
    global _ai_service
    if _ai_service is None:
        _ai_service = AICommentService(make_llm_client())
    return _ai_service


class AnalysisView(APIView):
    def post(self, request):
        req = AnalyzeRequestSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        d = req.validated_data
        # 전세가율은 명시 입력(없으면 거주가치 0=투자관점). 분석 엔드포인트는 DB-free 유지 —
        # UI가 /api/market_data/jeonse_ratio/ 로 먼저 조회해 값을 넘긴다(합성은 프론트가).
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
            jeonse_ratio=d.get("jeonse_ratio"),
            conversion_rate=d.get("conversion_rate"),
        )
        return Response(AnalyzeResponseSerializer(asdict(result)).data)


class AICommentView(APIView):
    """온디맨드 AI 코멘트. 실패해도 200 + {ok:false, message} — FE가 부드럽게 노출(500 없음)."""

    def post(self, request):
        req = AICommentRequestSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        result = get_ai_service().comment(dict(req.validated_data))
        return Response(asdict(result))
