"""[GENERATED 골격 + impl 보호구역] CollectionJob Aggregate (B형).

상태 머신은 생성됨. 가드/불변식/도메인 메서드는 impl 블록에서 채운다(§6).
"""

from contexts.market_data.domain.collection_job_state import ALLOWED, CollectionJobState
from contexts.market_data.domain.exceptions import IllegalTransition, InvariantViolation  # noqa: F401


class CollectionJob:
    def __init__(self, state: CollectionJobState = CollectionJobState.PENDING):
        self.state = state

    # >>> generated: do-not-edit
    def _transition(self, to: CollectionJobState) -> None:
        if to not in ALLOWED[self.state]:
            raise IllegalTransition(self.state, to)
        self.state = to
    # <<< generated

    # >>> impl: editable  (AI 바이브코딩은 여기만)
    @classmethod
    def create(cls, job_type: str, target_date) -> "CollectionJob":
        """수집 잡 생성 — PENDING으로 시작. (job_type, target_date)가 식별자."""
        job = cls()
        job.job_type = job_type
        job.target_date = target_date
        job.fetched_count = 0
        job.error = None
        return job

    def start(self) -> None:
        """PENDING → RUNNING. CD-INV01(동시 RUNNING 1개)은 스토어가 강제 — application에서 enforce."""
        self._transition(CollectionJobState.RUNNING)

    def succeed(self, fetched_count: int) -> None:
        """RUNNING → DONE. 수집 건수 기록."""
        if fetched_count < 0:
            raise InvariantViolation("fetched_count는 음수일 수 없다")
        self.fetched_count = fetched_count
        self._transition(CollectionJobState.DONE)

    def fail(self, reason: str) -> None:
        """RUNNING → FAILED. CD-G01: 외부 API 오류·쿼터 초과·타임아웃."""
        self.error = reason
        self._transition(CollectionJobState.FAILED)

    def retry(self) -> None:
        """FAILED → PENDING. 재시도 준비(에러 초기화)."""
        self.error = None
        self._transition(CollectionJobState.PENDING)
    # <<< impl
