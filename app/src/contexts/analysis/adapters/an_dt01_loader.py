"""[GENERATED] an_dt01 로더 — CSV(데이터) → AnDt01Table. 어댑터(I/O는 여기서만)."""

from __future__ import annotations

import csv
from pathlib import Path
from datetime import date
from contexts.analysis.domain.an_dt01_table import AnDt01Rule, AnDt01Table

_CSV = Path(__file__).resolve().parent.parent / "domain" / "decision_tables" / "an_dt01.csv"


def _num(s: str):
    s = s.strip()
    return None if s == "" else float(s)


def load_an_dt01_table(path: Path = _CSV) -> AnDt01Table:
    rules: list[AnDt01Rule] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(line for line in f if not line.lstrip().startswith("#"))
        for row in reader:
            rules.append(AnDt01Rule(
                version=row["version"].strip(),
                effective_date=date.fromisoformat(row["effective_date"].strip()),
                purchase_price_min=_num(row["purchase_price_min"]),
                purchase_price_max=_num(row["purchase_price_max"]),
                max_loan_amount=row["max_loan_amount"].strip(),
            ))
    return AnDt01Table(rules)
