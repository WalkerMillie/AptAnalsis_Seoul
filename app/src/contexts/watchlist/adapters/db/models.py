"""[HAND-WRITTEN] watchlist 영속 모델 (Django ORM). 관심 단지(즐겨찾기) 저장.

owner = 소유자 슬롯. 아직 로그인이 없어 기본 "default"(단일 소유자, CF Access 화이트리스트).
로그인 붙이면 owner=user.id 로 채우기만 하면 사용자별 분리가 된다(스키마 불변).
표시·딥링크에 필요한 단지 메타(이름·구·동)는 등록 시점에 비정규화 저장 — 조회 시 추가 lookup 불필요.
"""

from django.db import models


class WatchItemRecord(models.Model):
    owner = models.CharField(max_length=64, default="default", db_index=True)
    complex_id = models.CharField(max_length=200)
    apt_name = models.CharField(max_length=200)
    region_code = models.CharField(max_length=10)
    legal_dong = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "complex_id"],
                name="uq_watch_owner_complex"),   # 동일 소유자가 같은 단지 중복 등록 금지
        ]
        ordering = ["-created_at"]                # 최근 등록 먼저
