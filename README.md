<p align="center">
  <img src="assets/branding/liongateos-bible-logo.png" alt="GD Bible logo" width="320">
</p>

# GD Bible — Grow Daily

GD Bible is a documented custom King James Version Bible project maintained
under the project name **LionGateOS**.

The project preserves the complete 66-book Bible while maintaining a
traceable record of its editorial revisions, source material, Strong's study
data, words-of-Jesus formatting, generated editions, validation work, and
distribution formats.

The goal is that another reader, developer, publisher, or future steward can
understand exactly what GD contains, what was changed, why it was changed,
where its source material came from, and how the resulting editions were
validated.

> **Development status:** GD Bible is under active source, Strong's,
> words-of-Jesus, export, and rights validation. Development builds exist, but
> the final public release has not yet been declared complete.

## What does GD mean?

**GD** stands for **Grow Daily**.

The visible Bible edition name is intentionally short so that Bible software
and e-Sword can display a clear version abbreviation.

The two planned public editions are:

### GD

**Grow Daily - Custom King James Version**

GD contains:

- the complete 66-book custom KJV text
- 31,102 canonical verses
- documented GD wording revisions
- words spoken by Jesus displayed in **Royal Purple**
- no inline Strong's numbers

### GD+

**Grow Daily - Custom King James Version with Strong's Numbers**

GD+ contains:

- the same complete GD custom Bible text
- the same Jesus speech identification system
- Aqua words-of-Jesus rendering optimized for Strong's study
- integrated Hebrew and Greek Strong's numbers for study
- Strong's dictionary support where supported by the target Bible software

GD and GD+ use the same underlying GD Scripture text. Strong's study support
is the principal difference between the two editions.

## Quick facts

| Item | Current verified value |
|---|---:|
| Bible books | 66 |
| Canonical verses | 31,102 |
| Hebrew Strong's dictionary entries | 8,674 |
| Greek Strong's dictionary entries | 5,523 |
| Combined Strong's dictionary entries | 14,197 |
| Unique verses affected by documented GD revisions | 335 |
| Current documented text operations | 383 |
| Missing canonical verses | 0 |

Strong's alignment totals are intentionally not listed here while the
production alignment source is being migrated and exhaustively revalidated.
Final release totals will be published after that migration is complete.

## What changed in GD?

GD is not presented as an unchanged reproduction of the standard King James
Version.

The current revision audit records **383 individual text operations across
335 unique verses**.

| Testament | Text operations | Unique verses |
|---|---:|---:|
| Old Testament | 146 | 126 |
| New Testament | 237 | 209 |
| **Total** | **383** | **335** |

The operation count includes principal wording revisions together with
necessary companion changes such as articles, pronouns, grammar, and
capitalization.

Major documented wording revisions currently include:

| Standard KJV wording | GD wording | Total |
|---|---|---:|
| Holy Ghost | Holy Spirit | 90 |
| ghost | spirit | 14 |
| ghost | Spirit | 5 |
| adoption | sonship | 5 |
| scapegoat | Azazel | 4 |
| Easter | Passover | 1 |
| conversation | conduct | 20 |
| was | became | 1 |
| in his spirit | by his spirit | 1 |
| hate not | love less than | 1 |
| gentleness | kindness | 1 |
| longsuffering | patience and mercy | 1 |
| goodness | goodness and generosity | 1 |
| Meekness | Meekness and humility | 1 |
| temperance | self-control | 1 |
| prevent | precede | 7 |
| charity | love | 28 |
| devils | demons | 55 |
| corn | grain | 102 |
| unicorn | wild ox | 6 |
| careful | anxious | 4 |
| quick | living | 4 |
| carriages | baggage | 2 |
| peculiar | special | 4 |
| target | spear | 1 |

Additional operations adjust surrounding grammar or capitalization where
required.

See
[Complete Custom KJV Change Summary](docs/CUSTOM_KJV_CHANGES.md)
for the detailed revision record.

## Words spoken by Jesus — Royal Purple

GD uses **Royal Purple** rather than traditional red for words spoken by
Jesus.

The project contains separate standard-KJV and GD-custom words-of-Jesus
assets.

The earlier implementation successfully reconstructed the underlying verse
text, but later review identified cases where heuristic speech-boundary logic
could select the wrong speaker inside a verse.

Because of that discovery, the older words-of-Jesus count is **not treated as
a final editorial result**.

The production system is being replaced with a deterministic,
source-backed approach using explicit speech spans plus documented reviewed
exceptions.

Final Royal Purple totals will be published only after the replacement maps
have completed whole-Bible validation.

## Strong's study data

GD+ is designed to provide inline Strong's study numbers while preserving the
GD Scripture text exactly.

The project includes:

- 8,674 Hebrew dictionary entries
- 5,523 Greek dictionary entries
- 14,197 combined dictionary entries
- per-book inline alignment assets
- validation scripts
- generated GD+ projection data
- e-Sword-compatible Strong's markup

The Strong's production alignment source is currently being migrated to a
reproducible **eBible.org King James Version USFM source** containing embedded
Hebrew and Greek Strong's identifiers.

The migration is being performed conservatively:

1. the GD/KJV canonical text remains authoritative for displayed Scripture
2. Strong's identifiers are transferred only where the source word can be
   positively aligned
3. translator-added or unmatched words are never assigned invented Strong's
   identifiers
4. every generated verse must reconstruct the canonical displayed text
5. unresolved verses remain readable without pretending that an uncertain
   word-level alignment is known

The previous implementation and its history are being preserved for
traceability while the replacement is validated.

See [Strong's Data Explained](docs/STRONGS_DATA.md).

## e-Sword editions

Development builds currently include:

- `GD.bblx`
- `GD.bbli`
- `GD+.bblx`
- `GD+.bbli`

The intended e-Sword identities are:

| Abbreviation | Edition |
|---|---|
| GD | Grow Daily - Custom King James Version |
| GD+ | Grow Daily - Custom King James Version with Strong's Numbers |

### iPad — e-Sword HD

The tested installation method for a compatible `.bbli` development build is:

1. Save the `.bbli` file on the iPad.
2. Open it from Safari or the Files app.
3. Tap **Share**.
4. Choose **e-Sword**.
5. Open e-Sword HD.
6. Select the imported GD edition.

See
[e-Sword Mobile Install Guide](docs/ESWORD_MOBILE_INSTALL.md)
for additional details.

Only formats that have been tested in their target Bible application should
be considered supported.

## Source and provenance

The authoritative Bible source is maintained separately from generated
release files.

Important project areas include:

- `source/growdaily/assets/bible/` — canonical Standard and GD Bible text
- `source/growdaily/assets/red_letters/` — words-of-Jesus source and generated maps
- `source/growdaily/assets/strong/` — Strong's dictionaries and alignment assets
- `source/growdaily/scripts/` — generation, reconciliation, and validation tools
- `editions/esword/` — generated e-Sword development packages
- `docs/` — editorial, technical, provenance, rights, and release documentation

Generated release files must not silently replace the canonical Bible source.

The original GrowDaily Bible source checkpoint was imported from the
GrowDaily repository, branch `kjv_custom`, at commit:

`9964d7fea44de71b0d56bb2891626e3f8158ce68`

The initial standalone Bible repository commit is:

`947d029`

Checksums and provenance records are maintained in the repository so that
important source and generated artifacts can be reproduced and audited.

## Rights and distribution status

The King James Version source used by this project is treated as public
domain outside the United Kingdom according to its documented upstream
source information.

The Authorized Version has a special rights status within the United
Kingdom.

A preliminary permissions inquiry has been submitted to Cambridge University
Press & Assessment concerning distribution of the complete GD custom
KJV-derived edition in relevant UK territories.

Until that question is resolved, this repository does **not** claim that GD
has received UK distribution authorization.

The project is also auditing the provenance and applicable terms of every
non-GD component used in the finished editions, including Strong's source
data and other third-party material.

No organization should be understood to endorse, sponsor, own, or have
accepted stewardship of GD Bible merely because the project may be discussed
with them in the future.

## Project stewardship

GD Bible is currently maintained by its creator under the **LionGateOS**
project name.

LionGateOS is a project name and is not presented here as a registered
corporation or other separate legal entity.

Future ownership or stewardship arrangements, if any, will be documented
only after the relevant parties have actually agreed to them.

## Suggest a Bible change

Suggestions and corrections are welcome.

A useful proposal should include:

1. the Bible reference
2. the current GD wording
3. the suggested wording
4. the reason for the change
5. any supporting textual or source material

A suggestion does not automatically become part of GD. Changes are reviewed,
documented, validated, and preserved in project history before becoming
canonical.

## Current development priorities

Current work includes:

- completing the reproducible Strong's source migration
- replacing heuristic words-of-Jesus span generation
- validating GD and GD+ across the complete 31,102-verse canon
- maintaining source and rights provenance
- validating e-Sword desktop and iPad packages
- resolving UK distribution requirements
- updating documentation and release metadata
- preparing a clean, auditable public release

## Release principle

A GD Bible release should be reproducible from documented sources and should
include enough information to determine:

- what Scripture text it contains
- what editorial changes were made
- why those changes were made
- where study data came from
- how words-of-Jesus spans were determined
- what validations passed
- what rights or distribution conditions apply
- which files are authoritative and which are generated

The repository history is intentionally part of that record.
