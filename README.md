# LionGateOS Bible Editions

This repository contains Bible text, Strong's study data, words-of-Jesus
highlighting, documented LionGateOS KJV revisions, validation records, and
tools used to build the editions.

The documentation is written so that a reader does not need to understand the
source code or search through the repository to determine what is included.

## Quick facts

| Item | Verified total |
|---|---:|
| Bible books | 66 |
| Bible verses | 31,100 |
| Hebrew Strong's dictionary entries | 8,674 |
| Greek Strong's dictionary entries | 5,523 |
| Combined Strong's dictionary entries | 14,197 |
| Directly aligned Strong's verses | 26,926 |
| Safe fallback verses | 4,174 |
| Missing verses | 0 |
| Custom KJV text operations | 159 |
| Unique verses affected by custom revisions | 137 |
| Documented custom revision rules | 14 |

## The three editions

### 1. Enhanced Standard King James Version

The regular King James Version text with:

- Strong's numbers and dictionary information
- Hebrew and Greek study information
- Words spoken by Jesus displayed in royal purple
- No LionGateOS wording changes

### 2. LionGateOS Custom King James Version

The LionGateOS revised KJV with:

- The same Strong's study support
- Words spoken by Jesus displayed in royal purple
- 159 documented text operations
- 137 unique affected verses
- A record of every revision rule and its purpose

### 3. LionGateOS Custom KJV for e-Sword

A planned e-Sword-compatible edition generated from the LionGateOS Custom KJV.

The e-Sword package has not yet been built or validated. It will be kept
separate from the authoritative Bible source files.

## What Strong's material is included?

This repository includes digital Strong's-number study data, not a scanned or
typeset copy of the printed *Strong's Exhaustive Concordance*.

The bundled material contains:

- 8,674 Hebrew dictionary entries
- 5,523 Greek dictionary entries
- Strong's source mappings for the entire 66-book Bible
- Direct word-alignment data for 26,926 verses
- Safe plain-text fallback handling for 4,174 verses
- No missing canonical verses

A directly aligned verse has verified inline word-to-Strong's placement.

A fallback verse remains complete and readable, but the project does not claim
a reconstructed word-by-word inline alignment for that verse.

See [Strong's Data Explained](docs/STRONGS_DATA.md).

## What changed in the LionGateOS Custom KJV?

The custom edition contains 159 individual text operations in 137 unique
verses.

| Testament | Text operations | Unique verses |
|---|---:|---:|
| Old Testament | 28 | 16 |
| New Testament | 131 | 121 |
| **Total** | **159** | **137** |

The number 159 includes the main wording replacements and necessary companion
changes such as pronouns, articles, and capitalization.

Major wording revisions include:

| Standard KJV wording | LionGateOS wording | Total |
|---|---|---:|
| Holy Ghost | Holy Spirit | 90 |
| ghost | spirit | 14 |
| ghost | Spirit | 5 |
| adoption | sonship | 5 |
| scapegoat | Azazel | 4 |
| Easter | Passover | 1 |
| conversation | conduct | 20 |

Additional operations adjust nearby grammar or capitalization so the revised
phrases remain readable and grammatically correct.

See [Complete Custom KJV Change Summary](docs/CUSTOM_KJV_CHANGES.md).

## Words spoken by Jesus

The project contains separate words-of-Jesus maps for:

- the Enhanced Standard KJV
- the LionGateOS Custom KJV

The words are displayed in royal purple rather than traditional red.

Verified red-letter status:

- 2,055 intended references represented
- 2,054 mapped verse entries
- Two documented versification offsets
- Standard KJV reconstruction failures: 0
- Custom KJV reconstruction failures: 0
- Regression tests passed: 38 of 38

## Source separation

The repository keeps different kinds of material separate:

- `source/growdaily/` contains the imported, verified source checkpoint
- `editions/enhanced-kjv/` is reserved for generated Enhanced KJV releases
- `editions/liongateos-custom-kjv/` is reserved for generated Custom KJV releases
- `editions/esword/` is reserved for future e-Sword packages
- `docs/` contains plain-language and technical documentation

Generated release files must never replace the authoritative source files.

## Source checkpoint

The initial source was imported from the GrowDaily repository, branch
`kjv_custom`, at commit:

`9964d7fea44de71b0d56bb2891626e3f8158ce68`

Repository initial commit:

`947d029`

Checksums are recorded in
[Source Checksums](docs/SOURCE_CHECKSUMS.md).

## Current status

Available now:

- Standard KJV source
- LionGateOS Custom KJV source
- Hebrew and Greek Strong's dictionaries
- Whole-Bible Strong's mappings
- Direct and fallback alignment data
- Standard and custom words-of-Jesus maps
- Revision manifests
- Validation scripts and records

Not yet released:

- Downloadable packaged Bible editions
- e-Sword-compatible module
- Public version tag and release archive
