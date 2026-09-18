from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from .models import (
    ALLOWED_SOURCE_TYPES,
    ALLOWED_VERIFICATION_METHODS,
    BLOCKED_VERIFICATION_METHODS,
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
                    verification_status=(row["verification_status"] or "").strip().casefold(),
                    verified_at=(row["verified_at"] or "").strip(),
                    confidence=_parse_confidence(row["confidence"] or "", row_number),
                    relevance_reason=(row["relevance_reason"] or "").strip(),
                    suppressed=_parse_bool(row["suppressed"] or "", row_number),
                )
            )
    return contacts


def _eligibility_reason(contact: ContactRecord, min_confidence: float) -> str | None:
    if contact.suppressed:
        return "suppressed"
    if contact.verification_method in BLOCKED_VERIFICATION_METHODS:
        return "guessed_or_inferred_address_prohibited"
    if contact.source_type not in ALLOWED_SOURCE_TYPES:
        return "source_type_not_permitted"
    if contact.verification_method not in ALLOWED_VERIFICATION_METHODS:
        return "verification_method_not_permitted"
    if contact.verification_status != "verified":
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
        "reason": reason,
    }


def build_review_batch(
    contacts: list[ContactRecord],
    *,
    max_batch: int = MAX_REVIEW_BATCH,
    min_confidence: float = 0.8,
) -> dict[str, object]:
    if not 1 <= max_batch <= MAX_REVIEW_BATCH:
        raise ValueError(f"max_batch must be between 1 and {MAX_REVIEW_BATCH}")
    if not 0.0 <= min_confidence <= 1.0:
        raise ValueError("min_confidence must be within [0, 1]")

    eligible: list[ContactRecord] = []
    excluded: list[dict[str, object]] = []

    for contact in contacts:
        reason = _eligibility_reason(contact, min_confidence)
        if reason is None:
            eligible.append(contact)
        else:
            excluded.append(_excluded(contact, reason))

    # For duplicate verified addresses, retain the highest-confidence provenance record.
    ranked = sorted(eligible, key=lambda item: (-item.confidence, item.row_number))
    deduped: dict[str, ContactRecord] = {}
    for contact in ranked:
        key = contact.normalized_email
        if key in deduped:
            excluded.append(_excluded(contact, "duplicate_email"))
            continue
        deduped[key] = contact

    selected = sorted(deduped.values(), key=lambda item: item.row_number)
    overflow = selected[max_batch:]
    selected = selected[:max_batch]
    for contact in overflow:
        excluded.append(_excluded(contact, "batch_cap_deferred"))

    drafts = [_draft(contact) for contact in selected]
    return {
        "schema_version": "emailfinder.review-batch.v0.1",
        "mode": "DRAFT_ONLY",
        "max_batch": max_batch,
        "min_confidence": min_confidence,
        "draft_count": len(drafts),
        "excluded_count": len(excluded),
        "drafts": drafts,
        "excluded": sorted(excluded, key=lambda item: item["row_number"]),
    }
