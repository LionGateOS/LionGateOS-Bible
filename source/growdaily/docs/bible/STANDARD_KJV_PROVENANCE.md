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

The King James Version text is in the public domain worldwide. The thiagobodruk transcription is also freely available. No copyright restriction applies to the text itself.

## Checksums

| File | SHA-256 |
|---|---|
| `en_kjv.json` (repaired standard) | `aa93816e3ca6a47deae0de21b4212527384cf143c0588032c199b817ab5adeec` |
| `en_kjv.json.before-clean` (pre-cleaning backup) | `47463eb68296f9a0e487d7b5c56f6fecdeadc0ddeb64db18fea3b31ca286cd99` |
| `kjv_modified.json` (custom) | `a38066ee769d4224ec51db78a1b9ba370df9a2e232ab6757f89d86def22454ba` |
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
- 31,100 verses
- No remaining braces or guillemets in any verse
- Genesis 1:12 restored with authentic wording: "And the earth brought forth grass, and herb yielding seed after his kind, and the tree yielding fruit, whose seed was in itself, after his kind: and God saw that it was good."
- No LionGateOS substitutions in the standard asset (verified by `standardKjvAuthenticity.test.js`)
- Deterministic regeneration from the preserved pre-clean backup (running `repair_en_kjv.py` produces the same checksum)
- Strong's Phase 1 production asset (`strong_kjv.json`) covers 31,090 of 31,100 verses with 355,011 word-index → Strong's ID mappings
- Strong's Phase 2 alignment (regenerated against repaired text) confirms 23,442 exact matches with the kaiserlik/kjv source

## NOT FULLY PROVEN

The following are known uncertainties:

- Universal agreement with every KJV transcription or edition is NOT proven. The independent jburson source has 2,330 wording differences, 5,540 capitalization differences, and 576 punctuation differences from the repaired en_kjv.json.
- Resolution of all 2,330 wording differences against jburson is NOT proven. These represent different KJV transcription traditions (spelling variants, proper name variants, hyphenation conventions).
- Resolution of all 266 non-LORD capitalization differences is NOT proven. These have not been individually audited.
- Exact agreement with a third independent same-edition source is NOT proven. Only two sources have been compared.
- The jburson source under `tmp/` is NOT durable provenance — it is a secondary comparison point only.

## Full-Bible Comparison Results (31,100 verses)

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

### Structural Differences

The jburson source has 31,102 verses vs en_kjv's 31,100 due to different verse-numbering conventions.

## Strong's Architecture

### Phase 1 (Production, Tracked)

- Asset: `assets/strong/strong_kjv.json`
- Runtime: `logic/strongIndex.ts` → `require("../assets/strong/strong_kjv.json")` (Metro-bundled)
- Consumer: `screens/BibleScreen.js` → `import { lookupStrongs } from "../logic/strongIndex"`
- Coverage: 31,090 of 31,100 verses (99.97%), 355,011 word-index → Strong's ID mappings
- The 10 missing verses have no Strong's markers in the kaiserlik source
- NOT stale: maps kaiserlik source word positions, independent of display text

### Phase 2 (Experimental, /tmp only)

- Preview: `/tmp/growdaily-strongs-alignment-preview.json`
- Assets: `/tmp/growdaily-strongs-alignment-assets/`
- Runtime: `logic/strongsAlignmentLoader.js` (reads from `/tmp`, NOT used by BibleScreen)
- Regenerated against repaired custom KJV: 23,442 exact matches, 7,655 text-mismatch fallbacks, 3 missing-in-source fallbacks, 0 reconstruction failures

### Positional Validity Across Both Translations

The Phase 1 Strong's data (`strong_kjv.json`) maps word-index positions from the kaiserlik source text to Strong's IDs. This data is valid for both the Standard KJV and the LionGateOS Custom King James Version because:

1. Both translations have identical per-verse canonical token counts (790,539 tokens each)
2. The word-index in `strong_kjv.json` corresponds to the order of Strong's markers in the kaiserlik source, not to display-text word positions
3. The `lookupStrongs()` function returns Strong's entries in source order, not aligned to specific display words
4. The Phase 2 alignment (when available) provides word-boundary data for exact display alignment, but the Phase 1 system works at the verse level without requiring word-by-word alignment
5. Custom substitutions (e.g., Ghost→Spirit, scapegoat→Azazel) change visible words but preserve token count and position, so Strong's IDs remain valid

## Retrieval Date

The pre-cleaning backup file (`en_kjv.json.before-clean-20260607-211743`) was created on 2026-06-07. The repair was performed on 2026-06-21.
