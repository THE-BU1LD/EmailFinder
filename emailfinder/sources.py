from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import ALLOWED_SOURCE_TYPES, ContactRecord


@runtime_checkable
class ContactSourceAdapter(Protocol):
    """Interface for bounded, policy-approved contact-source adapters.

    Implementations may return only provenance-bearing professional records.
    This interface does not authorize scraping, access-control bypass, address
    guessing, or sending.
    """

    source_type: str

    def load(self) -> list[ContactRecord]:
        """Return bounded contact records with exact source provenance."""


def validate_source_adapter(adapter: ContactSourceAdapter) -> None:
    if adapter.source_type not in ALLOWED_SOURCE_TYPES:
        raise ValueError(f"source adapter type is not permitted: {adapter.source_type!r}")
