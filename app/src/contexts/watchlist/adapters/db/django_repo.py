"""[HAND-WRITTEN] watchlist 저장소 어댑터 (Django ORM). application이 포트로 주입받는다.

유니크 제약(owner, complex_id)이 중복 등록(WL-INV01)을 DB 레벨에서 보장 — get_or_create로 멱등.
"""

from contexts.watchlist.adapters.db.models import WatchItemRecord


def _to_dict(r: WatchItemRecord) -> dict:
    return {"complex_id": r.complex_id, "apt_name": r.apt_name,
            "region_code": r.region_code, "legal_dong": r.legal_dong,
            "created_at": r.created_at.isoformat()}


class DjangoWatchlistRepo:
    def list(self, owner: str) -> list[dict]:
        return [_to_dict(r) for r in WatchItemRecord.objects.filter(owner=owner)]

    def add(self, owner: str, complex_id: str, apt_name: str,
            region_code: str, legal_dong: str) -> bool:
        """멱등 등록. 새로 만들었으면 True, 이미 있었으면 False."""
        _, created = WatchItemRecord.objects.get_or_create(
            owner=owner, complex_id=complex_id,
            defaults={"apt_name": apt_name, "region_code": region_code,
                      "legal_dong": legal_dong})
        return created

    def remove(self, owner: str, complex_id: str) -> bool:
        n, _ = WatchItemRecord.objects.filter(
            owner=owner, complex_id=complex_id).delete()
        return n > 0
