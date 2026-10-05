# eBible KJV Strong's Source Provenance

## Purpose

This document records the upstream source selected for the GD Bible
Strong's alignment migration.

It applies specifically to the source used to obtain embedded Hebrew and
Greek Strong's identifiers. It does not replace the canonical GD Bible text
and does not authorize the source text to overwrite GD wording.

## Source identity

| Field | Value |
|---|---|
| Provider | eBible.org |
| Package | King James Version + Apocrypha |
| Format | USFM |
| Download | `https://ebible.org/Scriptures/eng-kjv_usfm.zip` |
| Retrieval date | 2026-10-04 |
| Package source files dated | 2026-09-26 |
| eBible package generation date | 2026-10-03 |
| Archive SHA-256 | `0e0359e9e488582a72c86800f227839ecb16dada7bb5ba316509d374c59e559a` |

The exact downloaded archive is preserved outside the Git worktree in the
verified project backup set.

The Git repository intentionally ignores ZIP archives. Reproducibility is
therefore based on the recorded source URL, pinned archive checksum, and the
per-book checksums in:

`EBIBLE_KJV_STRONGS_SOURCE_MANIFEST.json`

## Canonical-book selection

The downloaded package contains the King James Version with
Apocrypha/Deuterocanon and front matter.

GD and GD+ use only the 66 canonical Protestant Bible books.

The Strong's source migration therefore:

- accepts exactly 66 canonical USFM book files
- rejects accidental inclusion of Apocrypha/Deuterocanon files
- excludes front matter
- validates each canonical USFM file against its recorded SHA-256 checksum
- validates the downloaded archive against its pinned SHA-256 checksum

## Role of this source

The eBible USFM files contain embedded Strong's annotations such as:

`strong="H7225"`

and:

`strong="G####"`

These identifiers are source data for the GD+ Strong's alignment process.

They are not permission to replace GD Scripture wording.

The authoritative displayed Scripture remains the canonical GD/KJV source
maintained by this project.

## Alignment rule

Strong's identifiers may be transferred only when the corresponding source
word can be positively and deterministically aligned to the canonical
displayed Scripture.

The migration must obey these rules:

1. GD/KJV canonical text remains authoritative.
2. Source wording never silently replaces canonical wording.
3. A Strong's identifier is attached only to a positively matched word.
4. Translator-added or unmatched words are not assigned invented identifiers.
5. Every generated aligned verse must reconstruct the canonical displayed
   text exactly.
6. Any unresolved verse must remain readable without claiming an uncertain
   word-level Strong's alignment.

## Structural audit completed before migration

The eBible source was compared against all 31,102 canonical GD/KJV verse
coordinates.

The audit established:

- 31,102 canonical verses
- 31,102 corresponding eBible canonical verse coordinates
- 0 missing canonical coordinates
- 30,917 verses reducible to safe text-equivalence candidates after
  formatting, heading, and structural normalization
- 185 initially classified structural/text differences

Those 185 cases were further classified as:

- 115 Psalm superscription-only differences
- 43 Psalm 119 section-label shifts
- 13 New Testament subscription-only differences
- 3 canonical editorial-note differences
- 11 initially classified text differences

Further inspection showed that several of those 11 were structural or simple
orthographic cases. Seven verses remained materially different in visible
wording:

- Genesis 30:27
- Genesis 42:34
- Leviticus 23:21
- Job 36:5
- Psalms 18:41
- Isaiah 6:13
- Jeremiah 22:16

All seven were individually inspected in raw USFM.

The differing eBible phrases are translator-added/un-numbered material while
the Strong's-bearing lexical words needed for deterministic projection remain
present.

No Strong's identifier needs to be invented to handle these differences.

## Strong's coverage observed in source

The pre-migration audit found:

- canonical verses inspected: 31,102
- verses containing one or more Strong's annotations: 31,099
- verses containing no Strong's annotations: 3
- Strong's attributes observed: 348,884
- parsed Strong's IDs: 348,884
- multi-ID attributes: 0
- unparsed Strong's attribute values: 0

The three canonical verses with no embedded Strong's annotations in the
eBible source are:

- Mark 9:43
- Luke 6:41
- Luke 17:36

These are unresolved source-coverage cases, not missing Scripture verses.

GD+ must not fabricate word-level Strong's assignments for them.

## Rights information recorded from the package

The package's own `copr.htm` identifies the King James Version text as
Public Domain and states that it may be copied freely.

The same rights file expressly notes the special Authorized Version rights
situation in the United Kingdom and states that the public-domain position
described there applies outside the UK.

GD Bible has separately submitted a preliminary permissions inquiry to
Cambridge University Press & Assessment concerning intended distribution of
the custom KJV-derived GD editions in relevant UK territories.

No UK authorization is claimed while that inquiry is unresolved.

## Important rights limitation

The package rights page expressly addresses the King James Version text.

This project has not yet established, from that page alone, separate legal
provenance for the creation or licensing history of every embedded Strong's
tag.

Therefore this record does NOT make the stronger claim that the Strong's
annotation layer has independently proven rights provenance.

That question remains an explicit source-rights audit item before final
public release.

## Relationship to the previous Kaiserlik source

The existing GD production inline alignment was generated from
`kaiserlik/kjv`.

That source is being replaced because its provenance/licensing record was
not sufficiently clear for the audit standard required by this project.

The historical implementation and generated results are retained in Git
history and backups.

The eBible migration must be validated alongside the existing implementation
before the production alignment assets are replaced.

## Reproducibility

A future generator must verify:

1. the archive SHA-256
2. exactly 66 selected canonical USFM books
3. every selected file against
   `EBIBLE_KJV_STRONGS_SOURCE_MANIFEST.json`
4. the expected 31,102 canonical verse coordinates
5. canonical-text reconstruction after alignment
6. Strong's ID syntax and counts
7. explicit accounting for verses without source Strong's data

A source package that does not match the pinned checksums must not silently
produce release assets.

## Known documentation corrections still required

Existing historical documentation contains stale statements that must be
corrected as part of this migration, including:

- an overly broad statement that the KJV is public domain "worldwide"
- obsolete Kaiserlik-based Strong's coverage totals
- obsolete descriptions of Phase 1 runtime consumers
- obsolete Schema 2 alignment totals

Those historical documents are not being silently rewritten before the new
migration is proven. They will be updated with the migration audit trail
preserved.

## Status

**PROVENANCE RECORDED — PRODUCTION MIGRATION NOT YET COMPLETE**

Creating this record does not replace current production Strong's assets.
