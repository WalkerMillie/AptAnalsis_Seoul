#!/usr/bin/env python3
"""[HAND-WRITTEN] 로컬 개발용 LLM 브리지 — 호스트에서 실행.

컨테이너엔 node/claude가 없어 CLI를 못 돌린다. 이 shim이 호스트에서 `claude -p`를 실행하고
result 텍스트를 돌려주면, 컨테이너의 HTTPShimClient(AI_PROVIDER=http)가 그걸 받아 쓴다.
키 발급되면 AI_PROVIDER=anthropic 으로 교체하고 이 shim/브리지는 제거한다.

실행:  python docker/ai_shim.py            # 기본 0.0.0.0:8765
의존성 없음(stdlib). claude CLI가 PATH에 있고 인증돼 있어야 함.
"""

import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL = os.environ.get("AI_MODEL", "sonnet")
TIMEOUT = float(os.environ.get("AI_TIMEOUT", "75"))
PORT = int(os.environ.get("AI_SHIM_PORT", "8765"))


def run_claude(system: str, user: str) -> str:
    cmd = [
        "claude", "-p",
        "--output-format", "json",
        "--model", MODEL,
        "--system-prompt", system,
        "--disallowedTools", "*",
        "--strict-mcp-config",   # MCP 로딩 차단(startup 25s→5s)
    ]
    proc = subprocess.run(cmd, input=user, capture_output=True, text=True, timeout=TIMEOUT)
    if proc.returncode != 0:
        raise RuntimeError(f"claude rc={proc.returncode}: {proc.stderr[:200]}")
    wrap = json.loads(proc.stdout)
    if wrap.get("is_error") or wrap.get("subtype") != "success":
        raise RuntimeError(f"claude 오류: {wrap.get('subtype')}")
    text = wrap.get("result")
    if not text:
        raise RuntimeError("빈 result")
    return text


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):   # 조용히
        pass

    def do_POST(self):
        if self.path != "/gen":
            self.send_error(404)
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(n).decode("utf-8"))
            result = run_claude(req.get("system", ""), req.get("user", ""))
            payload = {"result": result}
        except subprocess.TimeoutExpired:
            payload = {"error": "timeout"}
        except Exception as e:  # noqa: BLE001
            payload = {"error": str(e)[:300]}
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print(f"▶ AI shim on 0.0.0.0:{PORT} (model={MODEL}, timeout={TIMEOUT}s) — POST /gen")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
