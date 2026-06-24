"""[운영 도구] 실거래 백필 — 여러 달을 순차 수집해 DB를 채운다.

각 달 = CollectionJob 하나(도메인 불변). 한 달 안에서 합성루트가 MOLIT_LAWD_CODES의
25개 구를 순회한다(composition._build_fetchers). 즉 (월 × 25구)를 실수집해 영속.
도메인/유스케이스는 손대지 않는다 — 이 스크립트는 트리거만 반복하는 바깥 도구다.

사용:
  ../.venv/bin/python backfill.py 202603 202604 202605          # 매매(기본)
  ../.venv/bin/python backfill.py rents 202603 202604 202605    # 전세
  ../.venv/bin/python backfill.py            # 매매 기본 월 세트
"""

import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from contexts.market_data.adapters.web.composition import get_service  # noqa: E402

_DEFAULT_MONTHS = ["202603", "202604", "202605"]


def main(job_type: str, months: list[str]) -> None:
    if not os.environ.get("MOLIT_SERVICE_KEY"):
        print("⚠️  MOLIT_SERVICE_KEY 없음 — fake 소스로 백필됩니다(실데이터 아님).")
    total = 0
    for ym in months:
        job = get_service().run(job_type, ym)
        state = job.state.name
        added = job.fetched_count
        total += added if state == "DONE" else 0
        mark = "✓" if state == "DONE" else "✗"
        print(f"{mark} {job_type} {ym}: {state} (+{added}건){' — ' + job.error if job.error else ''}")
    print(f"\n총 추가 {total}건 (기존 행은 idempotent upsert로 중복 안 됨).")


if __name__ == "__main__":
    args = sys.argv[1:]
    job = "trades"
    if args and args[0] in ("trades", "rents"):     # 첫 인자가 job_type이면 분리
        job = args.pop(0)
    main(job, args or _DEFAULT_MONTHS)
