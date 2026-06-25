"""[어댑터] ODsay 대중교통 경로 + Kakao 지오코딩 HTTP 클라이언트.

ODsay 웹키는 LAB 등록 Service URI와 Referer 정확 일치를 요구한다(서버호출도).
→ ODSAY_REFERER(기본 http://localhost) 헤더를 항상 박는다.
키는 env에서만 읽고 FE엔 절대 노출하지 않는다(백엔드 프록시).
"""
from __future__ import annotations

import json
import logging
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request

log = logging.getLogger(__name__)

# 인증서 검증을 끈 컨텍스트(fallback 전용). 사내망 SSL 검사 장비(ePrism 등)가 중간에서
# 재서명하면 컨테이너 트러스트스토어엔 그 루트가 없어 CERTIFICATE_VERIFY_FAILED 발생.
# → 평소엔 정상 검증, 검증 실패가 확인된 프로세스에서만 이 컨텍스트로 폴백(배포서버=정상검증 유지).
_INSECURE_SSL = ssl.create_default_context()
_INSECURE_SSL.check_hostname = False
_INSECURE_SSL.verify_mode = ssl.CERT_NONE

# 한 번 검증 실패를 보면 이후 호출은 곧장 폴백(매 호출 2회 시도 방지). 프로세스 수명 동안만.
_cert_fallback = False


class TransitError(Exception):
    """경로 조회 실패 — 서비스가 흡수해 FE엔 부드러운 메시지로."""


class ODsayClient:
    def __init__(self, api_key: str, referer: str = "http://localhost", timeout: float = 8.0):
        self.api_key = api_key
        self.referer = referer
        self.timeout = timeout

    def search(self, sx: float, sy: float, ex: float, ey: float) -> dict:
        qs = urllib.parse.urlencode({
            "apiKey": self.api_key, "SX": sx, "SY": sy, "EX": ex, "EY": ey,
            "OPT": 0, "SearchPathType": 0,
        })
        url = f"https://api.odsay.com/v1/api/searchPubTransPathT?{qs}"
        try:
            data = self._fetch(url)
        except urllib.error.URLError as e:
            raise TransitError(f"ODsay 연결 실패: {e}") from e
        except (json.JSONDecodeError, ValueError) as e:
            raise TransitError("ODsay 응답 파싱 실패") from e
        if data.get("error"):
            err = data["error"]
            msg = err[0].get("message") if isinstance(err, list) and err else err
            raise TransitError(f"ODsay 오류: {msg}")
        return data

    def _fetch(self, url: str) -> dict:
        """정상 검증으로 시도 → 인증서 검증 실패 시에만 검증 미적용으로 폴백(이후 호출은 폴백 고정)."""
        global _cert_fallback
        req = urllib.request.Request(url, headers={"Referer": self.referer})
        ctx = _INSECURE_SSL if _cert_fallback else None
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=ctx) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as e:
            if not _cert_fallback and isinstance(getattr(e, "reason", None), ssl.SSLCertVerificationError):
                log.warning("ODsay 인증서 검증 실패 — 검증 미적용으로 폴백(사내망 SSL검사 추정). %s", e.reason)
                _cert_fallback = True
                with urllib.request.urlopen(req, timeout=self.timeout, context=_INSECURE_SSL) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            raise


class KakaoGeocodeClient:
    """자유입력 목적지 → 좌표(키워드 검색 1건). 프리셋은 좌표 직접이라 불필요."""

    def __init__(self, rest_key: str, timeout: float = 6.0):
        self.rest_key = rest_key
        self.timeout = timeout

    def geocode(self, query: str):
        qs = urllib.parse.urlencode({"query": query, "size": 1})
        req = urllib.request.Request(
            f"https://dapi.kakao.com/v2/local/search/keyword.json?{qs}",
            headers={"Authorization": f"KakaoAK {self.rest_key}"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, json.JSONDecodeError, ValueError) as e:
            raise TransitError(f"목적지 검색 실패: {e}") from e
        docs = data.get("documents") or []
        if not docs:
            raise TransitError("목적지를 찾지 못했어요")
        d = docs[0]
        return float(d["x"]), float(d["y"]), d.get("place_name", query)


def make_odsay_client():
    key = os.environ.get("ODSAY_KEY", "")
    if not key:
        return None
    referer = os.environ.get("ODSAY_REFERER", "http://localhost")
    return ODsayClient(api_key=key, referer=referer)


def make_kakao_client():
    key = os.environ.get("KAKAO_REST_KEY", "")
    return KakaoGeocodeClient(rest_key=key) if key else None
