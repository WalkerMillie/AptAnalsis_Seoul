"""[HAND-WRITTEN] 데모 UI 전달 (delivery shell).

순수 표현용 인바운드 어댑터 — 정적 HTML 한 장을 반환할 뿐, 비즈니스 로직 없음.
브라우저가 JSON API(/api/...)를 호출한다. 컨텍스트 횡단이라 config(전달 셸)에 둔다.
"""

from pathlib import Path

from django.http import Http404, HttpResponse

_WEB_UI = Path(__file__).resolve().parent.parent / "web_ui"
_INDEX = _WEB_UI / "index.html"
_MOCKUPS = _WEB_UI / "mockups"
_SUBWAY_NEAR = _WEB_UI / "subway_near.json"


def index(request):
    return HttpResponse(_INDEX.read_text(encoding="utf-8"))


def subway_near(request):
    """동(법정동) 중심 기준 최근접 지하철역 사전계산표(키리스 정적 데이터).
    좌표 출처: korean-geocoding(행정구역 centroid) + 공공데이터 1~8호선 역좌표.
    동 단위 근사치 — 정밀 최근접은 단지 지오코딩(차기) 필요."""
    return HttpResponse(_SUBWAY_NEAR.read_text(encoding="utf-8"),
                        content_type="application/json")


def mockups(request, name=""):
    """디자인 시안 갤러리·개별 시안(web_ui/mockups/*.html) 정적 전달. 평가용 임시 라우트."""
    target = (_MOCKUPS / (name or "index.html")).resolve()
    # 디렉터리 이탈 방지 + .html만 허용.
    if _MOCKUPS not in target.parents or target.suffix != ".html" or not target.is_file():
        raise Http404("시안 없음")
    return HttpResponse(target.read_text(encoding="utf-8"))
