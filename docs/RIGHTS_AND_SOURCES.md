# GD Bible — Rights, Sources, and Transfer Status

## Purpose

This document records the provenance and rights status of the principal
materials used to build the GD Bible (Grow Daily), including GD and GD+.

Its purpose is to make the project auditable and transferable without losing
the history of where Bible text, Strong's data, words-of-Jesus markup, custom
editorial work, software, and branding originated.

This document records the project's present understanding. It should be
updated whenever an upstream source, license, or distribution method changes.

## Project ownership and stewardship

The canonical development repository is presently maintained by LionGateOS.

The public-facing Bible brand is:

- GD Bible
- GD = Grow Daily
- GD = Grow Daily - Custom King James Version
- GD+ = Grow Daily - Custom King James Version with Strong's Numbers

LionGateOS owns the original project work that LionGateOS created, subject to
the status of underlying public-domain and third-party source materials.

That original work includes, as applicable:

- GD-specific Bible wording revisions
- editorial documentation
- GD branding and project-created artwork
- build and validation software
- Bible transformation software
- project-created metadata
- project-created documentation
- project-created tests and validation records
- project-created packaging work


## King James Version Bible text

Primary underlying Bible tradition:

- King James Version / Authorized Version
- standardized 1769 KJV text
- 66-book canonical GD source structure contains 31,102 verses after the
  project's canonical structural repair

Outside the United Kingdom, the KJV source used by this project is treated as
public domain.

eBible identifies its KJV editions, including the KJV USFM source used during
the present words-of-Jesus investigation, as public domain.

### United Kingdom special status

The Authorized / King James Version has a special legal status in the United
Kingdom under the Royal prerogative and letters patent.

The UK government states that the right to print, publish, and distribute the
King James Bible is licensed by the Crown.

The National Archives describes the King James Bible as subject to perpetual
protection in the United Kingdom under the Royal prerogative.

Cambridge University Press administers Authorized Version rights under its
role as the King's Printer / Crown patentee for relevant UK territory.

This does not mean people in England are prohibited from reading or personally
using the GD Bible.

For intentional public distribution of the complete GD Bible in the United
Kingdom, including a full downloadable or published edition, the project
should obtain written permission or confirmation from the appropriate UK
rights administrator before claiming unrestricted UK distribution rights.

This UK-specific issue does not alter the public-domain status of the KJV
outside the United Kingdom.

## eBible KJV USFM

Source identifier used during the 2026-10 words-of-Jesus investigation:

- eBible KJV USFM
- eBible identifier: eng-kjv

The package is identified by eBible as public domain.

The USFM contains:

- KJV Bible text
- Strong's-number attributes
- words-of-Jesus \wj ... \wj* markup
- other USFM structural markup

The GD project is evaluating the eBible words-of-Jesus markup as the
deterministic baseline for Royal Purple speech spans.

The project should preserve source identification and the exact downloaded
source/version information used to regenerate derived assets.

## Words of Jesus / Royal Purple

Historical GD red-letter data originated from an older GrowDaily
logic/redLetters.js verse-reference list.

The historical list contained verse references, not authoritative word-level
speech spans.

The previous generator attempted to infer exact speech boundaries
heuristically.

Real-device review exposed incorrect boundaries, including John 1:38 and
John 1:42.

The heuristic method is therefore not considered sufficient provenance for
final words-of-Jesus spans.

During the 2026-10 investigation, eBible KJV USFM was found to contain balanced
explicit \wj speech markers:

- 2,038 opening markers
- 2,038 closing markers
- 2,028 verses containing \wj markup
- marker balance verified

The final GD Royal Purple map is not yet considered complete because
remaining editorial disagreements and exceptions are still under review.

The intended final architecture is deterministic exact source spans plus
explicitly reviewed GD exceptions, not inferred speech boundaries.

## Strong's dictionaries

The historical Strong's dictionary was published in the nineteenth century
and the underlying dictionary text is public domain.

The project also uses digital Strong's resources derived from Open Scriptures
materials.

Open Scriptures files are not all governed by one identical file-level
license.

Depending on the source file, Open Scriptures materials may identify:

- public-domain underlying Strong's dictionary text
- CC BY
- CC-BY-SA
- GPL-licensed digital conversions or enhancements

The project must preserve the applicable attribution and license information
for the exact digital source files that are redistributed.

Free/open licensing does not imply a payment obligation to LionGateOS.

## Strong's word-alignment provenance

The authoritative Schema 2.0 inline Strong's alignment now uses a pinned
two-source chain.

Primary source:

- eBible `eng-kjv` USFM
- 31,099 Strong's-bearing verses
- 348,884 mapped Strong's markers

Residual source:

- pinned CrossWire KJV
- Mark 9:43
- Luke 6:41
- Luke 17:36
- 66 mapped Strong's markers

Verified standard production result:

- 31,102 aligned verses
- 0 fallbacks
- 348,950 Strong's markers
- 0 reconstruction failures

Verified GD+ projection result:

- 31,102 projected verses
- 0 fallbacks
- 348,902 retained Strong's markers
- 48 markers intentionally not transferred across changed or ambiguous
  GD wording
- 0 reconstruction failures

The historical `kaiserlik/kjv` source is no longer required by the active
Schema 2.0 inline alignment.

Kaiserlik-derived legacy assets may remain for historical compatibility or
audit purposes, but they are not the provenance source for the current
GD+ inline alignment.

The eBible KJV package identifies its KJV text as public domain outside the
special UK Authorized Version regime. That statement alone does not
independently establish the legal provenance of every embedded Strong's tag.

For the three CrossWire fallback verses, the project preserves both
CrossWire's `DistributionLicense=GPL` metadata and its broad KJV2003
public-use statement. No final legal interpretation of their interaction
is asserted here.

Exact source identities, checksums, and fallback scope are recorded in the
eBible and CrossWire provenance manifests.

## GD custom Bible wording

The GD custom wording consists of documented editorial revisions layered on
the KJV base.

LionGateOS may transfer the rights it owns in those original revisions and
their associated documentation.

The underlying public-domain KJV words remain public domain outside the
special UK Authorized Version regime.

A transfer of GD project ownership does not create ownership over
public-domain KJV material itself.

## GD and GD+ e-Sword modules

Generated e-Sword packages are derived build artifacts.

Current planned public editions are exactly:

1. GD
   Grow Daily - Custom King James Version
   Royal Purple words of Jesus
   No Strong's numbers

2. GD+
   Grow Daily - Custom King James Version with Strong's Numbers
   Royal Purple words of Jesus
   Strong's numbers integrated

Generated modules should only be labeled final after:

- canonical Bible text validation passes
- Royal Purple speech-map validation passes
- Strong's validation passes where applicable
- applicable source rights and attribution records are current
- temporary test editions have been excluded
- UK distribution wording has been reviewed


## Audit rule

For every material source used in a final GD or GD+ release, preserve:

- source name
- source version or commit where available
- acquisition date where relevant
- applicable license or public-domain statement
- required attribution
- generated asset(s) derived from it
- validation performed
- known exceptions or unresolved questions

Do not silently replace a source without updating this record.

## Current unresolved rights/provenance items

1. Clarify or document the independent provenance/licensing basis of the
   embedded eBible Strong's annotation layer.
2. Preserve and review CrossWire's GPL and KJV2003 public-use metadata.
3. Record exact attribution/license requirements for bundled Open Scriptures
   dictionary files.
4. Confirm no final-release inline Strong's UI path depends on legacy
   Kaiserlik-derived mappings.
5. Obtain UK distribution permission or written clarification before claiming
   unrestricted complete GD/GD+ distribution in the United Kingdom.
6. Complete the deterministic reviewed Royal Purple source-span migration.
