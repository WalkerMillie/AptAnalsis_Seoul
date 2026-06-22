"""[GENERATED 골격] WatchlistItem 유스케이스 (application). §2: 판단/계산은 도메인에, 여기선 조율만.

도메인 메서드를 호출(로드→전이/계산→저장)할 뿐, if로 규칙을 재구현하지 않는다.
아웃바운드 의존(저장소 등)은 포트로 생성자 주입받는다.
"""

from contexts.watchlist.domain.watchlist_item import WatchlistItem


class WatchlistItemService:
    # >>> impl: editable (유스케이스 — 도메인 호출만. 판단/계산 금지)
    def __init__(self, *deps):
        self._deps = deps
    # <<< impl
