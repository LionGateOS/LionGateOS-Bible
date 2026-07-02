# Strong's Data Explained

## Plain-language answer

The repository includes Strong's-number dictionary and Bible-alignment data for
the complete 66-book Bible.

It is not a digital reproduction of every page, index, and feature in the
printed *Strong's Exhaustive Concordance*.

## Included dictionary data

| Dictionary | Entries |
|---|---:|
| Hebrew | 8,674 |
| Greek | 5,523 |
| **Combined** | **14,197** |

The dictionary records provide information such as:

- Strong's number
- original Hebrew or Greek form
- transliteration
- short meaning or gloss
- KJV-related definition fields where available

## Bible coverage

| Coverage item | Total |
|---|---:|
| Books | 66 |
| Canonical verses | 31,100 |
| Raw source records | 76,774 |
| Unique source references | 31,102 |
| Malformed references | 0 |
| Directly aligned verses | 26,926 |
| Fallback verses | 4,174 |
| Missing verses | 0 |

The two additional unique source references are handled by the project's
canonical verse reconciliation process. The final Bible contains the expected
31,100 canonical verses.

## What directly aligned means

A directly aligned verse has verified placement connecting the visible KJV
word sequence to the corresponding Strong's-number sequence.

These verses can support inline Strong's display with confidence in the
reconstructed word placement.

## What fallback means

A fallback verse is not missing.

The full Bible verse remains available and readable, but the project does not
claim a verified reconstructed word-by-word inline placement for that verse.

This prevents uncertain alignments from being shown as though they were exact.

## Standard and custom KJV support

The direct alignment was built from the Standard KJV source.

The LionGateOS Custom KJV uses a compatibility projection so documented wording
changes can retain Strong's support where the token structure remains safely
reconstructable.

Verified custom projection status:

- Custom projections: 26,926
- Custom projection fallbacks: 0
- Reconstruction failures: 0

## Data files

- `source/growdaily/assets/strong/strong_dict_hebrew.json`
- `source/growdaily/assets/strong/strong_dict_greek.json`
- `source/growdaily/assets/strong/strong_kjv.json`
- `source/growdaily/assets/strong/alignment/manifest.json`
- `source/growdaily/assets/strong/alignment/`

## Attribution and licensing

The bundled dictionary material is derived from Open Scriptures Strong's
sources.

The repository's imported source note records the Hebrew material as derived
from XML with Open Scriptures attribution and the Greek material with Open
Scriptures attribution.

See:

`source/growdaily/docs/bible/STRONGS_LICENSE_NOTE.md`

Licensing and attribution must be rechecked before changing data sources or
publishing a packaged public release.
