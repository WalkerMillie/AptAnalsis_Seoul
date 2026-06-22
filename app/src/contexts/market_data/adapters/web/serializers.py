"""[GENERATED 골격] market_data 직렬화기 (web adapter)."""

from rest_framework import serializers


class CollectionJobSerializer(serializers.Serializer):
    # >>> impl: editable (필드 정의)
    job_type = serializers.ChoiceField(choices=["trades", "rates", "listings"])
    target_date = serializers.CharField()   # 소스별 형식(YYYYMM 등). 갱신 대상 기간/일자.
    # <<< impl
