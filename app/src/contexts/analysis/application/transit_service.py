"""[HAND-WRITTEN] 대중교통 소요시간 유스케이스 — 온디맨드.

AI 코멘트와 동일 철학: 어떤 실패도 예외로 안 새고 ok=False+message로 흡수(FE 부드럽게).
프리셋은 좌표 직접, 자유입력은 Kakao 지오코딩 후 ODsay 경로.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass

from contexts.analysis.adapters.odsay_client import TransitError
from contexts.analysis.domain.transit import PRESETS, parse_routes

log = logging.getLogger(__name__)

_FRIENDLY = "지금은 교통 경로를 불러오기 어려워요. 잠시 후 다시 시도해 주세요."
_NOKEY = "교통 경로 기능이 아직 설정되지 않았어요."


@dataclass(frozen=True)
class TransitResult:
    ok: bool
    dest_label: str = ""
    routes: tuple = ()      # list[dict] (Route asdict)
    message: str = ""


class TransitService:
    def __init__(self, odsay_client, kakao_client=None):
        self._odsay = odsay_client
        self._kakao = kakao_client

    def presets(self) -> list:
        return PRESETS

    def routes(self, sx: float, sy: float, *, preset: str = "",
               dest_q: str = "", ex: float = None, ey: float = None) -> TransitResult:
        if self._odsay is None:
            return TransitResult(ok=False, message=_NOKEY)
        try:
            label, dx, dy = self._resolve_dest(preset, dest_q, ex, ey)
            raw = self._odsay.search(sx, sy, dx, dy)
            routes = parse_routes(raw, limit=3)
            if not routes:
                return TransitResult(ok=False, dest_label=label,
                                     message="대중교통 경로를 찾지 못했어요(너무 가깝거나 경로 없음).")
            return TransitResult(ok=True, dest_label=label,
                                 routes=tuple(self._serialize(r) for r in routes))
        except TransitError as e:
            log.warning("교통 경로 실패: %s", e)
            return TransitResult(ok=False, message=_FRIENDLY)
        except Exception as e:  # noqa: BLE001
            log.warning("교통 경로 예외: %s", e, exc_info=True)
            return TransitResult(ok=False, message=_FRIENDLY)

    def _resolve_dest(self, preset, dest_q, ex, ey):
        if preset:
            for p in PRESETS:
                if p["key"] == preset:
                    return p["label"], p["x"], p["y"]
            raise TransitError("알 수 없는 목적지")
        if ex is not None and ey is not None:
            return (dest_q or "목적지"), float(ex), float(ey)
        if dest_q:
            if self._kakao is None:
                raise TransitError("목적지 검색이 설정되지 않았어요")
            dx, dy, name = self._kakao.geocode(f"서울 {dest_q}")
            return name, dx, dy
        raise TransitError("목적지가 지정되지 않았어요")

    @staticmethod
    def _serialize(route) -> dict:
        d = asdict(route)
        d["legs"] = [{"type": l["type"], "name": l["name"], "from": l["from_"],
                      "to": l["to"], "minutes": l["minutes"]} for l in d["legs"]]
        return d
