# 서울 아파트 매매 의사결정 분석 플랫폼

서울 25개 자치구 아파트 실거래가(MOLIT 공공데이터)를 수집해, **"지금 이 단지를 사면 손익분기를 넘기는가"** 를 비용 포함 모델로 판단하고 단지·구별로 비교·랭킹하는 웹 플랫폼.

[HexaArch](https://github.com/WalkerMillie/HexaArchCli)로 뽑은 헥사고날 골격 위에 빌드. 도메인 코어(판단·계산)와 어댑터(I/O)가 분리돼 있고, `check` 가드가 경계 위반을 차단한다.

## 핵심 기능
- **실거래 수집** — MOLIT API에서 25개 구 × 다월 백필 (`app/backfill.py`)
- **가격 성장률** — 평형 정규화 + 기간 변화율(period_change), 표본 신뢰도 게이트
- **손익분기 분석(B안)** — 취득세·중개·양도세·이자·보유세·기회비용 전부 반영한 순손익/ROE
- **단지 랭킹 & 서울 지도** — 손익분기 초과율을 절대 지표로 점수화, 구별 코로플레스(인라인 SVG)
- **건축년도** 등 단지 상세

## 셋업
```bash
cd app
python3 -m venv ../.venv
../.venv/bin/pip install -r requirements.txt

# 환경변수: app/.env 에 MOLIT 서비스키가 들어 있음(data.go.kr 무료 공공 키).
#   본인 키로 바꾸려면 data.go.kr → "아파트 매매 실거래가 자료" 신청 후 교체.

../.venv/bin/python manage.py migrate
# 백필은 항상 매매(trades) + 전세(rents) 둘 다 채워야 한다.
#   전세가율·거주가치(buy-vs-rent)·추천 페이지가 전세 데이터에 의존한다.
../.venv/bin/python backfill.py trades 202406 202407 ... 202605   # 매매(약 8분/12개월)
../.venv/bin/python backfill.py rents  202406 202407 ... 202605   # 전세(같은 기간)
../.venv/bin/python manage.py runserver 0.0.0.0:8000
```
→ 브라우저에서 `http://localhost:8000`

> **DB는 레포에 없음.** `db.sqlite3`는 재수집 가능한 데이터라 git에서 제외했다. 위 `backfill.py`로 채운다.
>
> **백필 = 매매 + 전세 한 쌍.** `backfill.py trades …`만 돌리면 전세가율/거주가치/추천이 비어 보인다.
> 인자 없이 `backfill.py`(기본 3개월 매매)만 쓰지 말 것. Docker 첫 기동(`entrypoint.sh`)은 이미 둘 다 시딩한다.

## 구조
```
app/
  src/contexts/
    market_data/   # 수집·조회 (domain / application / adapters)
    analysis/      # 손익분기·비용 모델 (cost_model, analysis_service)
  config/          # Django 설정·URL
  web_ui/          # 단일 페이지 프론트(인라인 SVG 지도·차트)
  backfill.py      # 운영 백필 도구
domain-spec.yaml   # HexaArch 도메인 명세
docs/planning.md   # 설계 문서
```

## 테스트
```bash
cd app && ../.venv/bin/python manage.py test
```

## 데이터 출처
국토교통부 실거래가 공개시스템 (data.go.kr `RTMSDataSvcAptTrade`).
