"""[HAND-WRITTEN] 국토부 실거래가 소스 어댑터 (FetchMolitTrades 구현).

공공데이터포털 RTMSDataSvcAptTradeDev 응답(XML)을 Trade로 정규화한다.
parse()는 네트워크 없는 순수 함수라 단위테스트 가능. __call__만 실제 HTTP(urllib).
실행에는 서비스키(공공데이터포털 발급)가 필요 — 키/엔드포인트는 주입.
"""

from __future__ import annotations

import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date

from contexts.market_data.domain.trade import Trade

# 실측: 이 게이트웨이는 비Dev 오퍼레이션에 키가 승인됨(Dev는 Forbidden).
_DEFAULT_BASE = (
    "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
)
# 실측: WAF가 기본 urllib UA(Python-urllib)를 'Request Blocked'로 막음 → 브라우저 UA 필수.
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


class MolitTradesSource:
    def __init__(self, service_key: str, *, base_url: str = _DEFAULT_BASE, timeout: float = 15.0):
        self._key = service_key
        self._base = base_url
        self._timeout = timeout

    def __call__(self, *, region_code: str, deal_ym: str) -> "list[Trade]":
        """region_code=LAWD 5자리, deal_ym=YYYYMM."""
        qs = urllib.parse.urlencode({
            "serviceKey": self._key, "LAWD_CD": region_code,
            "DEAL_YMD": deal_ym, "numOfRows": 1000, "pageNo": 1,
        })
        req = urllib.request.Request(f"{self._base}?{qs}", headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            return self.parse(resp.read().decode("utf-8"))

    @staticmethod
    def parse(xml_text: str) -> "list[Trade]":
        """현행 Dev API 응답(영문 태그) → Trade. resultCode 오류면 예외(→ 수집 FAILED).

        구조: response/header/{resultCode,resultMsg} + response/body/items/item.
        item 필드(영문): aptNm, dealAmount(만원·콤마), excluUseAr, floor,
          dealYear/dealMonth/dealDay, sggCd(LAWD 5자리), umdNm(법정동), cdealType(해제여부).
        """
        root = ET.fromstring(xml_text)
        code = root.findtext(".//header/resultCode")
        if code is not None and code not in ("000", "00"):       # 정상 외 → 오류
            msg = (root.findtext(".//header/resultMsg") or "").strip()
            raise ValueError(f"MOLIT API 오류 resultCode={code} {msg}")

        out: list[Trade] = []
        for item in root.iter("item"):
            def f(tag: str) -> str:
                v = item.findtext(tag)
                return v.strip() if v else ""
            if f("cdealType"):                                   # 해제(취소)된 거래 제외
                continue
            amount = f("dealAmount").replace(",", "").replace(" ", "")
            if not (amount and f("excluUseAr") and f("dealYear")):
                continue                                         # 필수 필드 누락행 스킵
            apt, sgg = f("aptNm"), f("sggCd")
            out.append(Trade(
                complex_id=f"{sgg}-{apt}",
                apt_name=apt,
                region_code=sgg,
                legal_dong=f("umdNm"),
                area_m2=float(f("excluUseAr")),
                price=int(amount) * 10_000,                      # 만원 → 원
                floor=int(f("floor") or 0),
                contract_date=date(int(f("dealYear")), int(f("dealMonth")), int(f("dealDay"))),
                build_year=int(f("buildYear") or 0),             # 건축년도(연). 용적률·건폐율은 이 API에 없음
            ))
        return out
