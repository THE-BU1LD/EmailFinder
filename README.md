# EmailFinder

**Status: VERIFIED_DRAFT_PIPELINE v0.1 — no sending and no contact-discovery scraping.**

EmailFinder is a compliance-first pipeline for turning a **bounded operator-supplied professional contact CSV** into a provenance-bearing human review batch.

It does not discover contacts on the internet, guess email addresses, send messages, or claim that syntax checks prove mailbox ownership.

## Implemented v0.1

- typed contact/provenance records;
- explicit `verified`, `unverified`, and `unavailable` states;
- permitted source and verification-method allowlists;
- a source-adapter protocol for future bounded, policy-approved adapters;
- hard rejection of guessed/pattern-inferred addresses;
- per-record suppression handling;
- optional operator-maintained persistent suppression ledger applied across batches;
- confidence thresholding;
- deterministic deduplication within the current input;
- optional deduplication against one or more prior EmailFinder review-batch artifacts;
- hard maximum of **20 drafts per review batch**;
- hard maximum of **50 new review entries per day per campaign**, enforced from operator-supplied prior campaign state;
- output state fixed to `DRAFT_ONLY`;
- approval state fixed to `PENDING_HUMAN_APPROVAL`;
- exact-source CI, unit tests, and synthetic examples.

The pipeline still has **no sender integration** and **no network contact-discovery adapter**.

## Quick start

Python 3.11+; the v0.1 pipeline uses only the standard library.

```bash
python -m emailfinder.cli build-drafts \
  --input examples/contacts.csv \
  --suppression-ledger examples/suppression.csv \
  --output /tmp/review-batch.json
```

To deduplicate against a previous review batch and represent an existing daily campaign count:

```bash
python -m emailfinder.cli build-drafts \
  --input examples/contacts.csv \
  --suppression-ledger examples/suppression.csv \
  --prior-batch previous-review-batch.json \
  --campaign-id research-outreach \
  --campaign-day 2026-09-19 \
  --prior-campaign-count 30 \
  --output /tmp/review-batch.json
```

The suppression ledger is an operator-maintained CSV with columns `email,reason,recorded_at,source_ref`; its normalized addresses override otherwise eligible rows. The daily campaign count is still **operator-supplied state**, and cross-batch deduplication still depends on supplied prior review artifacts rather than a server-side campaign ledger.

## Input contract

Required CSV fields:

```text
organization,person_name,role,email,source_url,source_type,verification_method,
verification_status,verified_at,confidence,relevance_reason,suppressed
```

Allowed verification statuses are:

- `verified` — exact evidence supports using the address in a human review draft;
- `unverified` — evidence is incomplete; exclude from drafting;
- `unavailable` — no address is available; exclude and **do not guess**.

Unknown must remain unknown. An unavailable address does not authorize pattern guessing.

See:

- `docs/THREAT_MODEL.md`
- `docs/PERMITTED_SOURCES.md`
- `examples/contacts.csv`
- `examples/suppression.csv`

## Source adapters

`emailfinder.sources.ContactSourceAdapter` defines the contract for future bounded source adapters.

An adapter must identify a permitted source type and return `ContactRecord` values with exact provenance. The interface does **not** authorize scraping, access-control bypass, guessed addresses, or sending.

No network source adapter is included in v0.1.

## Hard boundaries

EmailFinder must not become a credential harvester, private-data scraper, guessed-address generator, or unattended spam sender.

Do not:

- infer an address from a name/domain pattern;
- collect passwords, tokens, private account data, or sensitive personal data;
- bypass access controls, robots policies, or provider limits;
- ignore suppression/unsubscribe state;
- treat a review-batch cap as permission to send;
- represent a prospect, reply, partnership, or affiliation as confirmed when it is not.

## Review-batch and daily limits

The software enforces at most **20** eligible records per generated review batch.

It also enforces a maximum of **50 new review entries per day per campaign** when the operator supplies the prior count for that campaign/day. Values above the hard cap fail closed.

These are review-safety boundaries, not sending authorization.

## Next safe milestones

1. add one bounded source-ingestion adapter only for explicitly permitted public professional sources;
2. preserve immutable retrieval/provenance receipts;
3. add a verification provider adapter that distinguishes syntax/domain/mailbox evidence;
4. add durable dedup/campaign state only with explicit retention and deletion policy, while preserving suppression precedence;
5. keep any future sender in a separate, explicitly authorized subsystem with a human approval transition.

## Repository routing

Canonical repository: `THE-BU1LD/EmailFinder`.
