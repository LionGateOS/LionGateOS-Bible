# GrowDaily Canonical Standard KJV Provenance

## Source Identity

| Field | Value |
|---|---|
| Source title | King James Version (1769 Oxford/Blayney edition) |
| Transcription | thiagobodruk dataset |
| Documented in | `data/scriptureMemory.js:12` as "thiagobodruk 1769 KJV" |
| Pre-cleaning backup | `assets/bible/en_kjv.json.before-clean-20260607-211743` |
| Repaired standard asset | `assets/bible/en_kjv.json` |
| Repair script | `scripts/bible/repair_en_kjv.py` |

## Edition Claim

GrowDaily pins one documented 1769 KJV transcription: the thiagobodruk 1769 Oxford/Blayney edition. This is the most widely used KJV edition and is the basis for most modern KJV printings. This document does NOT claim that every available KJV dataset is identical.

## Licensing / Public-Domain Information

Outside the United Kingdom, the underlying KJV source text used by this
project is treated as public domain.

The Authorized / King James Version has a special continuing rights regime
in the United Kingdom. The project has submitted a preliminary permissions
inquiry to Cambridge University Press & Assessment and does not claim
unrestricted UK distribution rights while that inquiry remains unresolved.

This section addresses the underlying KJV text only. Strong's annotations,
dictionaries, software, and other third-party data have separate provenance
and license records.

## Checksums

| File | SHA-256 |
|---|---|
| `en_kjv.json` (repaired standard) | `4109ee74d422614995325b5d2f43da9ec35d9be547d6a11bc68fb0978179585f` |
| `en_kjv.json.before-clean` (pre-cleaning backup) | `47463eb68296f9a0e487d7b5c56f6fecdeadc0ddeb64db18fea3b31ca286cd99` |
| `kjv_modified.json` (custom) | `f2e29b70e61fb1345d80721905caf9f59049f5265ad1c28bd2f9e2d82fedbb4c` |
| `strong_kjv.json` (Phase 1 Strong's) | `dcc057b771f73e4ca6690d526cab07f256dfb5971b6a5d3c48cad042f5c4534a` |

## Deterministic Regeneration

The repaired `en_kjv.json` is deterministically regenerated from the preserved pre-clean backup by `scripts/bible/repair_en_kjv.py`. The repair applies:

1. **Italicized translator-added words** (braces like `{and}`, `{was}`, `{it was}`): UNWRAPPED — braces removed, text preserved
2. **Publisher editorial notes** (braces with colons, like `{grass: Heb. tender grass}`): REMOVED — braces and content deleted
3. **Guillemet blocks** (`«...»` with epistle attributions): REMOVED
4. **Stray braces** (leftover `{` or `}` after processing): REMOVED
5. **Multiple spaces**: Collapsed to single space
6. **Space before punctuation**: Fixed (e.g., `word ,` → `word,`)

No LionGateOS custom substitutions are applied to this asset.

## PROVEN

The following are proven with direct evidence:

- Exact source file lineage: `en_kjv.json.before-clean-20260607-211743` → `repair_en_kjv.py` → `en_kjv.json`
- Repaired brace-handling process: 17,366 verses with braces processed (italicized words unwrapped, editorial notes removed)
- Source and repaired checksums (see above)
- 66 books
- 1,189 chapters
- 31,102 verses
- No remaining braces or guillemets in any verse
- Genesis 1:12 restored with authentic wording: "And the earth brought forth grass, and herb yielding seed after his kind, and the tree yielding fruit, whose seed was in itself, after his kind: and God saw that it was good."
- No LionGateOS substitutions in the standard asset (verified by `standardKjvAuthenticity.test.js`)
- Deterministic regeneration from the preserved pre-clean backup (running `repair_en_kjv.py` produces the same checksum)
- Historical Phase 1 `strong_kjv.json` remains preserved as a legacy Kaiserlik-derived asset
- Current Schema 2.0 production alignment covers all 31,102 canonical verses with 348,950 Strong's markers and 0 fallbacks
- Current GD+ projection covers all 31,102 verses with 348,902 retained Strong's markers and 0 projection fallbacks

## NOT FULLY PROVEN

The following are known uncertainties:

- Universal agreement with every KJV transcription or edition is NOT proven. The independent jburson source has 2,330 wording differences, 5,540 capitalization differences, and 576 punctuation differences from the repaired en_kjv.json.
- Resolution of all 2,330 wording differences against jburson is NOT proven. These represent different KJV transcription traditions (spelling variants, proper name variants, hyphenation conventions).
- Resolution of all 266 non-LORD capitalization differences is NOT proven. These have not been individually audited.
- Exact agreement with a third independent same-edition source is NOT proven. Only two sources have been compared.
- The jburson source under `tmp/` is NOT durable provenance — it is a secondary comparison point only.

## Historical Pre-Structural-Repair Comparison Results (31,100-verse snapshot)

Comparison of repaired `en_kjv.json` against independent `jburson-kjv.json`:

| Metric | Count |
|---|---|
| Identical verses | 22,650 |
| Capitalization-only differences | 5,540 |
| Punctuation-only differences | 576 |
| Wording differences | 2,330 |
| Verses in en_kjv missing from jburson | 4 |
| Verses in jburson missing from en_kjv | 6 |
| Reference mismatches | 0 |
| Total matched verses | 31,096 |

### Capitalization Differences (5,540)

- 5,274 are `LORD` vs `Lord` — the en_kjv uses `LORD` (all caps for the tetragrammaton, 1769 Oxford/Blayney convention), the jburson source uses `Lord` (title case). This is an edition formatting convention difference.
- 266 are other capitalization differences (not individually audited).

### Wording Differences (2,330)

These include spelling variants, proper name variants, hyphenation differences, minor word substitutions, and 326 verses with token-count differences due to different verse splitting.

### Structural Differences — corrected 2026-10-04

The earlier 31,100-verse `en_kjv.json` was not merely an alternate verse-numbering convention. Structural reconciliation found six omitted canonical verse boundaries and four erroneous extra split boundaries. The canonical asset has been repaired to 31,102 verses. The comparison table above is retained as historical evidence from the pre-repair 31,100-verse snapshot and has not been presented as a recomputation of the current asset.

## Strong's Architecture

### Legacy Phase 1 asset

The repository still contains the historical
`assets/strong/strong_kjv.json` mapping generated from `kaiserlik/kjv`.

It is retained as legacy/historical data and may still be referenced by
older lookup code. It is not the authoritative source for the active
Schema 2.0 inline GD+ alignment.

### Schema 2.0 inline alignment — current production

Current production assets:

- `assets/strong/alignment/manifest.json`
- 66 per-book alignment files
- runtime loader: `logic/inlineStrongsLoader.js`
- GD projection: `logic/customKjvInlineStrongs.js`

Verified standard production totals:

- canonical verses: 31,102
- aligned verses: 31,102
- plain fallbacks: 0
- Strong's markers: 348,950
- missing verses: 0
- reconstruction failures: 0

Current source chain:

- eBible `eng-kjv` USFM:
  31,099 Strong's-bearing verses / 348,884 markers
- pinned CrossWire KJV fallback:
  Mark 9:43, Luke 6:41, Luke 17:36 / 66 markers

The active Schema 2.0 alignment therefore no longer requires Kaiserlik.

### GD+ custom projection

Canonical GD wording remains authoritative.

For changed GD verses, Strong's IDs transfer only through conservative,
deterministic matching. Changed or ambiguous wording is left unnumbered
rather than guessed.

Verified GD+ totals:

- projected verses: 31,102
- projection fallbacks: 0
- changed GD verses: 335
- changed verses projected: 335
- retained Strong's markers: 348,902
- source markers conservatively not transferred: 48
- reconstruction failures: 0

## Retrieval Date

The pre-cleaning backup file (`en_kjv.json.before-clean-20260607-211743`) was created on 2026-06-07. The repair was performed on 2026-06-21.
