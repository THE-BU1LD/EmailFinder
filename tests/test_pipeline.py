from __future__ import annotations

import unittest

from emailfinder.models import ContactRecord
from emailfinder.pipeline import MAX_REVIEW_BATCH, build_review_batch


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

    def test_unverified_and_suppressed_contacts_are_excluded(self):
        payload = build_review_batch(
            [
                contact(2, verification_status="unverified"),
                contact(3, suppressed=True),
            ]
        )
        self.assertEqual(payload["draft_count"], 0)
        reasons = {item["reason"] for item in payload["excluded"]}
        self.assertEqual(reasons, {"not_verified", "suppressed"})

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


if __name__ == "__main__":
    unittest.main()
