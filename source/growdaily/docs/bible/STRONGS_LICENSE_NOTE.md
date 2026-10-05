# Strong's Data Source Note

Audit updated: 2026-10-04

## Current Schema 2.0 inline alignment

The authoritative inline Strong's alignment uses two pinned sources:

1. eBible.org `eng-kjv` USFM
   - 31,099 Strong's-bearing canonical verses
   - 348,884 mapped Strong's markers

2. CrossWire Bible Society KJV
   - pinned commit:
     `d490be7e34762deb2c76cb2c1306d4808e27890d`
   - used only for Mark 9:43, Luke 6:41, and Luke 17:36
   - 66 mapped Strong's markers

Verified standard production alignment:

- 31,102 aligned verses
- 0 fallbacks
- 348,950 Strong's markers
- 0 reconstruction failures

Verified GD+ custom projection:

- 31,102 projected verses
- 0 fallbacks
- 348,902 retained Strong's markers
- 48 markers deliberately not transferred across changed or ambiguous GD wording
- 0 reconstruction failures

Canonical GD/KJV wording remains authoritative. Strong's source wording is
not allowed to replace displayed Scripture text.

## Historical Kaiserlik mapping

`assets/strong/strong_kjv.json` was historically generated from
`https://github.com/kaiserlik/kjv`.

No sufficiently clear redistribution license was established for that
repository during the provenance review.

The Kaiserlik-derived mapping is therefore legacy/historical data and is not
the upstream source for the active Schema 2.0 inline alignment.

## Strong's dictionaries

The bundled Hebrew and Greek dictionary resources are derived from Open
Scriptures materials.

Recorded source information includes CC-BY-SA and other file-level licensing
terms. The underlying nineteenth-century Strong's dictionary content is
public domain, but digital conversions and enhancements may have separate
attribution or redistribution requirements.

Those exact requirements must remain preserved for redistributed dictionary
data.

## Alignment-source rights status

The eBible KJV package identifies its KJV text as public domain outside the
special UK Authorized Version rights regime.

That statement alone does not independently prove the creation or licensing
history of every embedded Strong's annotation. This remains an explicit
release-rights audit item.

CrossWire `kjv.conf` records both:

- `DistributionLicense=GPL`
- a broad public-use statement for its KJV2003 Project text

Both statements are preserved. This project does not assert a final legal
interpretation of their interaction.

Exact CrossWire source identity, checksums, and three-verse scope are pinned
in:

`CROSSWIRE_KJV_STRONGS_FALLBACK_MANIFEST.json`

## Current safety rule

True inline Strong's placement may use the verified Schema 2.0 alignment.

The runtime must not silently substitute positional Kaiserlik-derived data
when Schema 2.0 alignment is unavailable.

Changed GD wording receives a Strong's ID only when the conservative
projection can transfer it without guessing.

## Remaining release audit items

- clarify or document independent rights provenance for the eBible Strong's
  annotation layer
- preserve and review CrossWire's recorded GPL/public-use metadata
- verify exact Open Scriptures dictionary attribution/license obligations
- confirm no final-release inline UI path depends on legacy Kaiserlik data
- complete deterministic Royal Purple source-span migration separately
