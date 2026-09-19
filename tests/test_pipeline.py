from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from emailfinder.models import ContactRecord
from emailfinder.pipeline import (
    MAX_DAILY_CAMPAIGN_CONTACTS,
    MAX_REVIEW_BATCH,
    build_review_batch,
    load_prior_review_emails,
)
from emailfinder.sources import ContactSourceAdapter, validate_source_adapter


def contact(
    row_number: int,
    *,
    email: str | None = None,
    confidence: float = 0.95,
    suppressed: bool = False,
    verification_method: str = "public_source_exact_match",
    verification_status: str = "verified",
    source_url: str | None = None,
) -> ContactRecord:
    address = email if email is not None else f"person{row_number}@example.com"
    return ContactRecord(
        row_number=row_number,
        organization=f"Example Org {row_number}",
        person_name=f"Example Person {row_number}",
        role="Researcher",
        email=address,
        source_url=source_url or f"https://example.com/team/{row_number}",
        source_type="organization_site",
        verification_method=verification_method,
        verification_status=verification_status,
        verified_at="2026-09-18T00:00:00Z",
        confidence=confidence,
        relevance_reason="Public professional role matches the bounded research topic.",
        suppressed=suppressed,
    )


class DraftPipelineTests(unittest.TestCase):
    def test_verified_contact_becomes_human_review_draft(self):
        payload = build_review_batch([contact(2)])
        self.assertEqual(payload["mode"], "DRAFT_ONLY")
        self.assertEqual(payload["draft_count"], 1)
        draft = payload["drafts"][0]
        self.assertEqual(draft["outreach_state"], "DRAFT_ONLY")
        self.assertEqual(draft["approval_state"], "PENDING_HUMAN_APPROVAL")
        self.assertNotIn("send", draft)
        self.assertNotIn("message", draft)

    def test_guessed_or_pattern_inferred_address_is_never_drafted(self):
        payload = build_review_batch(
            [contact(2, verification_method="pattern_inferred")]
        )
        self.assertEqual(payload["draft_count"], 0)
        self.assertEqual(
            payload["excluded"][0]["reason"],
            "guessed_or_inferred_address_prohibited",
        )

    def test_unverified_unavailable_and_suppressed_contacts_are_distinct(self):
        payload = build_review_batch(
            [
                contact(2, verification_status="unverified"),
                contact(3, email="", verification_status="unavailable"),
                contact(4, suppressed=True),
            ]
        )
        self.assertEqual(payload["draft_count"], 0)
        reasons = {item["reason"] for item in payload["excluded"]}
        self.assertEqual(reasons, {"not_verified", "address_unavailable", "suppressed"})

    def test_duplicate_email_keeps_highest_confidence_record(self):
        payload = build_review_batch(
            [
                contact(2, email="Same@Example.com", confidence=0.85),
                contact(3, email="same@example.com", confidence=0.99),
            ]
        )
        self.assertEqual(payload["draft_count"], 1)
        self.assertEqual(payload["drafts"][0]["confidence"], 0.99)
        self.assertIn("duplicate_email", {x["reason"] for x in payload["excluded"]})

    def test_prior_review_batch_addresses_are_deduplicated(self):
        payload = build_review_batch(
            [contact(2, email="prior@example.com"), contact(3)],
            prior_emails={"PRIOR@example.com"},
        )
        self.assertEqual(payload["draft_count"], 1)
        self.assertEqual(payload["drafts"][0]["email"], "person3@example.com")
        self.assertIn("prior_record_duplicate", {x["reason"] for x in payload["excluded"]})

    def test_prior_batch_loader_accepts_only_draft_pipeline_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prior.json"
            path.write_text(
                json.dumps(
                    {
                        "mode": "DRAFT_ONLY",
                        "drafts": [{"email": "Past@Example.com"}],
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(load_prior_review_emails([path]), {"past@example.com"})

            path.write_text(json.dumps({"mode": "SEND", "drafts": []}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_prior_review_emails([path])

    def test_invalid_source_url_fails_closed(self):
        payload = build_review_batch(
            [contact(2, source_url="file:///private/contact.txt")]
        )
        self.assertEqual(payload["draft_count"], 0)
        self.assertEqual(payload["excluded"][0]["reason"], "missing_or_invalid_source_url")

    def test_batch_cap_is_hard_limited_to_twenty(self):
        contacts = [contact(row) for row in range(2, 27)]
        payload = build_review_batch(contacts, max_batch=MAX_REVIEW_BATCH)
        self.assertEqual(payload["draft_count"], 20)
        deferred = [x for x in payload["excluded"] if x["reason"] == "batch_cap_deferred"]
        self.assertEqual(len(deferred), 5)

        with self.assertRaises(ValueError):
            build_review_batch(contacts, max_batch=MAX_REVIEW_BATCH + 1)

    def test_daily_campaign_cap_is_enforced_from_operator_supplied_state(self):
        contacts = [contact(row) for row in range(2, 5)]
        payload = build_review_batch(
            contacts,
            campaign_id="research-review",
            campaign_day="2026-09-19",
            prior_campaign_count=49,
        )
        self.assertEqual(payload["draft_count"], 1)
        self.assertEqual(payload["campaign"]["daily_cap"], MAX_DAILY_CAMPAIGN_CONTACTS)
        self.assertEqual(payload["campaign"]["projected_count"], 50)
        self.assertEqual(payload["campaign"]["remaining_after_batch"], 0)
        deferred = [
            item
            for item in payload["excluded"]
            if item["reason"] == "daily_campaign_cap_deferred"
        ]
        self.assertEqual(len(deferred), 2)

        with self.assertRaises(ValueError):
            build_review_batch(contacts, prior_campaign_count=51)

    def test_source_adapter_contract_rejects_unpermitted_types(self):
        class AllowedAdapter:
            source_type = "organization_site"

            def load(self) -> list[ContactRecord]:
                return [contact(2)]

        class BlockedAdapter:
            source_type = "private_scrape"

            def load(self) -> list[ContactRecord]:
                return [contact(2)]

        allowed = AllowedAdapter()
        self.assertIsInstance(allowed, ContactSourceAdapter)
        validate_source_adapter(allowed)

        with self.assertRaises(ValueError):
            validate_source_adapter(BlockedAdapter())


if __name__ == "__main__":
    unittest.main()
