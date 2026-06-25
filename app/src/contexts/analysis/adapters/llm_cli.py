"""[HAND-WRITTEN] LLM 어댑터 — provider 2종을 한 포트(generate)로 추상화.

지금은 API 키 발급이 막혀 'cli' provider(로컬 Claude Code 구독 세션, 키 불필요)로 검증한다.
키가 풀리면 AI_PROVIDER=anthropic 으로 스위치 — 본체(application)는 안 건드린다.

포트: generate(system, user) -> str  (모델 원문 텍스트. 실패 시 LLMError).
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request


class LLMError(RuntimeError):
    """LLM 호출 실패(타임아웃·비정상 종료·빈 응답 등). 서비스가 친절 메시지로 변환."""


class ClaudeCLIClient:
    """로컬 `claude -p` 헤드리스 호출. API 키 없이 구독 세션 사용(검증용).

    --system-prompt 로 기본 CC 시스템프롬프트를 대체(불필요한 도구 지침·캐시 제거),
    --disallowedTools '*' 로 도구 사용 차단(순수 텍스트 생성).
    """

    def __init__(self, model: str = "sonnet", timeout: float = 75.0):
        self.model = model
        self.timeout = timeout

    def generate(self, system: str, user: str) -> str:
        cmd = [
            "claude", "-p",
            "--output-format", "json",
            "--model", self.model,
            "--system-prompt", system,
            "--disallowedTools", "*",
            # MCP 서버 로딩이 startup의 대부분(25s→5s) — 코멘트엔 도구 불필요하므로 전부 차단.
            "--strict-mcp-config",
        ]
        try:
            proc = subprocess.run(
                cmd, input=user, capture_output=True, text=True,
                timeout=self.timeout,
            )
        except FileNotFoundError as e:
            raise LLMError("claude CLI 미설치") from e
        except subprocess.TimeoutExpired as e:
            raise LLMError("LLM 응답 시간 초과") from e
        if proc.returncode != 0:
            raise LLMError(f"claude 비정상 종료(rc={proc.returncode}): {proc.stderr[:200]}")
        try:
            wrap = json.loads(proc.stdout)
        except (json.JSONDecodeError, ValueError) as e:
            raise LLMError("CLI 출력 파싱 실패") from e
        if wrap.get("is_error") or wrap.get("subtype") != "success":
            raise LLMError(f"LLM 오류 응답: {wrap.get('subtype')}")
        text = wrap.get("result")
        if not text:
            raise LLMError("빈 result")
        return text


class HTTPShimClient:
    """호스트에서 도는 claude shim(docker/ai_shim.py)에 HTTP 위임.

    컨테이너엔 node/claude가 없어 CLI를 직접 못 돌리므로(개발용 브리지), 호스트 shim이
    대신 `claude -p`를 실행하고 result 텍스트를 돌려준다. 키 풀리면 anthropic provider로 교체.
    """

    def __init__(self, url: str, timeout: float = 75.0):
        self.url = url
        self.timeout = timeout

    def generate(self, system: str, user: str) -> str:
        body = json.dumps({"system": system, "user": user}).encode("utf-8")
        req = urllib.request.Request(
            self.url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as e:
            raise LLMError(f"shim 연결 실패: {e}") from e
        except (json.JSONDecodeError, ValueError) as e:
            raise LLMError("shim 응답 파싱 실패") from e
        if data.get("error"):
            raise LLMError(f"shim 오류: {data['error']}")
        text = data.get("result")
        if not text:
            raise LLMError("shim 빈 result")
        return text


class AnthropicClient:
    """[미구현] API 키 발급 후 작성 — anthropic SDK 직접 호출.

    키가 풀리면 여기에 messages.create(model, system, messages=[{user}]) 구현하고
    AI_PROVIDER=anthropic 로 스위치. 시그니처(generate)는 동일 유지.
    """

    def __init__(self, model: str = "claude-sonnet-4-6", timeout: float = 45.0):
        self.model = model
        self.timeout = timeout

    def generate(self, system: str, user: str) -> str:  # noqa: ARG002
        raise LLMError("anthropic provider 미구현(API 키 발급 대기)")


def make_llm_client():
    """합성 루트용 팩토리 — AI_PROVIDER 환경변수로 provider 선택(기본 cli)."""
    provider = os.environ.get("AI_PROVIDER", "cli").lower()
    model = os.environ.get("AI_MODEL", "sonnet" if provider != "anthropic" else "claude-sonnet-4-6")
    timeout = float(os.environ.get("AI_TIMEOUT", "75"))
    if provider == "anthropic":
        return AnthropicClient(model=model, timeout=timeout)
    if provider == "http":
        url = os.environ.get("AI_SHIM_URL", "http://host.docker.internal:8765/gen")
        return HTTPShimClient(url=url, timeout=timeout)
    return ClaudeCLIClient(model=model, timeout=timeout)
