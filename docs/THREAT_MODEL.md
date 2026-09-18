# Threat and privacy model

EmailFinder's first milestone is deliberately narrow: **build reviewable draft records from a bounded input list without sending anything**.

## Assets to protect

- contact provenance and verification state;
- suppression/unsubscribe state;
- operator approval state;
- private participant, account, credential, or access-controlled information.

## Prohibited behavior

The pipeline must fail closed rather than:

- infer an address from a person's name or an organization naming pattern;
- label syntax validation as mailbox verification;
- scrape access-controlled or sensitive personal data;
- bypass robots/access controls or provider limits;
- emit suppressed contacts;
- create a sender, SMTP/API integration, or unattended delivery path;
- treat a draft as an approved outreach action.

## Trust boundary

Input data is operator-supplied. The software validates structure, provenance fields, suppression, confidence, and explicit verification status; it cannot independently prove that an operator's provenance statement is true.

Every emitted record remains `DRAFT_ONLY` and `PENDING_HUMAN_APPROVAL`.

## Abuse resistance

- hard cap: 20 drafts per generated review batch;
- deduplication by normalized email;
- suppression always excludes;
- guessed/pattern-inferred verification methods are explicitly prohibited;
- public HTTP(S) provenance is required for eligible externally sourced contacts;
- no sending dependency or network contact-discovery implementation exists in v0.1.
