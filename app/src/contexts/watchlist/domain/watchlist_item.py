"""[GENERATED 골격 + impl 보호구역] WatchlistItem Aggregate (B형).

상태 머신은 생성됨. 가드/불변식/도메인 메서드는 impl 블록에서 채운다(§6).
"""

from contexts.watchlist.domain.watchlist_item_state import ALLOWED, WatchlistItemState
from contexts.watchlist.domain.exceptions import IllegalTransition, InvariantViolation  # noqa: F401


class WatchlistItem:
    def __init__(self, state: WatchlistItemState = WatchlistItemState.WATCHING):
        self.state = state

    # >>> generated: do-not-edit
    def _transition(self, to: WatchlistItemState) -> None:
        if to not in ALLOWED[self.state]:
            raise IllegalTransition(self.state, to)
        self.state = to
    # <<< generated

    # >>> impl: editable  (AI 바이브코딩은 여기만)
    @classmethod
    def create(cls, user_id: int, complex_id: int) -> "WatchlistItem":
        """관심 단지 등록. 등록 직후는 WATCHING(분석 가능).

        WL-INV01(동일 (user, complex) 1개)은 단일 애그리거트로 보장 불가 —
        영속화 계층(repository unique 제약 / application 유스케이스)에서 강제한다.
        """
        item = cls()
        item.user_id = user_id
        item.complex_id = complex_id
        return item

    def evaluate_gate(self, listing_count: int) -> None:
        """매물 카운트로 게이트를 재평가한다. 매물=조사의 시작 신호(기획서 §1.3).

        WL-G01: WATCHING + 매물 0  → GATE_LOCKED (잠김, 깊은 분석 보류)
        WL-G02: GATE_LOCKED + 매물≥1 → WATCHING (잠김 해제)
        그 외(이미 일치하는 상태)는 무전이. 실제 상태변경은 방어선 A(_transition) 경유.
        """
        if listing_count < 0:
            raise InvariantViolation("listing_count는 음수일 수 없다")
        if self.state is WatchlistItemState.WATCHING and listing_count == 0:
            self._transition(WatchlistItemState.GATE_LOCKED)   # WL-G01
        elif self.state is WatchlistItemState.GATE_LOCKED and listing_count >= 1:
            self._transition(WatchlistItemState.WATCHING)      # WL-G02

    @property
    def is_locked(self) -> bool:
        """잠김(매물 0)이면 깊은 분석을 보류해야 한다."""
        return self.state is WatchlistItemState.GATE_LOCKED
    # <<< impl
