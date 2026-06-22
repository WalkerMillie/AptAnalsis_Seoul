"""[GENERATED] an_dt02 로더 — CSV(데이터) → AnDt02Table. 어댑터."""

from __future__ import annotations

import csv
from pathlib import Path
from datetime import date
from contexts.analysis.domain.an_dt02_table import AnDt02Rule, AnDt02Table

_CSV = Path(__file__).resolve().parent.parent / "domain" / "decision_tables" / "an_dt02.csv"


def load_an_dt02_table(path: Path = _CSV) -> AnDt02Table:
    rules: list[AnDt02Rule] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(line for line in f if not line.lstrip().startswith("#"))
        for row in reader:
            rules.append(AnDt02Rule(
                version=row["version"].strip(),
                effective_date=date.fromisoformat(row["effective_date"].strip()),
                complex_id=row["complex_id"].strip(),
                ltz_applies=row["ltz_applies"].strip(),
            ))
    return AnDt02Table(rules)
