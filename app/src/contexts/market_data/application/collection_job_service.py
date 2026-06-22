"""[GENERATED 골격] CollectionJob 유스케이스 (application). §2: 판단/계산은 도메인에, 여기선 조율만.

도메인 메서드를 호출(로드→전이/계산→저장)할 뿐, if로 규칙을 재구현하지 않는다.
아웃바운드 의존(저장소 등)은 포트로 생성자 주입받는다.
"""

from contexts.market_data.domain.collection_job import CollectionJob


class CollectionJobService:
    # >>> impl: editable (유스케이스 — 도메인 호출만. 판단/계산 금지)
    class DuplicateCollection(Exception):
        """CD-INV01 — 같은 (job_type, target_date) 수집이 이미 진행 중(스토어 강제)."""

    def __init__(self, *, store, fetchers: dict):
        # store: JobStore 포트(has_running/save/upsert), fetchers: {job_type: (target_date)->list}
        self._store = store
        self._fetchers = fetchers

    def run(self, job_type: str, target_date):
        """갱신 트리거: 로드→전이→포트호출→upsert→전이. 규칙은 도메인/스토어가 가진다."""
        if self._store.has_running(job_type, target_date):     # CD-INV01 (스토어 동시성)
            raise self.DuplicateCollection(
                f"({job_type}, {target_date}) 이미 수집 중 — 중복 트리거 차단")
        job = CollectionJob.create(job_type, target_date)
        job.start()                                            # PENDING → RUNNING
        self._store.save(job)                                  # RUNNING 점유(가시성)
        try:
            rows = self._fetchers[job_type](target_date)       # 아웃바운드 포트
            count = self._store.upsert(job_type, rows)         # idempotent upsert
            job.succeed(count)                                 # RUNNING → DONE
        except Exception as exc:                               # CD-G01 경로
            job.fail(str(exc))                                 # RUNNING → FAILED
        self._store.save(job)                                  # 점유 해제 + 상태 반영
        return job
    # <<< impl
