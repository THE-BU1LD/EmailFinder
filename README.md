# EmailFinder

> **Status: placeholder / specification only. No contact-discovery implementation is currently committed.**

EmailFinder is intended to become a **compliance-first professional contact research helper** for legitimate outreach workflows. The repository name does not imply that it can currently find, verify, enrich, or send email.

Canonical repository: `THE-BU1LD/EmailFinder`.

## Intended scope

A future implementation may help an operator:

1. ingest a bounded set of target organizations/people;
2. collect contact information from permitted public professional sources or user-provided records;
3. retain the exact source/provenance for each contact;
4. verify rather than guess email addresses;
5. score relevance and confidence;
6. deduplicate against prior/current outreach;
7. prepare **draft-only** outreach records for human approval.

## Hard boundaries

EmailFinder must not become a credential harvester, private-data scraper, guessed-address generator, or unattended spam sender.

Do not:

- infer or fabricate an email address from a naming pattern and call it verified;
- collect passwords, session tokens, private account data, or access-controlled records;
- scrape sensitive personal data or non-professional personal contact details;
- bypass robots/access controls or provider rate limits;
- evade unsubscribe/suppression records;
- automatically message every discovered contact;
- represent a prospect, reply, partnership, sponsorship, or affiliation as confirmed when it is not.

## Default operating mode

The safe default is **DRAFT_ONLY**.

A future pipeline should keep discovery and sending separate:

```text
DISCOVER
  -> VERIFY
  -> QUALIFY
  -> DEDUPLICATE
  -> PERSONALIZE
  -> VALIDATE
  -> APPROVE
  -> SEND
```

Only the final `SEND` transition may contact someone, and it requires explicit campaign authorization outside the discovery step.

Conservative operational limits for any future approved campaign:

- at most 20 newly discovered contacts per review batch;
- at most 50 new contacts per day per campaign;
- deduplicate before drafting or sending;
- maintain suppression/unsubscribe state;
- retain source and verification confidence;
- stop rather than guess when an address cannot be verified.

## Data model requirements

Every contact record should eventually carry, at minimum:

- organization;
- person/name when legitimately available;
- role/title;
- source URL or source record;
- source type;
- verification method;
- verification timestamp;
- confidence;
- relevance reason;
- deduplication key/state;
- outreach state;
- suppression/unsubscribe state;
- reviewer/approval state.

Unknown must remain unknown. A blank or unavailable address is not a failure condition that authorizes guessing.

## Repository maturity

There is currently **no implementation** in this repository beyond the license. Before calling EmailFinder operational, add:

1. a threat/privacy model;
2. a permitted-source policy;
3. a typed contact/provenance schema;
4. verification and deduplication tests;
5. rate-limit and suppression tests;
6. a draft-only output path;
7. CI;
8. an explicit approval boundary for any sender integration.

## Success criterion

The first meaningful milestone is **VERIFIED_DRAFT_PIPELINE**: given a bounded input list and permitted sources, produce deduplicated, provenance-bearing, reviewable contact drafts **without sending anything and without guessing missing addresses**.
