"""[HAND-WRITTEN] WatchlistItem 유스케이스 (application). §2: 조율만 — 판단은 도메인/DB 제약에.

관심 단지(즐겨찾기) 등록/해제/조회. 중복 방지(WL-INV01)는 저장소 유니크 제약이 보장하므로
여기선 if로 재구현하지 않는다(멱등 add). 저장소는 포트로 생성자 주입.

참고: 도메인 WatchlistItem 의 매물-카운트 게이트(WATCHING/GATE_LOCKED)는 매물(listing) 데이터
소스가 아직 없어 휴면 상태다. 현재는 순수 즐겨찾기 — 등록 단지는 모두 분석/비교 가능.
"""

DEFAULT_OWNER = "default"   # 로그인 전 단일 소유자 슬롯. 로그인 붙으면 user.id로 대체.


class WatchlistItemService:
    def __init__(self, repo):
        self._repo = repo

    def list(self, owner: str = DEFAULT_OWNER) -> list[dict]:
        return self._repo.list(owner)

    def add(self, complex_id: str, apt_name: str, region_code: str,
            legal_dong: str, owner: str = DEFAULT_OWNER) -> bool:
        """등록(멱등). 새로 추가면 True, 이미 등록돼 있었으면 False."""
        return self._repo.add(owner, complex_id, apt_name, region_code, legal_dong)

    def remove(self, complex_id: str, owner: str = DEFAULT_OWNER) -> bool:
        """해제. 실제로 지웠으면 True, 없던 단지면 False."""
        return self._repo.remove(owner, complex_id)
