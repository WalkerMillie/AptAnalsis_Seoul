"""[HAND-WRITTEN] 수집한 실거래에서 동·단지 파생 조회 (드릴다운 2·3단계).

planning §3.3: 단지 목록은 '거래 빈도순' 정렬. 수집된 Trade에서 그대로 파생한다.
조율/집계만 — 판단 규칙 없음. store는 JobStore 포트(수집과 같은 인스턴스 주입).
"""

from __future__ import annotations

import datetime as dt
from collections import Counter
from statistics import median

from contexts.market_data.domain.price_trend import (
    confidence_score, period_change,
)

# 표본 게이트(실측 교훈): 소표본·단기·외딴끝점은 노이즈가 커서 미달은 None.
_MIN_MONTHS = 3      # 서로 다른 거래월 최소 개수
_MIN_TRADES = 5      # 윈도우 내 거래 최소 건수
_MIN_SEG = 3         # 첫 구간·끝 구간 각각 최소 거래수(외딴 1건 끝점 차단=끝점 견고화)
_MIN_BAND_SEG = 2    # 대표 평형의 첫·끝 구간 각 최소 거래수(평형 정규화 endpoint)
_MIN_RATIO_SEG = 3   # 전세가율: 같은 평형의 매매·전세 각 최소 표본(median 비율 안정화)
_INSUFFICIENT = (f"표본 부족(거래월 {_MIN_MONTHS}개·거래 {_MIN_TRADES}건·양끝 각 {_MIN_SEG}건·"
                 f"같은 평형 양끝 각 {_MIN_BAND_SEG}건 비교 가능해야 함)")

# 전국 집계 스냅샷 캐시의 '로직 버전'. _growth_from_points/게이트/대표평형 산정 등
# 결과 수치에 영향 주는 계산 로직을 바꾸면 반드시 +1 → 기존 스냅샷 전부 자동 무효(재계산).
# (데이터 변경은 data_version이 잡고, 로직 변경은 이 상수가 잡는다 — 2축 무효화.)
AGG_LOGIC_VERSION = 1


def _tier(score: float) -> str:
    return "높음" if score >= 0.7 else "보통" if score >= 0.4 else "낮음"


def _band(area: float) -> int:
    """전용면적 → 평형 밴드(반올림 ㎡). 같은 평형끼리만 비교해 믹스 왜곡 제거."""
    return round(area)


def _month_idx(d) -> int:
    """date → 연속 월 인덱스(year*12+month-1). 윈도우 필터/간격 계산용."""
    return d.year * 12 + (d.month - 1)


def _ym_label(idx: int) -> str:
    return f"{idx // 12}-{idx % 12 + 1:02d}"


def _window_start_date(anchor: dt.date, months: int) -> dt.date:
    """anchor(최신 계약일)에서 months개월 윈도우의 시작 달 1일.

    DB 푸시다운 필터(contract_date >= 이 날짜)용. 월 인덱스 윈도우
    (start_idx <= idx <= anchor_idx)와 동치 — anchor가 최댓값이라 상한은 자동 충족.
    """
    aidx = anchor.year * 12 + (anchor.month - 1)
    sidx = aidx - (months - 1)
    return dt.date(sidx // 12, sidx % 12 + 1, 1)


def _growth_from_points(points: list) -> dict | None:
    """(월idx, 전용면적, ㎡당가) 점들에서 평형 정규화 '기간 상승률' + 신뢰도 + 근거.

    왜곡 제거 3중:
      ① 끝점 견고화 — 윈도우를 첫 1/3·끝 1/3 '구간'으로 나눠 각 구간을 모아 비교(외딴 1건 X).
      ② 평형 정규화 — 같은 전용(밴드)끼리만 비교(평형 믹스로 ㎡당가 출렁이는 것 차단).
         대표 평형 = 양끝 구간 모두 _MIN_BAND_SEG건 이상인 밴드 중 거래 최다.
      ③ 신뢰도 — 총거래·커버개월·대표평형 약한끝 거래수 결합(0~1). 절대값과 함께 본다.
    게이트 미달이면 None.
    """
    n_trades = len(points)
    idxs_all = {i for i, _, _ in points}
    months_covered = len(idxs_all)
    if months_covered < _MIN_MONTHS or n_trades < _MIN_TRADES:
        return None
    lo, hi = min(idxs_all), max(idxs_all)
    span = hi - lo
    if span < 1:
        return None
    e_cut, l_cut = lo + span / 3.0, hi - span / 3.0
    early = [(i, a, p) for i, a, p in points if i <= e_cut]
    late = [(i, a, p) for i, a, p in points if i >= l_cut]
    if len(early) < _MIN_SEG or len(late) < _MIN_SEG:
        return None                                  # 외딴 끝점 차단
    # 평형(밴드)별 양끝 구간 거래 모음
    eb: dict = {}
    lb: dict = {}
    for i, a, p in early:
        eb.setdefault(_band(a), []).append((i, p))
    for i, a, p in late:
        lb.setdefault(_band(a), []).append((i, p))
    # 대표 평형: 양끝 각 _MIN_BAND_SEG건 이상 있는 밴드 중 (early+late) 거래 최다
    candidates = [b for b in eb if b in lb
                  and len(eb[b]) >= _MIN_BAND_SEG and len(lb[b]) >= _MIN_BAND_SEG]
    if not candidates:
        return None                                  # 같은 평형 비교 불가 → 보류
    band = max(candidates, key=lambda b: len(eb[b]) + len(lb[b]))
    e_pts, l_pts = eb[band], lb[band]
    e_ppm2 = median(p for _, p in e_pts)
    l_ppm2 = median(p for _, p in l_pts)
    e_cent = sum(i for i, _ in e_pts) / len(e_pts)   # 대표평형 거래 무게중심(월)
    l_cent = sum(i for i, _ in l_pts) / len(l_pts)
    if l_cent - e_cent <= 0:
        return None
    min_endpoint = min(len(e_pts), len(l_pts))
    score = confidence_score(n_trades, months_covered, min_endpoint)
    return {
        "growth": period_change(e_ppm2, l_ppm2),     # 기간(윈도우) 상승률 — 연환산 안 함
        "span_months": span,
        "band_m2": band,                             # 비교 기준 평형
        "confidence": round(score, 3),
        "confidence_tier": _tier(score),
        "first": {"ym": _ym_label(min(i for i, _ in e_pts)),
                  "ppm2": round(e_ppm2), "n": len(e_pts)},
        "last": {"ym": _ym_label(max(i for i, _ in l_pts)),
                 "ppm2": round(l_ppm2), "n": len(l_pts)},
    }


class TradeQueryService:
    def __init__(self, store):
        self._store = store

    def dongs(self, region_code: str) -> list[str]:
        """구(region_code)에서 거래가 있는 법정동 목록(DB distinct)."""
        return self._store.dongs_by_region(region_code)

    def complexes(self, region_code: str, dong: str) -> list[dict]:
        """구+동의 단지 목록 — 거래빈도 내림차순(DB 집계)."""
        return [{"complex_id": cid, "apt_name": name, "trade_count": n}
                for cid, name, n in self._store.complex_counts(region_code, dong)]

    def search_dongs(self, q: str, limit: int = 50) -> list[dict]:
        """동 이름 부분일치 검색(전체 구 횡단). 거래빈도 내림차순.

        결과의 region_code는 UI가 구 목록(code→name)으로 매핑한다. 동 클릭→바로 이동용.
        """
        q = q.strip()
        if not q:
            return []
        return [{"region_code": code, "dong": dong, "trade_count": n}
                for (code, dong), n in self._store.search_dongs_counts(q, limit)]

    def trades(self, complex_id: str, limit: int = 30) -> list[dict]:
        """단지(complex_id)의 최근 실거래 — 계약일 내림차순. UI 가격표시·분석 프리필용."""
        rows = self._store.trades_by_complex(complex_id)
        rows.sort(key=lambda t: t.contract_date, reverse=True)
        return [{"contract_date": t.contract_date.isoformat(),
                 "price": t.price, "area_m2": t.area_m2, "floor": t.floor,
                 "apt_name": t.apt_name, "legal_dong": t.legal_dong,
                 "build_year": t.build_year}
                for t in rows[:limit]]

    def _anchor_idx(self) -> int | None:
        """비교 기준이 되는 최신 거래월(전체 데이터 공통). 단지마다 같은 달력 윈도우로 측정.

        DB에서 max(contract_date) 1건만 받아 월 인덱스로 변환(전 행 로드 안 함)."""
        anchor = self._store.anchor_month()
        return _month_idx(anchor) if anchor is not None else None

    def price_series(self, complex_id: str, months: int = 12) -> dict:
        """단지의 월별 중앙 ㎡당가 시계열(대표 평형 기준) — 추세 차트용.

        대표 평형 = 윈도우 내 거래 최다 전용(밴드). 그 평형의 월별 median ㎡당가만 반환해
        평형 믹스로 출렁이지 않는 깨끗한 추세를 그린다.
        """
        anchor = self._anchor_idx()
        rows = [t for t in self._store.trades_by_complex(complex_id) if t.area_m2 > 0]
        if anchor is None or not rows:
            return {"complex_id": complex_id, "months": months, "band_m2": None, "series": []}
        start = anchor - (months - 1)
        win = [t for t in rows if start <= _month_idx(t.contract_date) <= anchor]
        if not win:
            return {"complex_id": complex_id, "months": months, "band_m2": None, "series": []}
        band_counts = Counter(_band(t.area_m2) for t in win)
        band = band_counts.most_common(1)[0][0]            # 대표 평형
        by_month: dict = {}
        for t in win:
            if _band(t.area_m2) == band:
                by_month.setdefault(_month_idx(t.contract_date), []).append(t.price / t.area_m2)
        series = [{"ym": _ym_label(i), "ppm2": round(median(v)), "n": len(v)}
                  for i, v in sorted(by_month.items())]
        return {"complex_id": complex_id, "months": months, "band_m2": band, "series": series}

    def price_growth(self, complex_id: str, months: int = 3) -> dict:
        """단지의 실제 기간 상승률(㎡당가, 평형 정규화) — 최근 `months`개월 윈도우. 자동입력용.

        growth=None 이면 reason에 사유(표본 부족 등). 근거(first/last 월·㎡당가) 동봉.
        """
        anchor = self._anchor_idx()
        rows = [t for t in self._store.trades_by_complex(complex_id) if t.area_m2 > 0]
        if anchor is None or not rows:
            return {"complex_id": complex_id, "months": months,
                    "growth": None, "reason": "수집된 거래 없음", "n_trades": 0}
        start = anchor - (months - 1)
        points = [(_month_idx(t.contract_date), t.area_m2, t.price / t.area_m2)
                  for t in rows if start <= _month_idx(t.contract_date) <= anchor]
        n = len(points)
        mc = len({i for i, _, _ in points})
        g = _growth_from_points(points)
        if g is None:
            return {"complex_id": complex_id, "months": months, "growth": None,
                    "reason": _INSUFFICIENT, "n_trades": n, "months_covered": mc}
        return {"complex_id": complex_id, "months": months, "n_trades": n,
                "months_covered": mc, **g}

    def complex_growth_scores(self, region_code: str, dong: str, months: int = 3) -> list[dict]:
        """구+동 단지별 연환산 상승률 — 비교/정렬용. 같은 윈도우(공통 anchor)로 측정.

        점수(손익분기 초과율)는 표준 대출조건이 필요하므로 UI에서 (상승률 − 표준허들)로 계산.
        여기선 단지별 실제 상승률과 근거만 낸다(판단 없음).
        """
        anchor = self._anchor_idx()
        if anchor is None:
            return []
        start = anchor - (months - 1)
        per: dict = {}          # complex_id → {"name", "count", "points", "recent"}
        for t in self._store.trades_by_region_dong(region_code, dong):
            if t.area_m2 <= 0:
                continue
            e = per.setdefault(t.complex_id,
                               {"name": t.apt_name, "count": 0, "points": [], "recent": None})
            e["count"] += 1
            # 최신 실거래(계약일 max) — trades()/hero가 쓰는 값과 동일 소스로 일관 유지.
            if e["recent"] is None or t.contract_date > e["recent"]["date"]:
                e["recent"] = {"date": t.contract_date, "price": t.price, "area_m2": t.area_m2}
            idx = _month_idx(t.contract_date)
            if start <= idx <= anchor:
                e["points"].append((idx, t.area_m2, t.price / t.area_m2))
        out = []
        for cid, e in per.items():
            g = _growth_from_points(e["points"])
            rc = e["recent"]
            out.append({"complex_id": cid, "apt_name": e["name"], "trade_count": e["count"],
                        "months": months,
                        "growth": (g["growth"] if g else None),
                        "confidence": (g["confidence"] if g else None),
                        "confidence_tier": (g["confidence_tier"] if g else None),
                        "band_m2": (g["band_m2"] if g else None),
                        "recent_price": (rc["price"] if rc else None),
                        "recent_area": (rc["area_m2"] if rc else None),
                        "recent_date": (rc["date"].isoformat() if rc else None),
                        "months_covered": len({i for i, _, _ in e["points"]}),
                        "window_trades": len(e["points"])})
        # 상승률 있는 단지 우선(내림차순), 표본부족(None)은 뒤로.
        out.sort(key=lambda x: (x["growth"] is not None, x["growth"] or 0), reverse=True)
        return out

    def jeonse_ratio(self, complex_id: str, months: int = 12) -> dict:
        """단지의 전세가율(전세 ㎡당 보증금 ÷ 매매 ㎡당가, 평형 정규화) — 최근 months 윈도우.

        매매·전세를 같은 대표 평형(밴드)에서 median끼리 비교(믹스 왜곡 제거). 거주가치
        입력으로 쓰인다(buy-vs-rent). ratio=None이면 reason에 사유. 양쪽 표본이 있어야.
        """
        sales = [t for t in self._store.trades_by_complex(complex_id) if t.area_m2 > 0]
        rents = [r for r in self._store.rents_by_complex(complex_id) if r.area_m2 > 0]
        if not sales:
            return {"complex_id": complex_id, "ratio": None, "reason": "매매 실거래 없음"}
        if not rents:
            return {"complex_id": complex_id, "ratio": None, "reason": "전세 실거래 없음"}
        anchor = max(_month_idx(t.contract_date) for t in sales)
        start = anchor - (months - 1)

        def _by_band(rows, value):
            out: dict = {}
            for x in rows:
                if start <= _month_idx(x.contract_date) <= anchor:
                    out.setdefault(_band(x.area_m2), []).append(value(x) / x.area_m2)
            return out
        sale_b = _by_band(sales, lambda t: t.price)
        rent_b = _by_band(rents, lambda r: r.deposit)
        # 게이트: 같은 평형에서 매매·전세 각 _MIN_RATIO_SEG건 이상이라야 median 비율이 안정.
        # (신축처럼 매매 1건뿐인 밴드를 뽑아 전세가율이 비현실적으로 튀는 것 차단)
        common = [b for b in sale_b if b in rent_b
                  and len(sale_b[b]) >= _MIN_RATIO_SEG and len(rent_b[b]) >= _MIN_RATIO_SEG]
        if not common:
            return {"complex_id": complex_id, "ratio": None, "months": months,
                    "reason": (f"같은 평형의 매매·전세 각 {_MIN_RATIO_SEG}건+ 동시 표본 없음 "
                               "(매매 회전 적은 단지)")}
        # 대표 평형 = 매매+전세 표본 최다 밴드
        band = max(common, key=lambda b: len(sale_b[b]) + len(rent_b[b]))
        sale_ppm2 = median(sale_b[band])
        rent_ppm2 = median(rent_b[band])
        return {
            "complex_id": complex_id, "months": months, "band_m2": band,
            "ratio": round(rent_ppm2 / sale_ppm2, 4),
            "sale_ppm2": round(sale_ppm2), "rent_ppm2": round(rent_ppm2),
            # 대표 평형 기준 절대 금액(원) — 매매 시세·전세 보증금 시세(표시용).
            "sale_price": round(sale_ppm2 * band), "rent_deposit": round(rent_ppm2 * band),
            "sale_n": len(sale_b[band]), "rent_n": len(rent_b[band]),
        }

    def jeonse_series(self, complex_id: str, months: int = 12) -> dict:
        """단지의 월별 중앙 전세 ㎡당 보증금 시계열(대표 평형) — 전세 추세 차트용.

        price_series(매매)의 전세 판. 대표 평형 = 윈도우 내 전세 거래 최다 전용(밴드).
        anchor는 전세 데이터 자체의 최신월(매매와 평형·월이 다를 수 있어 독립 산정).
        """
        rents = [r for r in self._store.rents_by_complex(complex_id) if r.area_m2 > 0]
        if not rents:
            return {"complex_id": complex_id, "months": months, "band_m2": None, "series": []}
        anchor = max(_month_idx(r.contract_date) for r in rents)
        start = anchor - (months - 1)
        win = [r for r in rents if start <= _month_idx(r.contract_date) <= anchor]
        if not win:
            return {"complex_id": complex_id, "months": months, "band_m2": None, "series": []}
        band = Counter(_band(r.area_m2) for r in win).most_common(1)[0][0]
        by_month: dict = {}
        for r in win:
            if _band(r.area_m2) == band:
                by_month.setdefault(_month_idx(r.contract_date), []).append(r.deposit / r.area_m2)
        series = [{"ym": _ym_label(i), "ppm2": round(median(v)), "n": len(v)}
                  for i, v in sorted(by_month.items())]
        return {"complex_id": complex_id, "months": months, "band_m2": band, "series": series}

    def candidate_metrics(self, months: int = 12, min_trades: int = 10,
                          limit: int = 2000) -> dict:
        """서울 전 단지의 다지표(가격·평수·건축년도·상승률·전세가율·신뢰도)를 1회 순회로 집계.

        가중치 랭킹(후보 추천)용 raw 지표 — 정규화·가중합·정렬은 프론트에서(슬라이더 즉시 반영).
        같은 윈도우(공통 anchor·최근 months개월) + 표본 게이트(min_trades·_growth_from_points) 통과만.
        매매·전세 각각 한 번씩만 순회(O(N)) — 단지별로 모아 처리.
        """
        anchor_d = self._store.anchor_month()
        if anchor_d is None:
            return {"months": months, "min_trades": min_trades, "candidates": []}
        start_date = _window_start_date(anchor_d, months)
        # 매매: 단지별 윈도우 거래점 + 건축년도 (DB가 윈도우·area>0 필터, 경량 튜플)
        S: dict = {}
        for cid, rc, dong, name, byear, area, price, cd in \
                self._store.trades_window(start_date):
            e = S.setdefault(cid, {
                "name": name, "region": rc, "dong": dong,
                "points": [], "byears": []})
            e["points"].append((_month_idx(cd), area, price / area))
            if byear:
                e["byears"].append(byear)
        # 전세: 단지별 평형밴드 → ㎡당 보증금
        R: dict = {}
        for cid, area, deposit in self._store.rents_window(start_date):
            R.setdefault(cid, {}).setdefault(_band(area), []).append(deposit / area)
        out = []
        for cid, e in S.items():
            pts = e["points"]
            if len(pts) < min_trades:
                continue
            g = _growth_from_points(pts)
            if g is None:
                continue
            # 대표 평형 = 성장 계산과 같은 밴드(양끝 표본 검증된 밴드)로 가격도 통일.
            band = g["band_m2"]
            # 가격은 '현재 시세' = 최근 구간(끝 1/3) median ㎡당가. 12개월 전체 median은
            # 급등 단지를 옛 싼 거래로 끌어내려 실제 매수가와 괴리(상세=최근 실거래와 어긋남).
            recent_ppm2 = g["last"]["ppm2"]
            # 전세가율은 매매·전세를 같은 방식(12개월 median)으로 재야 왜곡이 없다(현재가 아님).
            jr = None
            rb = R.get(cid, {}).get(band)
            sale_seg = [p for _, a, p in pts if _band(a) == band]
            if rb and len(rb) >= _MIN_RATIO_SEG and len(sale_seg) >= _MIN_RATIO_SEG:
                jr = round(median(rb) / median(sale_seg), 4)
            build_year = Counter(e["byears"]).most_common(1)[0][0] if e["byears"] else 0
            out.append({
                "complex_id": cid, "apt_name": e["name"],
                "region_code": e["region"], "dong": e["dong"],
                "price_ppm2": recent_ppm2,
                "total_price": round(recent_ppm2 * band),
                "area_m2": band, "build_year": build_year,
                "growth": g["growth"], "jeonse_ratio": jr,
                "confidence": g["confidence"], "window_trades": len(pts),
            })
        return {"months": months, "min_trades": min_trades,
                "total": len(out), "candidates": out[:limit]}

    # ── 전국 집계 스냅샷 캐시 ──────────────────────────────────────────
    # 무거운 전국 집계 3종(+티커)의 결과를 (data_version, logic_version) 키로 얼린다.
    # 둘 다 일치하면 즉답, 아니면 라이브 함수를 '그대로' 1회 호출해 저장(재구현 없음 →
    # 캐시값 = 라이브값 보장). 파라미터 공간이 작고(기간 5종 등) backfill 사이 불변이라
    # 결과 스냅샷이 가장 효율적. store가 스냅샷 포트 없으면(인메모리) 라이브 폴백.
    _TICKER_MONTHS = 24
    _TICKER_TOP = 30

    def _cached(self, cache_key: str, compute):
        store = self._store
        if not (hasattr(store, "data_version") and hasattr(store, "agg_snapshot")):
            return compute()                       # 폴백: 버전/스냅샷 포트 없는 스토어
        dv = store.data_version()
        snap = store.agg_snapshot(cache_key)
        if (snap is not None and snap["data_version"] == dv
                and snap["logic_version"] == AGG_LOGIC_VERSION):
            return snap["payload"]                 # 데이터·로직 둘 다 그대로 → 얼린 값
        payload = compute()                        # 라이브 함수 그대로(재구현 X)
        if hasattr(store, "save_agg_snapshot"):
            store.save_agg_snapshot(cache_key, dv, AGG_LOGIC_VERSION, payload)
        return payload

    def rankings_cached(self, months: int = 12, min_trades: int = 10, limit: int = 100) -> dict:
        return self._cached(f"rankings|m={months}|mt={min_trades}|lim={limit}",
                            lambda: self.rank_complexes(months, min_trades, limit))

    def region_summary_cached(self, months: int = 12, min_trades: int = 10) -> dict:
        return self._cached(f"region_summary|m={months}|mt={min_trades}",
                            lambda: self.region_summary(months, min_trades))

    def candidates_cached(self, months: int = 12, min_trades: int = 10, limit: int = 2000) -> dict:
        return self._cached(f"candidates|m={months}|mt={min_trades}|lim={limit}",
                            lambda: self.candidate_metrics(months, min_trades, limit))

    def _ticker_payload(self) -> dict:
        """티커 원본 계산(급등 상위 30 + 구별 중앙값). 캐시·shadow검증 공용."""
        rk = self.rank_complexes(months=self._TICKER_MONTHS, min_trades=10,
                                 limit=self._TICKER_TOP)
        rs = self.region_summary(months=self._TICKER_MONTHS, min_trades=10)
        return {"movers": [{"apt_name": c["apt_name"], "growth": c["growth"]}
                           for c in rk.get("ranked", [])],
                "regions": rs.get("regions", {})}

    def ticker(self) -> dict:
        """상단 티커 payload — data_version 키 캐시. 갱신 시 자동 무효(즉시 최신 반영)."""
        return self._cached("ticker", self._ticker_payload)

    def region_summary(self, months: int = 12, min_trades: int = 10) -> dict:
        """구(region_code)별 단지 상승률 중앙값 — 지도 색칠(choropleth)용.

        각 구의 표본 통과 단지들의 기간 상승률을 모아 median. 단지 수도 함께.
        """
        anchor_d = self._store.anchor_month()
        if anchor_d is None:
            return {"months": months, "min_trades": min_trades, "regions": {}}
        start_date = _window_start_date(anchor_d, months)
        per: dict = {}      # complex_id → points
        region_of: dict = {}
        for cid, rc, dong, name, byear, area, price, cd in \
                self._store.trades_window(start_date):
            per.setdefault(cid, []).append((_month_idx(cd), area, price / area))
            region_of[cid] = rc
        growths: dict = {}   # region_code → [growth, ...]
        for cid, points in per.items():
            if len(points) < min_trades:
                continue
            g = _growth_from_points(points)
            if g is None:
                continue
            growths.setdefault(region_of[cid], []).append(g["growth"])
        regions = {code: {"median_growth": median(v), "complexes": len(v)}
                   for code, v in growths.items() if v}
        return {"months": months, "min_trades": min_trades, "regions": regions}

    def rank_complexes(self, months: int = 12, min_trades: int = 10,
                       limit: int = 100) -> dict:
        """서울 전체 단지를 기간 상승률(평형 정규화) 내림차순으로 줄세운다(리더보드).

        같은 윈도우(공통 anchor·최근 months개월)로 전 단지 측정 → 표본 게이트 통과 +
        윈도우 내 거래 min_trades건 이상만 랭킹에 올린다(소표본 노이즈 상위 점령 방지).
        한 번에 전 거래(rows)를 순회하므로 시간이 걸릴 수 있다(시간 허용 전제).
        """
        anchor_d = self._store.anchor_month()
        if anchor_d is None:
            return {"months": months, "min_trades": min_trades,
                    "ranked": [], "skipped_low_sample": 0}
        start_date = _window_start_date(anchor_d, months)
        per: dict = {}      # complex_id → {name, region, dong, points}
        for cid, rc, dong, name, byear, area, price, cd in \
                self._store.trades_window(start_date):
            e = per.setdefault(cid, {
                "name": name, "region": rc,
                "dong": dong, "points": []})
            e["points"].append((_month_idx(cd), area, price / area))
        ranked, skipped = [], 0
        for cid, e in per.items():
            window_trades = len(e["points"])
            g = _growth_from_points(e["points"])
            if g is None or window_trades < min_trades:
                skipped += 1
                continue
            ranked.append({
                "complex_id": cid, "apt_name": e["name"],
                "region_code": e["region"], "dong": e["dong"],
                "growth": g["growth"], "window_trades": window_trades,
                "months_covered": len({i for i, _, _ in e["points"]}),
                "band_m2": g["band_m2"],
                "confidence": g["confidence"], "confidence_tier": g["confidence_tier"],
                "first": g["first"], "last": g["last"]})
        ranked.sort(key=lambda x: x["growth"], reverse=True)
        return {"months": months, "min_trades": min_trades,
                "ranked": ranked[:limit], "total_qualified": len(ranked),
                "skipped_low_sample": skipped}
