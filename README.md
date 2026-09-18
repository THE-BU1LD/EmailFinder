# EmailFinder

**Status: VERIFIED_DRAFT_PIPELINE v0.1 — no sending and no contact-discovery scraping.**

EmailFinder now provides a small compliance-first pipeline for turning a **bounded operator-supplied contact CSV** into a provenance-bearing human review batch.

It does not discover contacts on the internet, guess email addresses, send messages, or claim that syntax checks prove mailbox ownership.

## Implemented v0.1

- typed contact/provenance records;
- explicit permitted source and verification-method allowlists;
- hard rejection of guessed/pattern-inferred addresses;
- suppression handling;
- confidence thresholding;
- deterministic email deduplication;
- hard maximum of **20 drafts per review batch**;
- output state fixed to `DRAFT_ONLY`;
- approval state fixed to `PENDING_HUMAN_APPROVAL`;
- exact-source CI, unit tests, and a synthetic example.

## Quick start

Python 3.11+; the v0.1 pipeline uses only the standard library.

```bash
python -m emailfinder.cli build-drafts \
  --input examples/contacts.csv \
  --output /tmp/review-batch.json
```

The output includes eligible drafts plus excluded records and their fail-closed reason.

## Input contract

Required CSV fields:

```text
organization,person_name,role,email,source_url,source_type,verification_method,
verification_status,verified_at,confidence,relevance_reason,suppressed
```

Unknown must remain unknown. An unavailable address does **not** authorize pattern guessing.

See:

- `docs/THREAT_MODEL.md`
- `docs/PERMITTED_SOURCES.md`
- `examples/contacts.csv`

## Hard boundaries

EmailFinder must not become a credential harvester, private-data scraper, guessed-address generator, or unattended spam sender.

The v0.1 repository contains **no sender integration**. Generating a review batch is not approval to contact anyone.

Do not:

- infer an address from a name/domain pattern;
- collect passwords, tokens, private account data, or sensitive personal data;
- bypass access controls, robots policies, or provider limits;
- ignore suppression/unsubscribe state;
- represent a prospect, reply, partnership, or affiliation as confirmed when it is not.

## Review-batch limits

The software enforces at most **20** eligible records per generated batch. Lower values can be requested with `--max-batch`; values above 20 fail closed.

This cap is a review-safety boundary, not permission to send 20 messages.

## Next safe milestones

1. add a source-ingestion adapter only for explicitly permitted public professional sources;
2. preserve immutable retrieval/provenance receipts;
3. add a verification provider adapter that distinguishes syntax/domain/mailbox evidence;
4. add a persistent suppression/deduplication ledger;
5. keep any future sender in a separate explicitly authorized subsystem rather than this discovery/draft pipeline.

## Repository routing

Canonical repository: `THE-BU1LD/EmailFinder`.
