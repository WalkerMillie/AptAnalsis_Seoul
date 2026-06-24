"""[HAND-WRITTEN] analysis 직렬화기 (web adapter). 요청 파싱/응답 형태만."""

from rest_framework import serializers


class AnalyzeRequestSerializer(serializers.Serializer):
    purchase_price = serializers.FloatField(min_value=1)       # 매매가(원)
    loan_amount = serializers.FloatField(min_value=0)          # 대출액(원)
    equity = serializers.FloatField(min_value=1)               # 자기자본(원)
    effective_rate = serializers.FloatField(min_value=0)       # 실효금리(소수)
    assumed_growth = serializers.FloatField()                  # 가정 연 상승률(소수)
    complex_id = serializers.CharField()                       # 단지 ID
    as_of = serializers.DateField(required=False)              # 기준일(생략시 오늘)
    holding_years = serializers.FloatField(min_value=0.5, required=False, default=2.0)  # 보유기간(년)
    opportunity_rate = serializers.FloatField(min_value=0, required=False, default=0.03)  # 자기자본 기회비용률
    is_first_home = serializers.BooleanField(required=False, default=True)  # 1주택(양도세 비과세 판정)
    # 전세가율(소수). 생략 시 뷰가 해당 단지 실거래로 자동 산정. 자택 거주가치 반영용.
    jeonse_ratio = serializers.FloatField(min_value=0, required=False, allow_null=True)


class AnalyzeResponseSerializer(serializers.Serializer):
    breakeven_rate = serializers.FloatField()
    interest_breakeven = serializers.FloatField()
    net_profit = serializers.FloatField()
    roe = serializers.FloatField()
    stress_rate = serializers.FloatField()
    max_loan_amount = serializers.IntegerField()
    ltz_applies = serializers.BooleanField(allow_null=True)
    is_profitable = serializers.BooleanField()
    breakeven_margin = serializers.FloatField()
    first_home_exempt = serializers.BooleanField()
    costs = serializers.DictField()
    # 거주가치(자택) 반영 — 전세가율이 있을 때만 의미. 없으면 투자관점과 동일.
    jeonse_ratio = serializers.FloatField(allow_null=True)
    residence_value = serializers.FloatField()           # 보유기간 누적 거주가치(원)
    net_profit_residence = serializers.FloatField()       # 거주가치 포함 순익(원)
    roe_residence = serializers.FloatField()
    breakeven_rate_residence = serializers.FloatField()   # 거주가치 포함 손익분기 상승률
    is_profitable_residence = serializers.BooleanField()
