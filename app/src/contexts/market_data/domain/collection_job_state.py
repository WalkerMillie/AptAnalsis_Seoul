"""[GENERATED] CollectionJob 상태 + 전이 테이블. 방어선 A. 스펙에서 결정론 생성 — 직접 수정 금지."""

from enum import Enum, auto


class CollectionJobState(Enum):
    PENDING = auto()
    RUNNING = auto()
    DONE = auto()
    FAILED = auto()

ALLOWED = {
    CollectionJobState.PENDING: { CollectionJobState.RUNNING },
    CollectionJobState.RUNNING: { CollectionJobState.DONE, CollectionJobState.FAILED },
    CollectionJobState.DONE: {  },
    CollectionJobState.FAILED: { CollectionJobState.PENDING },
}
