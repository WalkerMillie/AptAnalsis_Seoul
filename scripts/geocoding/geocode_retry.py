"""2차 패스: 1차 실패 단지를 이름 정제 후 재시도."""
import json, os, re, time, urllib.parse, urllib.request, urllib.error, threading
from concurrent.futures import ThreadPoolExecutor

KEY = os.environ["KAKAO_REST_KEY"]
SCRATCH = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(SCRATCH, "complex_geo.json")

districts = {d["code"]: d["name"] for d in json.load(open(os.path.join(SCRATCH, "districts.json")))["districts"]}
complexes = json.load(open(os.path.join(SCRATCH, "complexes.json")))
out = json.load(open(OUT))
miss = [c for c in complexes if c["cid"] not in out]
print("재시도 대상:", len(miss))

lock = threading.Lock()
SEOUL = lambda la, ln: 37.3 < la < 37.8 and 126.6 < ln < 127.3


def kakao(path, params):
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"https://dapi.kakao.com/v2/local/{path}?{qs}",
                                 headers={"Authorization": f"KakaoAK {KEY}"})
    for a in range(5):
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(0.5 * (a + 1)); continue
            raise
        except Exception:
            time.sleep(0.3 * (a + 1))
    return None


def clean_variants(name):
    """이름 정제 변형들(괄호/로마숫자/차수/영문병기 제거)."""
    v = []
    base = re.sub(r"[（(].*?[)）]", "", name)            # 괄호 제거
    base = re.sub(r"[ⅠⅡⅢⅣⅤ]", "", base)
    base = re.sub(r"\d+차", "", base)
    base = base.replace("/", " ").strip()
    if base and base != name:
        v.append(base)
    # 첫 토큰(영문병기 앞)
    first = re.split(r"[/(]", name)[0].strip()
    if first and first not in v and first != name:
        v.append(first)
    return v


def nearest_station(x, y):
    s = kakao("search/category.json", {"category_group_code": "SW8", "x": x, "y": y,
                                       "radius": 2000, "sort": "distance", "size": 15})
    sdocs = (s or {}).get("documents", [])
    if not sdocs:
        return {}
    first = sdocs[0]
    base = first["place_name"].rsplit(" ", 1)[0]
    lines = []
    for sd in sdocs:
        stn = sd["place_name"].rsplit(" ", 1)
        if stn[0] == base and len(stn) == 2 and stn[1] not in lines:
            lines.append(stn[1])
    return {"station": base, "line": "·".join(lines), "dist_m": int(first["distance"]),
            "slat": round(float(first["y"]), 6), "slng": round(float(first["x"]), 6)}


def work(c):
    gu = districts.get(c["rc"], "")
    for nm in clean_variants(c["name"]) + [""]:
        q = f"서울 {gu} {c['dong']} {nm}".strip()
        d = kakao("search/keyword.json", {"query": q, "size": 15})
        docs = (d or {}).get("documents", [])
        for x in docs:
            addr = x.get("address_name", "") or x.get("road_address_name", "")
            if gu and gu not in addr:
                continue
            la, ln = float(x["y"]), float(x["x"])
            if not SEOUL(la, ln):
                continue
            rec = {"lat": round(la, 6), "lng": round(ln, 6),
                   "road": x.get("road_address_name") or x.get("address_name", ""),
                   "approx": bool(nm == "")}  # 동까지만 근사면 표시
            rec.update(nearest_station(x["x"], x["y"]))
            with lock:
                out[c["cid"]] = rec
            return


with ThreadPoolExecutor(max_workers=8) as ex:
    list(ex.map(work, miss))

json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
still = [c for c in complexes if c["cid"] not in out]
print(f"2차 후: 좌표 {len(out)}/{len(complexes)} (잔여 미스 {len(still)})")
