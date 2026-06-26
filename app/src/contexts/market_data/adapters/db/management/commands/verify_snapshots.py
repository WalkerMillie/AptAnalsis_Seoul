"""저장된 집계 스냅샷을 라이브 재계산과 대조 — 드리프트 감지(배포 후 1회 권장).

스냅샷 payload는 라이브 함수 출력을 얼린 것이라 '항상' 같아야 한다. 한 건이라도
다르면(로직 버그·무효화 누락 등) 비정상이므로 비0 종료. CI/배포 게이트에 물릴 수 있다.

  python manage.py verify_snapshots          # 전체 대조
  python manage.py verify_snapshots --quiet   # 불일치만 출력
"""
import json

from django.core.management.base import BaseCommand

from contexts.market_data.adapters.db.models import AggregateSnapshot
from contexts.market_data.adapters.web.composition import get_trade_query


def _norm(obj) -> str:
    """비교용 정규화 — 키 정렬 + 타입 차이(튜플/날짜) 흡수."""
    return json.dumps(obj, sort_keys=True, default=str, ensure_ascii=False)


def _live(q, cache_key: str):
    """cache_key를 파싱해 동일 라이브 호출 재현. 알 수 없는 키는 None."""
    head, *rest = cache_key.split("|")
    p = dict(kv.split("=", 1) for kv in rest if "=" in kv)
    m = int(p["m"]) if "m" in p else 12
    mt = int(p.get("mt", 10))
    lim = int(p.get("lim", 100))
    if head == "rankings":
        return q.rank_complexes(m, mt, lim)
    if head == "region_summary":
        return q.region_summary(m, mt)
    if head == "candidates":
        return q.candidate_metrics(m, mt, lim)
    if head == "ticker":
        return q._ticker_payload()
    return None


class Command(BaseCommand):
    help = "저장된 집계 스냅샷을 라이브 재계산과 대조(드리프트 감지)."

    def add_arguments(self, parser):
        parser.add_argument("--quiet", action="store_true", help="불일치만 출력")

    def handle(self, *args, **opts):
        q = get_trade_query()
        rows = list(AggregateSnapshot.objects.all())
        if not rows:
            self.stdout.write("스냅샷 없음 — 대조할 것 없음.")
            return
        mismatches, unknown = 0, 0
        for r in rows:
            live = _live(q, r.cache_key)
            if live is None:
                unknown += 1
                self.stdout.write(self.style.WARNING(f"? {r.cache_key}: 알 수 없는 키(스킵)"))
                continue
            if _norm(live) == _norm(r.payload):
                if not opts["quiet"]:
                    self.stdout.write(self.style.SUCCESS(f"✓ {r.cache_key}"))
            else:
                mismatches += 1
                self.stdout.write(self.style.ERROR(f"✗ {r.cache_key}: 스냅샷 ≠ 라이브"))
        total = len(rows)
        summary = f"\n대조 {total}건 · 불일치 {mismatches} · 알수없음 {unknown}"
        if mismatches:
            self.stderr.write(self.style.ERROR(summary + " — 실패"))
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS(summary + " — OK"))
