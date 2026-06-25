"""Kakao Local 배치: 단지별 정확좌표 + 전노선 최근접역 precompute.
출력: complex_geo.json = { complex_id: {lat,lng,road,station,line,dist_m,slat,slng} }
- 키워드검색(서울 구 동 단지명) → 정확좌표(아파트 우선·구 일치 필터)
- SW8 카테고리검색 → 최근접 지하철역(환승노선 통합)
재개: 기존 출력 있으면 이어서. 429 백오프.
"""
import json, os, sys, time, urllib.parse, urllib.request, threading
from concurrent.futures import ThreadPoolExecutor

KEY = os.environ["KAKAO_REST_KEY"]
SCRATCH = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(SCRATCH, "complex_geo.json")

districts = {d["code"]: d["name"] for d in json.load(open(os.path.join(SCRATCH, "districts.json")))["districts"]}
complexes = json.load(open(os.path.join(SCRATCH, "complexes.json")))

out = {}
if os.path.exists(OUT):
    try:
        out = json.load(open(OUT))
        print(f"재개: 기존 {len(out)}개 로드")
    except Exception:
        out = {}

lock = threading.Lock()
done = len(out)


def kakao(path, params):
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        f"https://dapi.kakao.com/v2/local/{path}?{qs}",
        headers={"Authorization": f"KakaoAK {KEY}"},
    )
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(0.5 * (attempt + 1))
                continue
            raise
        except Exception:
            time.sleep(0.3 * (attempt + 1))
    return None


SEOUL = lambda la, ln: 37.3 < la < 37.8 and 126.6 < ln < 127.3


def geocode(c):
    gu = districts.get(c["rc"], "")
    name = c["name"].strip()
    # jibun-only 이름((627-120) 등)은 동까지만으로 근사
    nm_q = "" if (name.startswith("(") and name.endswith(")")) else name
    q = f"서울 {gu} {c['dong']} {nm_q}".strip()
    d = kakao("search/keyword.json", {"query": q, "size": 15})
    if not d or not d.get("documents"):
        d = kakao("search/keyword.json", {"query": f"서울 {gu} {nm_q}".strip(), "size": 15})
    docs = (d or {}).get("documents", [])
    # 구 일치 + 아파트 우선
    cand = None
    for x in docs:
        addr = x.get("address_name", "") or x.get("road_address_name", "")
        if gu and gu not in addr:
            continue
        la, ln = float(x["y"]), float(x["x"])
        if not SEOUL(la, ln):
            continue
        is_apt = ("아파트" in x.get("category_name", "")) or (nm_q and nm_q in x.get("place_name", ""))
        if cand is None or (is_apt and not cand[2]):
            cand = (la, ln, is_apt, x)
            if is_apt:
                break
    if cand is None:
        return None
    la, ln, _, x = cand
    rec = {"lat": round(la, 6), "lng": round(ln, 6),
           "road": x.get("road_address_name") or x.get("address_name", "")}
    # 최근접역(SW8)
    s = kakao("search/category.json", {"category_group_code": "SW8", "x": x["x"], "y": x["y"],
                                       "radius": 2000, "sort": "distance", "size": 15})
    sdocs = (s or {}).get("documents", [])
    if sdocs:
        # 최근접 역명 그룹의 노선 통합
        first = sdocs[0]
        base = first["place_name"].rsplit(" ", 1)[0]  # "대치역 3호선" → "대치역"
        lines, slat, slng, dist = [], float(first["y"]), float(first["x"]), int(first["distance"])
        for sd in sdocs:
            stn = sd["place_name"].rsplit(" ", 1)
            if stn[0] == base and len(stn) == 2:
                ln_nm = stn[1]
                if ln_nm not in lines:
                    lines.append(ln_nm)
        rec.update({"station": base, "line": "·".join(lines), "dist_m": dist,
                    "slat": round(slat, 6), "slng": round(slng, 6)})
    return rec


def work(c):
    global done
    if c["cid"] in out:
        return
    try:
        rec = geocode(c)
    except Exception as e:
        rec = None
    with lock:
        if rec:
            out[c["cid"]] = rec
        done += 1
        if done % 200 == 0:
            json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
            print(f"  {done}/{len(complexes)} (저장됨, 좌표성공 {len(out)})", flush=True)


todo = [c for c in complexes if c["cid"] not in out]
print(f"대상 {len(todo)} (전체 {len(complexes)}, 기존 {len(out)})")
with ThreadPoolExecutor(max_workers=8) as ex:
    list(ex.map(work, todo))

json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
print(f"완료: 좌표 {len(out)}/{len(complexes)}")
# 샘플
for cid in ["11680-은마", "11710-헬리오시티", "11305-에스케이북한산시티"]:
    for k in out:
        if cid.split("-")[1] in k:
            print(" ", k, out[k]); break
