"""[HAND-WRITTEN] 국토부 아파트 전월세 실거래가 소스 어댑터 (전세만).

공공데이터포털 RTMSDataSvcAptRent 응답(XML)을 JeonseTrade로 정규화한다.
월세(monthlyRent!=0)는 제외 — 이 프로젝트는 매매 vs 전세 비교만 본다.
molit_source(매매)와 동일 패턴: parse()는 네트워크 없는 순수 함수, __call__만 HTTP.
"""

from __future__ import annotations

import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date

from contexts.market_data.domain.jeonse_trade import JeonseTrade

# 매매와 같은 게이트웨이. 전월세는 별도 활용신청(data.go.kr 15126474) 필요 — 같은 키.
_DEFAULT_BASE = (
    "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"
)
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


class MolitRentsSource:
    def __init__(self, service_key: str, *, base_url: str = _DEFAULT_BASE, timeout: float = 15.0):
        self._key = service_key
        self._base = base_url
        self._timeout = timeout

    def __call__(self, *, region_code: str, deal_ym: str) -> "list[JeonseTrade]":
        """region_code=LAWD 5자리, deal_ym=YYYYMM."""
        qs = urllib.parse.urlencode({
            "serviceKey": self._key, "LAWD_CD": region_code,
            "DEAL_YMD": deal_ym, "numOfRows": 1000, "pageNo": 1,
        })
        req = urllib.request.Request(f"{self._base}?{qs}", headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            return self.parse(resp.read().decode("utf-8"))

    @staticmethod
    def parse(xml_text: str) -> "list[JeonseTrade]":
        """전월세 응답 → JeonseTrade(전세만). resultCode 오류면 예외(→ 수집 FAILED).

        item 필드: aptNm, deposit(만원·콤마), monthlyRent(만원), excluUseAr, floor,
          dealYear/Month/Day, sggCd(LAWD 5자리), umdNm(법정동), buildYear.
        monthlyRent != 0 인 행(월세/반전세)은 제외.
        """
        root = ET.fromstring(xml_text)
        code = root.findtext(".//header/resultCode")
        if code is not None and code not in ("000", "00"):
            msg = (root.findtext(".//header/resultMsg") or "").strip()
            raise ValueError(f"MOLIT 전월세 API 오류 resultCode={code} {msg}")

        out: list[JeonseTrade] = []
        for item in root.iter("item"):
            def f(tag: str) -> str:
                v = item.findtext(tag)
                return v.strip() if v else ""
            monthly = f("monthlyRent").replace(",", "")
            if monthly and monthly != "0":                       # 월세/반전세 제외 — 전세만
                continue
            deposit = f("deposit").replace(",", "").replace(" ", "")
            if not (deposit and f("excluUseAr") and f("dealYear") and f("aptNm")):
                continue
            apt, sgg = f("aptNm"), f("sggCd")
            out.append(JeonseTrade(
                complex_id=f"{sgg}-{apt}",
                apt_name=apt,
                region_code=sgg,
                legal_dong=f("umdNm"),
                area_m2=float(f("excluUseAr")),
                deposit=int(deposit) * 10_000,                   # 만원 → 원
                floor=int(f("floor") or 0),
                contract_date=date(int(f("dealYear")), int(f("dealMonth")), int(f("dealDay"))),
                build_year=int(f("buildYear") or 0),
            ))
        return out
