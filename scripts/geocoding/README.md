# 단지 지오코딩 배치 (재생성용)

`app/web_ui/complex_geo.json` 을 만드는 **1회성 배치**. 결과 JSON은 레포에 커밋되어 런타임엔
Kakao 호출 없이 그대로 서빙된다(`config/ui_view.py:complex_geo`). **배포서버에서 돌릴 필요 없음.**
신규 단지가 늘어 좌표가 빈 경우에만 **로컬에서** 다시 돌려 JSON을 갱신·재커밋한다.

## 무엇을 하나
- DB의 distinct 단지(`complex_id, apt_name, region_code, legal_dong`)를 읽어
- Kakao Local 키워드검색 → 정확좌표, 지하철역 카테고리(SW8) → 전노선 최근접역
- `complex_geo.json = { complex_id: {lat,lng,road,station,line,dist_m,slat,slng,approx?} }`
- DB는 **읽기만** 한다(적재·변경 없음).

## 재생성 절차 (로컬)
```bash
export KAKAO_REST_KEY=<카카오 REST 키>   # app/.env 와 동일
cd scripts/geocoding

# 1) DB에서 단지목록 추출 → complexes.json
docker compose exec -T app python -c "
import sqlite3, json
c=sqlite3.connect('/data/db.sqlite3'); cur=c.cursor()
cur.execute('SELECT complex_id, apt_name, region_code, legal_dong FROM market_data_db_traderecord GROUP BY complex_id')
print(json.dumps([{'cid':r[0],'name':r[1],'rc':r[2],'dong':r[3]} for r in cur.fetchall()], ensure_ascii=False))
" > complexes.json

# 2) 1차 배치(정확좌표 우선) — 재개 가능(complex_geo.json 있으면 이어서)
python3 geocode_complexes.py

# 3) 2차 패스(실패분 이름 정제 재시도, 동단위 근사 허용)
python3 geocode_retry.py

# 4) 산출물 반영
cp complex_geo.json ../../app/web_ui/complex_geo.json
```
`complexes.json` / `complex_geo.json` 중간산출물은 커밋하지 않는다(이 디렉터리는 스크립트만).
최종 `app/web_ui/complex_geo.json` 만 커밋.

## 비용/한도
- 단지당 Kakao 호출 ~2건(키워드+역). 5,746단지 ≈ 1.1만 호출, Kakao 일 10만 한도 내.
- 동시성 8, 429 백오프 내장. 전체 ~수 분.

## 런타임 키 정리
- **complex_geo.json = 정적** → 지도·최근접역은 키 0으로 영구 동작.
- **ODsay 키** = 교통 소요시간(온디맨드) → 배포 env 필수.
- **Kakao 키** = 자유입력 목적지 지오코딩에만 런타임 사용(프리셋만 쓰면 불필요).
