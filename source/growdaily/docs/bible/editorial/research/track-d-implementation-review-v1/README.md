# Implementation Review Master — v1

**Package:** GD Bible correction audit → implementation review package (batch 2026-10-19)
**Source master:** `UPSTREAM_TRACK_D_ROOT/combined-correction-master-v1/combined-correction-candidates.jsonl` (657 findings, SHA-256 `000f92795bc8e134c1dfd464a1e42d7369e2a87199361504f60fd2263e170db6`)
**Delivered at (read-only filesystem notice):** this package was generated in the writable
session workspace at `PACKAGE_BUILD_ROOT/`
because the specified target directory under
`UPSTREAM_TRACK_D_ROOT/combined-correction-master-v1/implementation-review-master-v1/`
is on a filesystem currently mounted **read-only** (root on `/dev/nvme0n1p4` is `ro`;
only the workspace bind is `rw`). Copy it into place with:

```bash
cp -r PACKAGE_BUILD_ROOT \
      UPSTREAM_TRACK_D_ROOT/combined-correction-master-v1/
# then re-verify: every artifact's recorded SHA-256 must still match after the copy
```

---

## 1. Purpose

This package turns the completed GD Bible correction audit into a reviewable implementation
package. It preserves **all 657 findings** from the combined correction master with their exact
source evidence, applies the owner's correction policy, and separates what qualifies for
implementation consideration from what needs human approval or further review.

Nothing here implements a correction. Nothing here proves doctrine. The canonical GD Bible
text, the original source master, the source archive documents, and the CASE project were **not
modified** by this batch (verification in `validation.json`).

## 2. Correction policy (owner-approved)

### Herbert W. Armstrong and Gerald Flurry

- **One verified source is enough to qualify a correction for consideration** for implementation.
  Three or more independent sources are *preferred*, never required.
- A **single-source correction is never rejected** or merged away; it is preserved with its
  exact citation. Single-source groups are labelled `single_source: true` with an explicit
  caveat.
- Distinct source **documents** are counted separately from repeated findings in the same
  document (`distinct_source_document_count` vs `member_count`).
- The two men are **not required to have made the same correction**; each qualifying HWA or GF
  source stands on its own (`author_profile` records which profile applies).
- Grouping uses the existing strict rules (exact case-sensitive wording after Unicode NFC and
  whitespace normalization; canonical verse set and correction type must match). Corrections
  that differ in wording or verse mapping are **not merged**; near-duplicate groups retain
  `potential_duplicate_group: true` and require human review.

### Other authors, ministers, and secondary sources

- Their statements are preserved as **potential future updates** with an explicit
  human-approval requirement (`potential-future-updates.jsonl`). They are never silently
  treated as corrections by Armstrong or Flurry.
- Three attribution kinds are distinguished everywhere:
  `direct_authorial` (speaker's own statement), `direct_quote_of_author` (the quoted words of
  Armstrong or Flurry themselves), and `secondary_or_editorial` (the correction attributed to
  another person quoted in the document).

### Evidence and uncertainty

Every retained candidate carries: source citation, exact archive-relative document path,
SHA-256, quotation, author/speaker attribution, original wording, proposed wording, and verse
reference(s).

- A verified SHA-256 proves **file integrity only**. It does **not** prove that a theological
  or translation claim is correct; those judgments remain separate human decisions.
- Uncertain attribution, ambiguous references, chapter-only references, missing wording, and
  invalid/incomplete verse mappings are retained in `held-for-review.jsonl` with full evidence.
- **Public source URLs:** a URL is included only when an exact URL is already available and
  verified in the existing evidence. The existing evidence contains **no URL fields**
  (checked across the master and the archive metadata inventory), so **no links are recorded**
  and **none were invented**. Every such candidate is listed in `needs-public-source-link.jsonl`.
- Candidates are produced **for consideration** (`status: implementation_candidate`,
  `implementation_requires_owner_review: true`); final implementation still requires owner review.

## 3. Files

| File | Contents |
|---|---|
| `correction-master.jsonl` | Complete, traceable inventory of **all 657 findings** with per-finding `review_status` (`implementation_candidate` / `potential_future_update` / `held_for_review`), group association, attribution details, reference-normalization dispositions, source integrity recheck, and pointers back to the upstream master line. |
| `unique-correction-groups.jsonl` | All **440 unique correction groups** (strict grouping rules), each with full member source records, distinct-source counts, duplicate flags, and aggregate review status. |
| `implementation-candidates.jsonl` | **431 group-level candidates** qualifying under the Armstrong/Flurry attribution + evidence criteria, **including 409 single-source candidates**. Each lists qualified members (full evidence), any non-qualifying members in the same group, and human-review flags. |
| `potential-future-updates.jsonl` | **7 proposals** whose statements are secondary/editorial (attributed to another person quoted by the author). Requires explicit owner approval. |
| `held-for-review.jsonl` | **163 findings**: the 159 baseline holds (missing wording 96; reference requires review 32; no reference evidence 31) plus 4 findings held because verification flagged their verse mapping incorrect. Evidence never dropped. |
| `source-evidence-index.jsonl` | **373 distinct archive documents** with exact paths, SHA-256, fresh re-hashing results, findings referencing them, and link availability. |
| `needs-public-source-link.jsonl` | All candidates (implementation + future updates) lacking a verified public URL. |
| `summary.json` | Counts, dispositions, source coverage, provenance chain, and SHA-256 of every generated artifact. |
| `validation.json` | Machine-checkable validation results (all checks, pass/fail recorded). |
| `README.md` | This file. |

## 4. Review process

1. **Implementation queue** — `implementation-candidates.jsonl` (431 unique corrections; 487
   qualifying findings behind them). Owner selects what to adopt, per correction and per verse.
2. **Human-required flags** — candidates marked `human_review_required: true` (potential
   duplicate wording groups, plausible-but-not-fully-verified verse mapping, or groups carrying
   non-qualifying member evidence) need a look before adoption even though they qualify.
3. **Potential future updates** — needs explicit owner approval before any secondary/editorial
   statement can be attributed as an Armstrong/Flurry correction.
4. **Held-for-review** — resolve the stated `hold_reason` per finding; evidence is preserved
   for each so a hold can be cleared without re-research.
5. **Public links** — attach verified URLs from `needs-public-source-link.jsonl` or deliberately
   publish without links.
6. **Publishing** — this closeout checkout's `origin` is `Church-Archive-Search`
   (`LionGateOS/Church-Archive-Search`); publishing this GD Bible package requires the owner to
   confirm the correct target repository first. **No commit was made** in this batch.

## 5. Provenance chain

Inputs (all SHA-256-verified at build time — see `summary.json` → `inputs`):

1. `combined-correction-candidates.jsonl` — original 657-finding master.
2. `reference-normalization-audit-v1` — 30 references audited (22 normalized, 6 ambiguous, 2 chapter-only).
3. `correction-grouping-audit-v2` — 657 → 498 eligible / 159 held; 440 unique group signatures; 39 potential duplicate groups. Baseline self-hash note: `correction-grouping-audit-v2/summary.json`'s recorded self-hash cannot match the file (a file cannot contain its own hash); the audit's data files themselves hash-verify correctly and were re-verified here.
4. `author-attribution-correction-v1` — 3 owner-confirmed author-attribution fixes (HWA → Gerald Flurry, "time no longer" → "no more delay"); corrected master and corrected groups re-verified.

Derived master used: `author-attribution-correction-v1/combined-correction-candidates-attribution-corrected.jsonl` (SHA-256 `814f74b036c4fa4df7158135ef74be810feaab9b71738f7718c9892a2013591f`). Original raw attribution (`speaker_raw`) is preserved in every record where it applies.

## 6. Verification performed

- All **657** source documents re-hashed against the preserved originals under
  `ARCHIVE_ROOT/documents/` — **657/657 match**, none missing.
- All upstream artifacts from the master summary, all three audit sub-reports, and the canonical
  Bible file (`en_kjv.json`, SHA-256 base as pinned in `gd_canonical_coordinates.json`)
  re-verified byte-for-byte.
- Reconciliation: 657 = 487 implementation findings + 7 future updates + 163 held; 498 + 159
  baseline preserved; 498 eligible findings ↔ 440 group members (exact set equality); 440 = 431
  implementation groups + 9 non-implementing groups.

See `validation.json` for the machine-readable checklist and `summary.json` for artifact hashes.

## 7. Limitations (stated plainly)

- **No doctrine is proven by this package.** Source verification = document integrity only.
- Implementation candidates are **consideration-ready**, not approved-for-publication.
- Verse mappings marked `plausible` (not fully verified) remain flagged inside candidates.
- Public URLs: none available; none fabricated. `needs-public-source-link.jsonl` must be
  resolved (add links or accept no links) before any publication step.
- The output location had to be the writable workspace because the normal master path was
  read-only at batch time (see top of this README).
- The `summary.json`/`validation.json` self-hash situation is documented: a file cannot
  contain its own hash; `validation.json` records `summary.json`'s hash, and any external
  verifier can recompute all hashes from the manifest inside `summary.json`.
## Publication-copy integrity note

This repository copy replaces private absolute filesystem roots with
descriptive path labels. Archive-relative source document paths and
source evidence are preserved.

The original batch passed 42/42 checks before sanitization.
`original-batch-validation.json` records that historical result; its
original artifact hashes do not validate this sanitized copy.

`summary.json` contains refreshed hashes for its listed artifacts.
`publication-integrity.json` independently records hashes for every
file in this publication copy. The upstream source archive is not
included, so its contents have not been re-audited by this import.

No Bible text or upstream source document was modified.
Correction candidates still require owner review before implementation.
