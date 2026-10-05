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

The pinned eBible package was audited across all 31,102 canonical verse
coordinates.

Observed eBible Strong's coverage:

- 31,102 canonical verse coordinates
- 31,099 verses containing Strong's annotations
- 3 verses containing no Strong's annotations
- 348,884 Strong's attributes
- 348,884 deterministically mapped Strong's markers
- 0 unresolved Strong's markers
- 0 canonical reconstruction failures

The three eBible verses without Strong's annotations are:

- Mark 9:43
- Luke 6:41
- Luke 17:36

Those three verses are supplied by the separately pinned CrossWire KJV
fallback source recorded in:

`CROSSWIRE_KJV_STRONGS_FALLBACK_MANIFEST.json`

CrossWire contributes:

- Mark 9:43 — 32 markers
- Luke 6:41 — 22 markers
- Luke 17:36 — 12 markers
- total — 66 markers

Luke 17:36 contains a canonical editorial note after the source verse.
That editorial note remains explicitly untagged.

Verified production result:

- 31,102 standard aligned verses
- 0 standard fallbacks
- 348,950 standard Strong's markers
- 31,102 GD+ projected verses
- 0 GD+ projection fallbacks
- 348,902 retained GD+ Strong's markers
- 48 markers conservatively not transferred across changed GD wording
- 0 reconstruction failures

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

The historical GD alignment was generated from `kaiserlik/kjv`.

That source did not have a sufficiently clear provenance/licensing record
for the audit standard required by this project.

The active Schema 2.0 production alignment has now been regenerated without
requiring Kaiserlik:

- primary source: pinned eBible `eng-kjv` USFM
- eBible contribution: 31,099 verses / 348,884 markers
- residual source: pinned CrossWire KJV
- CrossWire contribution: 3 verses / 66 markers
- final production alignment: 31,102 verses / 348,950 markers
- production fallbacks: 0

Historical Kaiserlik-derived files may remain for audit or legacy
compatibility, but Kaiserlik is no longer the upstream source for the active
Schema 2.0 inline alignment.

## Reproducibility

A reproducible regeneration must verify:

1. the pinned eBible archive SHA-256
2. exactly 66 canonical eBible USFM files
3. every selected eBible file against
   `EBIBLE_KJV_STRONGS_SOURCE_MANIFEST.json`
4. all 31,102 canonical verse coordinates
5. all 348,884 mapped eBible Strong's markers
6. the pinned CrossWire repository commit
7. the pinned CrossWire OSIS and configuration checksums
8. CrossWire scope of exactly Mark 9:43, Luke 6:41, and Luke 17:36
9. exactly 66 CrossWire markers
10. canonical reconstruction for every aligned verse
11. final standard total of 348,950 Strong's markers
12. final GD+ total of 348,902 retained Strong's markers
13. zero standard and GD+ fallbacks

A source that does not match the pinned checksums must not silently produce
release assets.

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

**PRODUCTION STRONG'S MIGRATION COMPLETE — TECHNICAL VALIDATION PASSED**

Verified production state:

- 66 books
- 31,102 canonical verses
- 31,102 standard aligned verses
- 0 standard fallbacks
- 348,950 standard Strong's markers
- 31,102 GD+ projected verses
- 0 GD+ projection fallbacks
- 348,902 GD+ Strong's markers
- 0 reconstruction failures

The active Schema 2.0 alignment no longer requires Kaiserlik.

Technical completion does not by itself resolve every third-party rights
question. The independent provenance/licensing status of the eBible
Strong's annotation layer and CrossWire's recorded license statements remain
explicit release-audit items.
