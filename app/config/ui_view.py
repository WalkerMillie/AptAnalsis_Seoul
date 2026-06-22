"""[HAND-WRITTEN] 데모 UI 전달 (delivery shell).

순수 표현용 인바운드 어댑터 — 정적 HTML 한 장을 반환할 뿐, 비즈니스 로직 없음.
브라우저가 JSON API(/api/...)를 호출한다. 컨텍스트 횡단이라 config(전달 셸)에 둔다.
"""

from pathlib import Path

from django.http import HttpResponse

_INDEX = Path(__file__).resolve().parent.parent / "web_ui" / "index.html"


def index(request):
    return HttpResponse(_INDEX.read_text(encoding="utf-8"))
