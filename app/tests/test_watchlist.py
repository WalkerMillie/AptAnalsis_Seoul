"""관심 단지(워치리스트) API 검증 — DB 영속 CRUD + 멱등 등록.

비교(A vs B) 기능의 그릇. 등록은 멱등(중복 무해), 해제는 실제 삭제, owner 슬롯 분리.
"""
from django.test import TestCase
from rest_framework.test import APIClient

from contexts.watchlist.adapters.db.models import WatchItemRecord

URL = "/api/watchlist/items/"
EUNMA = {"complex_id": "11680-은마", "apt_name": "은마",
         "region_code": "11680", "legal_dong": "대치동"}


class WatchlistApiTest(TestCase):
    def setUp(self):
        self.c = APIClient()

    def test_empty_initially(self):
        self.assertEqual(self.c.get(URL).json(), {"items": []})

    def test_add_then_list(self):
        r = self.c.post(URL, EUNMA, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.json()["created"])
        items = self.c.get(URL).json()["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["complex_id"], "11680-은마")
        self.assertEqual(items[0]["legal_dong"], "대치동")   # 비정규화 메타 보존

    def test_add_is_idempotent(self):
        self.c.post(URL, EUNMA, format="json")
        r = self.c.post(URL, EUNMA, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["created"])               # 중복은 created=False
        self.assertEqual(WatchItemRecord.objects.count(), 1)  # 행은 1개뿐

    def test_remove(self):
        self.c.post(URL, EUNMA, format="json")
        r = self.c.delete(URL + "?complex_id=11680-은마")
        self.assertTrue(r.json()["removed"])
        self.assertEqual(self.c.get(URL).json(), {"items": []})

    def test_remove_absent_is_false(self):
        r = self.c.delete(URL + "?complex_id=11680-없는단지")
        self.assertFalse(r.json()["removed"])

    def test_add_requires_fields(self):
        r = self.c.post(URL, {"complex_id": "11680-은마"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_delete_requires_complex_id(self):
        self.assertEqual(self.c.delete(URL).status_code, 400)

    def test_recent_first_ordering(self):
        self.c.post(URL, EUNMA, format="json")
        self.c.post(URL, {"complex_id": "11710-잠실엘스", "apt_name": "잠실엘스",
                          "region_code": "11710", "legal_dong": "잠실동"}, format="json")
        ids = [i["complex_id"] for i in self.c.get(URL).json()["items"]]
        self.assertEqual(ids[0], "11710-잠실엘스")          # 최근 등록 먼저
