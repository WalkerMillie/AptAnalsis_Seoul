"""[GENERATED] §9-③ 경계 위반 테스트 (stdlib AST). 도메인은 어댑터/인프라/타컨텍스트 import 금지."""

import ast
import pathlib
import unittest

SRC = pathlib.Path(__file__).resolve().parent.parent / "src"
CONTEXTS = SRC / "contexts"
FORBIDDEN = ('adapters', 'application', '.ports', 'django', 'rest_framework', 'sqlalchemy', 'requests', 'httpx', 'celery', 'redis')
ALL = {p.name for p in CONTEXTS.iterdir() if p.is_dir() and not p.name.startswith("__")}


def _imports(path):
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            for n in node.names:
                yield n.name
        elif isinstance(node, ast.ImportFrom):
            yield node.module or ""


class DomainBoundary(unittest.TestCase):
    def test_all_clean(self):
        bad = []
        for ctx in sorted(ALL):
            d = CONTEXTS / ctx / "domain"
            if not d.exists():
                continue
            for py in d.rglob("*.py"):
                for mod in _imports(py):
                    if any(f in mod for f in FORBIDDEN):
                        bad.append(f"{ctx}/domain/{py.name}: {mod}")
                    for other in ALL - {ctx}:
                        if f"contexts.{other}" in mod:
                            bad.append(f"{ctx}/domain/{py.name}: 타컨텍스트 {mod}")
            # §2 — web 어댑터는 도메인 직접 import 금지 (application 유스케이스 경유).
            web = CONTEXTS / ctx / "adapters" / "web"
            if web.exists():
                for py in web.rglob("*.py"):
                    for mod in _imports(py):
                        if f"contexts.{ctx}.domain" in mod:
                            bad.append(f"{ctx}/adapters/web/{py.name}: 도메인 직접 import {mod} (§2)")
        self.assertEqual(bad, [], "\n".join(bad))


if __name__ == "__main__":
    unittest.main()
