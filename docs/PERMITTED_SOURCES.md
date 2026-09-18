# Permitted source policy

For the v0.1 draft pipeline, only bounded records with explicit provenance are accepted for drafting.

## Permitted source types

- `user_provided` — a contact supplied directly by an authorized operator;
- `organization_site` — a public professional page on the person's organization;
- `public_professional_profile` — a public professional profile intended for professional visibility;
- `public_professional_directory` — a public professional directory.

## Permitted verification methods

- `user_provided`;
- `public_source_exact_match`;
- `organization_directory_exact_match`;
- `manual_mailbox_verification`.

These labels are retained as provenance. They are not interchangeable with identity proof, consent, or approval to send.

## Explicitly prohibited

- guessed addresses;
- pattern-inferred addresses;
- private/non-professional contact scraping;
- credential or session-token collection;
- bypassing access controls;
- replacing unknown with a fabricated value.

When the address or provenance cannot be verified, leave it unknown and exclude it from the draft batch.
