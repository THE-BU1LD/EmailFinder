from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pipeline import (
    MAX_DAILY_CAMPAIGN_CONTACTS,
    MAX_REVIEW_BATCH,
    build_review_batch,
    load_contacts,
    load_prior_review_emails,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a draft-only professional contact review batch.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build-drafts")
    build.add_argument("--input", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--max-batch", type=int, default=MAX_REVIEW_BATCH)
    build.add_argument("--min-confidence", type=float, default=0.8)
    build.add_argument(
        "--prior-batch",
        type=Path,
        action="append",
        default=[],
        help="Prior EmailFinder DRAFT_ONLY batch; repeat to deduplicate across earlier review batches.",
    )
    build.add_argument("--campaign-id", default="default")
    build.add_argument("--campaign-day", default="operator_unspecified")
    build.add_argument("--prior-campaign-count", type=int, default=0)
    build.add_argument(
        "--daily-campaign-cap",
        type=int,
        default=MAX_DAILY_CAMPAIGN_CONTACTS,
        help="Review-entry cap; cannot exceed the hard maximum of 50.",
    )

    args = parser.parse_args()
    contacts = load_contacts(args.input)
    prior_emails = load_prior_review_emails(args.prior_batch)
    payload = build_review_batch(
        contacts,
        max_batch=args.max_batch,
        min_confidence=args.min_confidence,
        prior_emails=prior_emails,
        campaign_id=args.campaign_id,
        campaign_day=args.campaign_day,
        prior_campaign_count=args.prior_campaign_count,
        daily_campaign_cap=args.daily_campaign_cap,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {payload['draft_count']} draft-only records to {args.output}")


if __name__ == "__main__":
    main()
