from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


ALLOWED_SOURCE_TYPES = frozenset(
    {
        "user_provided",
        "organization_site",
        "public_professional_profile",
        "public_professional_directory",
    }
)

ALLOWED_VERIFICATION_METHODS = frozenset(
    {
        "user_provided",
        "public_source_exact_match",
        "organization_directory_exact_match",
        "manual_mailbox_verification",
    }
)

BLOCKED_VERIFICATION_METHODS = frozenset(
    {
        "guessed",
        "pattern_inferred",
        "name_pattern",
        "unverified_scrape",
    }
)

VERIFICATION_STATUSES = frozenset({"verified", "unverified", "unavailable"})


@dataclass(frozen=True)
class ContactRecord:
    row_number: int
    organization: str
    person_name: str
    role: str
    email: str
    source_url: str
    source_type: str
    verification_method: str
    verification_status: str
    verified_at: str
    confidence: float
    relevance_reason: str
    suppressed: bool

    @property
    def normalized_email(self) -> str:
        return self.email.strip().casefold()


def is_public_http_url(value: str) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def is_syntactically_valid_email(value: str) -> bool:
    value = value.strip()
    if not value or value.count("@") != 1 or any(ch.isspace() for ch in value):
        return False
    local, domain = value.rsplit("@", 1)
    return bool(local) and "." in domain and not domain.startswith(".") and not domain.endswith(".")
