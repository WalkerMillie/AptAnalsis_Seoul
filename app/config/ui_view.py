"""[HAND-WRITTEN] 데모 UI 전달 (delivery shell).

순수 표현용 인바운드 어댑터 — 정적 HTML 한 장을 반환할 뿐, 비즈니스 로직 없음.
브라우저가 JSON API(/api/...)를 호출한다. 컨텍스트 횡단이라 config(전달 셸)에 둔다.
"""

import json
from pathlib import Path

from django.http import Http404, HttpResponse, JsonResponse

_WEB_UI = Path(__file__).resolve().parent.parent / "web_ui"
_INDEX = _WEB_UI / "index.html"
_MOCKUPS = _WEB_UI / "mockups"
_COMPLEX_GEO = _WEB_UI / "complex_geo.json"

_complex_geo_cache = None


def index(request):
    return HttpResponse(_INDEX.read_text(encoding="utf-8"))


def complex_geo(request):
    """단지별 정확좌표·전노선 최근접역 사전계산표(Kakao 1회 배치). ?cid=로 단건 반환.
    1.1MB 전체를 안 보내려고 서버가 메모리에 1회 로드 후 단건만 응답."""
    global _complex_geo_cache
    if _complex_geo_cache is None:
        _complex_geo_cache = json.loads(_COMPLEX_GEO.read_text(encoding="utf-8"))
    cid = request.GET.get("cid", "")
    rec = _complex_geo_cache.get(cid)
    if rec is None:
        return JsonResponse({"found": False})
    return JsonResponse({"found": True, **rec})


def mockups(request, name=""):
    """디자인 시안 갤러리·개별 시안(web_ui/mockups/*.html) 정적 전달. 평가용 임시 라우트."""
    target = (_MOCKUPS / (name or "index.html")).resolve()
    # 디렉터리 이탈 방지 + .html만 허용.
    if _MOCKUPS not in target.parents or target.suffix != ".html" or not target.is_file():
        raise Http404("시안 없음")
    return HttpResponse(target.read_text(encoding="utf-8"))
