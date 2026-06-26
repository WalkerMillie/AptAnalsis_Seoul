"""[HAND-WRITTEN] watchlist 직렬화기 (web adapter). 등록 요청 본문 검증."""

from rest_framework import serializers


class WatchlistItemSerializer(serializers.Serializer):
    complex_id = serializers.CharField(max_length=200)
    apt_name = serializers.CharField(max_length=200)
    region_code = serializers.CharField(max_length=10)
    legal_dong = serializers.CharField(max_length=100)
