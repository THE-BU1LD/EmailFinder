from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pipeline import MAX_REVIEW_BATCH, build_review_batch, load_contacts


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a draft-only professional contact review batch.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build-drafts")
    build.add_argument("--input", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--max-batch", type=int, default=MAX_REVIEW_BATCH)
    build.add_argument("--min-confidence", type=float, default=0.8)

    args = parser.parse_args()
    contacts = load_contacts(args.input)
    payload = build_review_batch(
        contacts,
        max_batch=args.max_batch,
        min_confidence=args.min_confidence,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {payload['draft_count']} draft-only records to {args.output}")


if __name__ == "__main__":
    main()
