from __future__ import annotations

import csv
from pathlib import Path

from .models import is_syntactically_valid_email


REQUIRED_COLUMNS = ("email", "reason", "recorded_at", "source_ref")


def load_suppression_ledger(path: str | Path) -> set[str]:
    path = Path(path)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = tuple(reader.fieldnames or ())
        missing = [column for column in REQUIRED_COLUMNS if column not in fields]
        if missing:
            raise ValueError(f"missing suppression columns: {', '.join(missing)}")

        suppressed: set[str] = set()
        for row_number, row in enumerate(reader, start=2):
            email = (row["email"] or "").strip()
            if not is_syntactically_valid_email(email):
                raise ValueError(f"row {row_number}: suppression email is missing or invalid")
            if not (row["reason"] or "").strip():
                raise ValueError(f"row {row_number}: suppression reason is required")
            if not (row["recorded_at"] or "").strip():
                raise ValueError(f"row {row_number}: suppression recorded_at is required")
            if not (row["source_ref"] or "").strip():
                raise ValueError(f"row {row_number}: suppression source_ref is required")
            suppressed.add(email.casefold())
    return suppressed
