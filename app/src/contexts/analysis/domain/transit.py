"""[순수] 대중교통 경로 도메인 — 목적지 프리셋 + ODsay 응답 파싱.

네트워크 없음(어댑터가 호출). 여기선 프리셋 좌표·응답→요약 변환만.
"""
from __future__ import annotations

from dataclasses import dataclass

# 자주 가는 목적지 프리셋 (역 좌표, Kakao SW8 기준). FE는 키 없이 이 목록을 그대로 노출.
PRESETS = [
    {"key": "gangnam", "label": "강남역", "x": 127.028001, "y": 37.498086},
    {"key": "hapjeong", "label": "합정역", "x": 126.914454, "y": 37.549913},
    {"key": "guui", "label": "구의역", "x": 127.086181, "y": 37.537175},
    {"key": "gaebong", "label": "개봉역", "x": 126.858716, "y": 37.494642},
]

_TRAFFIC = {1: "subway", 2: "bus", 3: "walk"}


@dataclass(frozen=True)
class Leg:
    type: str          # subway | bus | walk
    name: str          # 노선명/버스번호 ('' for walk)
    from_: str
    to: str
    minutes: int


@dataclass(frozen=True)
class Route:
    total_min: int
    walk_m: int
    payment: int
    transfers: int
    legs: tuple


def parse_routes(raw: dict, limit: int = 3) -> list:
    """ODsay searchPubTransPathT 응답 → Route 리스트(최대 limit, 빠른 순)."""
    paths = ((raw or {}).get("result") or {}).get("path") or []
    out = []
    for p in paths[:limit]:
        info = p.get("info", {})
        transfers = max(0, info.get("busTransitCount", 0) + info.get("subwayTransitCount", 0) - 1)
        legs = []
        for sp in p.get("subPath", []):
            t = _TRAFFIC.get(sp.get("trafficType"), "walk")
            if t == "walk":
                # 도보 구간은 합산만(개별 노출 생략) — 짧은 도보 누락 방지 위해 0분이면 skip
                continue
            lane = (sp.get("lane") or [{}])[0]
            name = lane.get("name") or (("버스 " + lane.get("busNo", "")) if lane.get("busNo") else "")
            legs.append(Leg(type=t, name=name.strip(), from_=sp.get("startName", ""),
                            to=sp.get("endName", ""), minutes=sp.get("sectionTime", 0)))
        out.append(Route(total_min=info.get("totalTime", 0), walk_m=info.get("totalWalk", 0),
                         payment=info.get("payment", 0), transfers=transfers, legs=tuple(legs)))
    return out
