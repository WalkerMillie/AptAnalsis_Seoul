"""[GENERATED] analysis 도메인 예외."""


class AnalysisError(Exception):
    pass


class NoMatchingRow(AnalysisError):
    """결정표에서 입력에 맞는 행 없음 (완전성 위반의 런타임 증상)."""


class IncompleteDecisionTable(AnalysisError):
    """결정표 완전성 위반 — 구간 공백/겹침/빈칸. (§9-④)"""

    def __init__(self, problems):
        self.problems = problems
        super().__init__("결정표 완전성 위반:\n" + "\n".join(problems))
