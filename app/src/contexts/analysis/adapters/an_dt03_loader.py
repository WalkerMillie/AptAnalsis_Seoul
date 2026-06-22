"""[GENERATED] an_dt03 로더 — CSV(데이터) → AnDt03Table. 어댑터."""

from __future__ import annotations

import csv
from pathlib import Path
from datetime import date
from contexts.analysis.domain.an_dt03_table import AnDt03Rule, AnDt03Table

_CSV = Path(__file__).resolve().parent.parent / "domain" / "decision_tables" / "an_dt03.csv"


def load_an_dt03_table(path: Path = _CSV) -> AnDt03Table:
    rules: list[AnDt03Rule] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(line for line in f if not line.lstrip().startswith("#"))
        for row in reader:
            rules.append(AnDt03Rule(
                version=row["version"].strip(),
                effective_date=date.fromisoformat(row["effective_date"].strip()),
                holding_years=row["holding_years"].strip(),
                residency_years=row["residency_years"].strip(),
                house_count=row["house_count"].strip(),
                capital_gains_tax_exempt=row["capital_gains_tax_exempt"].strip(),
            ))
    return AnDt03Table(rules)
