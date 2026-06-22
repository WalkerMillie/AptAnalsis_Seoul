"""[GENERATED] WatchlistItem 상태 + 전이 테이블. 방어선 A. 스펙에서 결정론 생성 — 직접 수정 금지."""

from enum import Enum, auto


class WatchlistItemState(Enum):
    WATCHING = auto()
    GATE_LOCKED = auto()

ALLOWED = {
    WatchlistItemState.WATCHING: { WatchlistItemState.GATE_LOCKED },
    WatchlistItemState.GATE_LOCKED: { WatchlistItemState.WATCHING },
}
