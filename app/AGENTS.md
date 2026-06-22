# AGENTS.md — 이 프로젝트에서 바이브코딩하는 규칙

이 골격은 HexaArch가 `domain-spec.yaml`에서 **결정론적으로 생성**했다.
계속 코드를 짜되 아래 규칙을 깨면 `hexaarch check`가 빌드를 막는다.

## 컨텍스트 (바운디드)
- **watchlist** — WatchlistItem
- **region** — Region, Complex
- **market_data** — CollectionJob, Trade, Rate, ListingSnapshot
- **analysis** — BreakevenCalc, LeverageROE, StressDSR

## 절대 규칙
1. **impl 블록 안에서만 짠다.** `>>> impl: editable` ~ `<<< impl` 사이가 네 영역이다.
   그 밖(상태표·`_transition`·예외·전이/경계 테스트·결정표 헤더)은 생성 영역 —
   고치려면 코드가 아니라 `domain-spec.yaml`을 고치고 재생성한다.
2. **도메인은 아무것도 import하지 않는다.** `contexts/*/domain/`은 어댑터·인프라·
   타 컨텍스트를 import 금지 (금지어: adapters, application, .ports, django, rest_framework, sqlalchemy, requests, httpx, celery, redis).
   크로스 컨텍스트 데이터는 값(VO)으로 주입받고, 동기 조회는 합성 루트에서 배선한다.
3. **상태 전이는 스펙이 정한 것만.** 새 상태/전이가 필요하면 스펙을 고친다.
4. **새 파일은 자유.** 유스케이스·VO·어댑터 등 프레임워크가 안 만든 파일은 마음껏 추가.
   단 도메인 디렉터리에 두면 규칙 2가 적용된다.

## 매 편집 후
```
hexaarch check domain-spec.yaml .
```
위반 0이어야 한다. drift = 생성 영역을 건드림 / boundary = 경계 침범 / missing = 골격 삭제.
