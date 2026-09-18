from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pipeline import MAX_REVIEW_BATCH, build_review_batch, load_contacts
from .suppression import load_suppression_ledger


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a draft-only professional contact review batch.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build-drafts")
    build.add_argument("--input", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--max-batch", type=int, default=MAX_REVIEW_BATCH)
    build.add_argument("--min-confidence", type=float, default=0.8)
    build.add_argument("--suppression-ledger", type=Path)

    args = parser.parse_args()
    contacts = load_contacts(args.input)
    suppressed = (
        load_suppression_ledger(args.suppression_ledger)
        if args.suppression_ledger is not None
        else set()
    )
    payload = build_review_batch(
        contacts,
        max_batch=args.max_batch,
        min_confidence=args.min_confidence,
        suppressed_emails=suppressed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {payload['draft_count']} draft-only records to {args.output}")


if __name__ == "__main__":
    main()
