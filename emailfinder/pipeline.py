from __future__ import annotations

import csv
import json
from collections.abc import Collection, Iterable
from pathlib import Path

from .models import (
    ALLOWED_SOURCE_TYPES,
    ALLOWED_VERIFICATION_METHODS,
    BLOCKED_VERIFICATION_METHODS,
    VERIFICATION_STATUSES,
    ContactRecord,
    is_public_http_url,
    is_syntactically_valid_email,
)


REQUIRED_COLUMNS = (
    "organization",
    "person_name",
    "role",
    "email",
    "source_url",
    "source_type",
    "verification_method",
    "verification_status",
    "verified_at",
    "confidence",
    "relevance_reason",
    "suppressed",
)

MAX_REVIEW_BATCH = 20
MAX_DAILY_CAMPAIGN_CONTACTS = 50


def _parse_bool(value: str, row_number: int) -> bool:
    normalized = value.strip().casefold()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no", ""}:
        return False
    raise ValueError(f"row {row_number}: suppressed must be true/false")


def _parse_confidence(value: str, row_number: int) -> float:
    try:
        confidence = float(value)
    except ValueError as exc:
        raise ValueError(f"row {row_number}: confidence must be numeric") from exc
    if not 0.0 <= confidence <= 1.0:
        raise ValueError(f"row {row_number}: confidence must be within [0, 1]")
    return confidence


def load_contacts(path: str | Path) -> list[ContactRecord]:
    path = Path(path)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = tuple(reader.fieldnames or ())
        missing = [column for column in REQUIRED_COLUMNS if column not in fields]
        if missing:
            raise ValueError(f"missing required columns: {', '.join(missing)}")

        contacts: list[ContactRecord] = []
        for row_number, row in enumerate(reader, start=2):
            verification_status = (row["verification_status"] or "").strip().casefold()
            if verification_status not in VERIFICATION_STATUSES:
                raise ValueError(
                    f"row {row_number}: verification_status must be one of "
                    f"{sorted(VERIFICATION_STATUSES)}"
                )
            contacts.append(
                ContactRecord(
                    row_number=row_number,
                    organization=(row["organization"] or "").strip(),
                    person_name=(row["person_name"] or "").strip(),
                    role=(row["role"] or "").strip(),
                    email=(row["email"] or "").strip(),
                    source_url=(row["source_url"] or "").strip(),
                    source_type=(row["source_type"] or "").strip().casefold(),
                    verification_method=(row["verification_method"] or "").strip().casefold(),
                    verification_status=verification_status,
                    verified_at=(row["verified_at"] or "").strip(),
                    confidence=_parse_confidence(row["confidence"] or "", row_number),
                    relevance_reason=(row["relevance_reason"] or "").strip(),
                    suppressed=_parse_bool(row["suppressed"] or "", row_number),
                )
            )
    return contacts


def load_prior_review_emails(paths: Iterable[str | Path]) -> set[str]:
    """Load normalized addresses from prior EmailFinder review-batch artifacts.

    This supports deterministic cross-batch deduplication without silently
    mutating a persistent ledger. A durable suppression/dedup ledger remains a
    separate future milestone.
    """

    seen: set[str] = set()
    for raw_path in paths:
        path = Path(raw_path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("mode") != "DRAFT_ONLY":
            raise ValueError(f"{path}: prior batch must be an EmailFinder DRAFT_ONLY object")
        drafts = payload.get("drafts")
        if not isinstance(drafts, list):
            raise ValueError(f"{path}: prior batch drafts must be a list")
        for index, draft in enumerate(drafts):
            if not isinstance(draft, dict):
                raise ValueError(f"{path}: draft {index} must be an object")
            email = draft.get("email")
            if not isinstance(email, str) or not is_syntactically_valid_email(email):
                raise ValueError(f"{path}: draft {index} has no valid email")
            seen.add(email.strip().casefold())
    return seen


def _eligibility_reason(contact: ContactRecord, min_confidence: float) -> str | None:
    if contact.suppressed:
        return "suppressed"
    if contact.verification_method in BLOCKED_VERIFICATION_METHODS:
        return "guessed_or_inferred_address_prohibited"
    if contact.source_type not in ALLOWED_SOURCE_TYPES:
        return "source_type_not_permitted"
    if contact.verification_method not in ALLOWED_VERIFICATION_METHODS:
        return "verification_method_not_permitted"
    if contact.verification_status not in VERIFICATION_STATUSES:
        return "verification_status_not_permitted"
    if contact.verification_status == "unavailable":
        return "address_unavailable"
    if contact.verification_status == "unverified":
        return "not_verified"
    if not is_syntactically_valid_email(contact.email):
        return "missing_or_invalid_email"
    if not is_public_http_url(contact.source_url):
        return "missing_or_invalid_source_url"
    if not contact.verified_at:
        return "missing_verification_timestamp"
    if not contact.organization or not contact.relevance_reason:
        return "missing_qualification_context"
    if contact.confidence < min_confidence:
        return "below_confidence_threshold"
    return None


def _draft(contact: ContactRecord) -> dict[str, object]:
    return {
        "organization": contact.organization,
        "person_name": contact.person_name,
        "role": contact.role,
        "email": contact.email,
        "source_url": contact.source_url,
        "source_type": contact.source_type,
        "verification_method": contact.verification_method,
        "verification_status": contact.verification_status,
        "verified_at": contact.verified_at,
        "confidence": contact.confidence,
        "relevance_reason": contact.relevance_reason,
        "outreach_state": "DRAFT_ONLY",
        "approval_state": "PENDING_HUMAN_APPROVAL",
    }


def _excluded(contact: ContactRecord, reason: str) -> dict[str, object]:
    return {
        "row_number": contact.row_number,
        "email": contact.email,
        "organization": contact.organization,
        "verification_status": contact.verification_status,
        "reason": reason,
    }


def _normalize_prior_emails(prior_emails: Collection[str]) -> set[str]:
    normalized: set[str] = set()
    for value in prior_emails:
        if not isinstance(value, str):
            raise TypeError("prior_emails must contain strings")
        value = value.strip().casefold()
        if value:
            normalized.add(value)
    return normalized


def build_review_batch(
    contacts: list[ContactRecord],
    *,
    max_batch: int = MAX_REVIEW_BATCH,
    min_confidence: float = 0.8,
    prior_emails: Collection[str] = (),
    campaign_id: str = "default",
    campaign_day: str = "operator_unspecified",
    prior_campaign_count: int = 0,
    daily_campaign_cap: int = MAX_DAILY_CAMPAIGN_CONTACTS,
) -> dict[str, object]:
    if not 1 <= max_batch <= MAX_REVIEW_BATCH:
        raise ValueError(f"max_batch must be between 1 and {MAX_REVIEW_BATCH}")
    if not 0.0 <= min_confidence <= 1.0:
        raise ValueError("min_confidence must be within [0, 1]")
    if not campaign_id.strip():
        raise ValueError("campaign_id must be non-empty")
    if not campaign_day.strip():
        raise ValueError("campaign_day must be non-empty")
    if isinstance(daily_campaign_cap, bool) or not isinstance(daily_campaign_cap, int):
        raise TypeError("daily_campaign_cap must be an integer")
    if not 1 <= daily_campaign_cap <= MAX_DAILY_CAMPAIGN_CONTACTS:
        raise ValueError(
            f"daily_campaign_cap must be between 1 and {MAX_DAILY_CAMPAIGN_CONTACTS}"
        )
    if isinstance(prior_campaign_count, bool) or not isinstance(prior_campaign_count, int):
        raise TypeError("prior_campaign_count must be an integer")
    if not 0 <= prior_campaign_count <= daily_campaign_cap:
        raise ValueError("prior_campaign_count must be between zero and daily_campaign_cap")

    prior_keys = _normalize_prior_emails(prior_emails)
    eligible: list[ContactRecord] = []
    excluded: list[dict[str, object]] = []

    for contact in contacts:
        reason = _eligibility_reason(contact, min_confidence)
        if reason is None and contact.normalized_email in prior_keys:
            reason = "prior_record_duplicate"
        if reason is None:
            eligible.append(contact)
        else:
            excluded.append(_excluded(contact, reason))

    # For duplicate verified addresses in the current input, retain the
    # highest-confidence provenance record.
    ranked = sorted(eligible, key=lambda item: (-item.confidence, item.row_number))
    deduped: dict[str, ContactRecord] = {}
    for contact in ranked:
        key = contact.normalized_email
        if key in deduped:
            excluded.append(_excluded(contact, "duplicate_email"))
            continue
        deduped[key] = contact

    candidates = sorted(deduped.values(), key=lambda item: item.row_number)
    daily_remaining_before = daily_campaign_cap - prior_campaign_count
    selection_limit = min(max_batch, daily_remaining_before)
    selected = candidates[:selection_limit]
    overflow = candidates[selection_limit:]
    overflow_reason = (
        "daily_campaign_cap_deferred"
        if daily_remaining_before < max_batch
        else "batch_cap_deferred"
    )
    for contact in overflow:
        excluded.append(_excluded(contact, overflow_reason))

    drafts = [_draft(contact) for contact in selected]
    projected_campaign_count = prior_campaign_count + len(drafts)
    return {
        "schema_version": "emailfinder.review-batch.v0.1",
        "mode": "DRAFT_ONLY",
        "max_batch": max_batch,
        "min_confidence": min_confidence,
        "prior_email_count": len(prior_keys),
        "campaign": {
            "campaign_id": campaign_id,
            "campaign_day": campaign_day,
            "daily_cap": daily_campaign_cap,
            "prior_count": prior_campaign_count,
            "projected_count": projected_campaign_count,
            "remaining_after_batch": daily_campaign_cap - projected_campaign_count,
        },
        "draft_count": len(drafts),
        "excluded_count": len(excluded),
        "drafts": drafts,
        "excluded": sorted(excluded, key=lambda item: item["row_number"]),
    }
