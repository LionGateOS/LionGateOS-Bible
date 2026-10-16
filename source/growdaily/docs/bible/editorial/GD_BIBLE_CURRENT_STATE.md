# GD Bible — Current State (GD-Owned Record)

**Status:** Canonical current-state record for the Grow Daily Bible ("GD Bible") research program.
**Owner:** GD Bible workstream. Church Archive Search Engine is a separate project sharing this
repository and workspace; that project's identity is governed by `docs/CHURCH_ARCHIVE_SEARCH_ROADMAP.md`
and `docs/CURRENT_STATE.md`, which are **not** GD Bible's identity documents.
**Recorded:** 2026-10-13 (EDT), full HIGH research corpus closeout.
**Evidence basis:** every fact below was independently re-verified against repository and disk
artifacts at recording time (hashes recomputed, row counts and verdicts re-derived read-only).

---

## 1. Project identity

- **GD Bible** is the research program that extracts, verifies, and indexes research findings
  (quotes, topics, speakers, scripture attributions) from the downloaded church archive.
- **Repository:** `/home/liongateos/LionGateOS-Bible` — canonical home for all GD Bible
  research scripts, tooling, and documentation (recovered to this repository 2026-10-16;
  see §8).
- **Historical workspace:** GD Bible research scripts were previously developed inside the
  `pcog-archive-collector` worktree. That path now hosts CASE only. Read-only CASE data
  dependencies (archive databases, archive originals) remain in `pcog-archive-collector`
  and `/home/liongateos/PCOG-Research-Archive`.
- **Archive originals:** `/home/liongateos/PCOG-Research-Archive` (**21,469 preserved files**;
  originals are bytes-immutable for GD purposes).
- **Separate-project boundary:** The Church Archive Search Engine (CASE) owns
  search/navigation and archive collection concerns. GD Bible owns document extraction,
  research generation, evidence verification, and scripture normalization. Neither project
  writes the other's artifacts without explicit approval. Do not implement GD Bible work
  inside `pcog-archive-collector`.

## 2. GD-M06-A0.1 Identity Gate decision (approved 2026-10-11)

| Artifact | Role | SHA-256 | `research_findings` |
|---|---|---|---|
| `archive_research_sidecar.db` (workspace) | **Approved GD-M06-A operating baseline** — post-M12 | `f8c20ede53efdd71be00a71681e00a3f3141524ec1c1399561ebbd395e770d7c` | 19,340 (2,060 documents) |
| `/mnt/SanDisk-Backup/MASTER_BACKUPS/archive_research_sidecar_20261011_002538.db` | **Immutable pre-M12 recovery baseline** | `23a5723caa11e81735235c68d06547b3d58e9c8594db3e10903bf2cc955f2d1e` | 30,730 (2,377 documents) |
| `/home/liongateos/PCOG-Research-Archive/metadata/gd_bible_30730_findings_export.json` | Preserved recovery copy (content-identical to pre-M12 sidecar) | `305eb6475828dfde70def700c2b0543204de48e3090bae096b261a0194c70a5f` | 30,730 records |

Decision terms:
- 30,730 − 11,390 = 19,340. The **11,390 removed findings remain preserved and suspended**:
  they exist only in the pre-M12 artifacts; they are **not silently discarded** and are **not
  automatically restored**. Restoration and/or re-anchoring (~6,300 quotes still verbatim in the
  corrected text) is a **separate future milestone requiring explicit approval**
  (also barred by `docs/CHURCH_ARCHIVE_SEARCH_ROADMAP.md` §7.2 without separate approval).
- Anchor-verdict basis of the approved baseline (re-verified from `anchor_validity_manifest.json`):
  **18,626 valid / 602 mismatch / 112 out_of_bounds**; quarantine holds 714 findings across 56
  documents. The anchor gate must gate every consumer of evidence offsets (§5).

## 3. M12 evidence facts (summary — full record: `docs/M12_EVIDENCE_RECONCILIATION.md`)

- Commit `016115e` ("M12: Patch RTF extraction skip logic to suppress metadata leaks",
  2026-10-11 16:26:21 EDT) corrected the RTF extractor (`EXTRACTOR_VERSION` 1.0.0 → 1.1.0).
  Re-extraction changed text for **547 of 795** RTF-container documents.
- The sidecar was reconciled **in place** (sparse `rowid`s 1…30,327 vs contiguous pre-M12
  rowids prove deletion, not rebuild): **30,730 → 19,340; 11,390 findings removed across 317
  documents** (286 with genuinely shifted text; 31 over-deleted whose text never changed).
- This was an **intended evidence reconciliation**, not accidental loss. Execution was
  **imperfect in both directions** (358 still-valid findings over-deleted; 714 invalid-anchor
  findings retained) and was not pre-authorized in any committed record; it was later documented
  and independently re-verified in commit `70c60ec`'s predecessor `b3a47c8`
  (`docs/M12_EVIDENCE_RECONCILIATION.md` §5, §9).
- **Archive originals were not modified.** The M12 correction changed only the derived text
  layer (`archive_search.db` `document_text`) and the derived sidecar. `documents.char_count`
  in the primary DB is stale for 547 rows; anchor bounds must use `len(document_text.content)`.
- `archive_research_sidecar.db.m02_backup` is **byte-identical to the 19,340 live sidecar**
  (same SHA-256, mtime identical to the nanosecond): it is **not a rollback point** and
  restores nothing.
- No script, commit, or log records the pruning invocation; the mechanism is documented, the
  invocation is unrecoverable (`*.db`/`*.json` are gitignored).
- `scripture_refs` in the sidecar are **model-attributed, unverified** annotations
  (`docs/M12_EVIDENCE_RECONCILIATION.md` §7: 55.1% of ref entries do not textually appear in
  their own finding). They are a different evidentiary class from deterministic
  `gd_scripture_engine` extraction and must never be merged with it.

## 4. Current GD Bible technical workstreams (do not merge)

1. **Full HIGH research expansion — COMPLETE (2026-10-13).** The current full-archive HIGH
   target is **22,756 / 22,756 passages**, consisting of **16,788 fresh 2026 passages** plus
   **5,968 independently revalidated historical passages**. The verified combined candidate
   contains **58,498 verified findings** across **8,221 documents**, with no missing passage
   identities or duplicate selections. Full evidence: `docs/GD_FULL_HIGH_RESEARCH_CLOSEOUT_2026-10-13.md`.
   This does **not** replace or mutate the approved 19,340-row M12 sidecar baseline.
2. **GD-M06-A — Scripture Reference Normalization & Reference Assertion Baseline** (active;
   planning → baseline freeze). Normalize model-attributed scripture references
   deterministically, assert them against canonical text, and produce a reference layer with
   verbatim provenance. Architecture review and A0.1 Identity Gate are complete.
3. **GD-M02-C — Bounded Constrained Extraction Proof**: **planning only; not authorized for
   corpus-scale execution.** No repository document currently defines this label; scope is
   operator-designated and must be documented before authorization.
4. **Blocked:** scripture relationship graphs (Church Archive roadmap CASE-03 depends on a
   normalization/verification precursor) remain **blocked until GD-M06-A proves normalization
   plus reference assertion quality**. Roadmap CASE numbering is the Church Archive Search
   Engine's label space; GD-Mxx numbering is GD Bible's. Historical collision note:
   `audit_m06.py` uses "M06" for an older, unrelated audit (`docs/M12_EVIDENCE_RECONCILIATION.md` §9.1).

## 5. Standing safeguards

- Preserve archive originals unchanged: exact filenames, paths, bytes, provenance.
- Generated research (findings, quotes, topics, refs) is **derived and non-authoritative**,
  always traceable to source documents, and labelled as model observations in any UI.
- Preserve raw scripture references **verbatim**; normalize but **never silently repair**
  (repairs, if any, are separate annotations with their own provenance).
- **No production database writes** (`archive_search.db`, `archive_research_sidecar.db`)
  without explicit approval; the pre-M12 recovery artifacts in §2 must remain immutable.
- `scripture_refs` are **model-attributed/unverified** until GD-M06-A proves otherwise.
- The **anchor validity gate** (`gd_anchor_verifier.py` + `anchor_validity_manifest.json`,
  commit `b3a47c8`) is mandatory for any consumer of evidence offsets; the strict
  `gd_string_assertion.verify_evidence_span()` over-quarantines 639 valid findings without its
  normalization layer (M12 doc §4.1).
- Deterministic validation precedes AI interpretation, always.

## 6. Next action (as of 2026-10-13)

**GD-M06-A0.2 — Baseline Freeze**: capture frozen facts (artifact identity with file and
logical digests, population counts, the verbatim scripture-reference population of all 15,612
entries, the incumbent-engine baseline, and the known-defect fixture register) against the
**approved 19,340 operating baseline** — read-only, re-runnable against either candidate, with
digest specifications pinned before capture. Outputs require approval; no database is created
in A0.

---

## 7. Current Status Update (2026-10-15)

### 7.1 Historical Baseline Preserved

The 2026-10-13 record above remains the authoritative historical baseline. The following
sections advance the record through 2026-10-15.

### 7.2 Completed Milestones

| Milestone | Commit | Description |
|-----------|--------|-------------|
| Full HIGH research | `4e621a6` | Complete; 58,498 findings, 22,756 passages |
| Scripture normalization | `1a5ad16` | Repair GD scripture reference normalization and assertion |
| Deterministic revision mapping | `f8e50c3` | Add deterministic GD Bible revision mapping |
| Revision Review Packets V1 | `fea4ab7` | Add GD Bible revision review packets |

### 7.3 Current Active Phase

**Editorial Review V1 — proposition-specific and rule-family evidence audit**

This phase establishes a durable repository/GitHub-backed editorial evidence-review layer
for the GD Bible.

#### 7.3.1 Current Principle

**Existing transformation ≠ newly approved transformation**

Current presence in the GD Bible does NOT constitute approval under the new editorial
lifecycle. Each transformation must progress through the lifecycle explicitly.

#### 7.3.2 No Canonical Bible Edits

No canonical Bible text is edited during the current audit phase. This milestone documents
and audits existing transformations without modifying:
- `en_kjv.json`
- `kjv_modified.json`
- `TRANSFORMATION_MANIFEST.json`
- Production review packets
- Archive databases or archive originals
- Existing evidence bridge artifacts

### 7.4 Review Universe Summary

| Track | Description | Count |
|-------|-------------|-------|
| Track A | Existing GD-changed verses | 335 |
| Track B | Unchanged Tier-1 archive-evidence candidates | 316 |
| Track C | Owner candidates | 10 |
| Track C overlap with Track B | — | 4 |
| Track C owner-only | — | 6 |
| Track D | Explicit Authorial Corrections | Pending verification |
| **Total unique review identities (Tracks A-C)** | — | **657** |
| Duplicate review identities | — | 0 |

### 7.5 Production Packet Artifacts

**Location:** `/home/liongateos/PCOG-Research-Archive/research/gd-bible-revision-review-packets-v1`

| File | SHA-256 |
|------|---------|
| `existing_change_review_packets.jsonl` | `be68fe90ecdd924d6b57cfc19055fe8c978dcf8ff87dbf388fc0f7c7b915d1cf` |
| `new_change_tier1_review_packets.jsonl` | `b11d8176e4854930bd819da5911244c08129cf84425dd7e7e96633fe5e371f08` |
| `owner_candidate_review_overlay.jsonl` | `389ff0e6c4e725424fa04d246316f335c1ea23871a54e57969c9753995facefb` |
| `review_universe_index.jsonl` | `f083e0b2312aee6dfe92eac88fcfde93854c33e7b9d5b3a2005943104e5d4186` |
| `manifest.json` | `04d89f8db429790fb95b47943b98491ad1cb0765c03e0438db05c53f287171d7` |

**Production backup:**
```
Location: /mnt/SanDisk-Backup/MASTER_BACKUPS/GD-Bible/gd-bible-revision-review-packets-v1-production-20261015-153001.tgz
SHA-256: 37f3ad3a2ec46e8444ab5615ab6b0ba3ff655857179c1470cf8f147cc09685a5
```

### 7.6 Current Audited Rule Families

| Family | Rules | Status |
|--------|-------|--------|
| R001 | R001 | EVIDENCE_AUDIT |
| R002 family | R002/R004/R006/R007/R008 | EVIDENCE_AUDIT |
| R003 family | R003/R005 | EVIDENCE_AUDIT |

**R009 deferred** to reverential-capitalization/style review.

### 7.7 Current Next Action

Establish and use durable editorial-review records, continue bounded rule/family evidence
audits, perform external verification and owner decisions before any new application.

### 7.8 Future CASE-Safe Research Insight Export

A future CASE-safe research insight export/sidecar is planned.

**Allowed exports (with provenance preserved):**
- ARCHIVE_NATIVE evidence quotations and verified source metadata
- ARCHIVE_CITED_EXTERNAL quotations with explicit attribution
- Source-native Scripture references (verbatim from archive documents)
- Neutral navigation identifiers (verse keys, document paths)

**DETERMINISTIC_CANONICAL classification alone does not confer CASE-export eligibility.**
The following are NOT eligible: canonical GD wording, KJV-to-GD comparisons,
transformation-manifest facts, GD editorial counts.

**Excluded from CASE export:** GD editorial recommendations, owner decisions,
MODEL_EXTERNAL and MODEL_DERIVED reasoning, lifecycle states, transformation-manifest
details. Do not import as archive fact.

---

## Evidence index (verified through 2026-10-13)

| Evidence | Location / commit |
|---|---|
| M12 reconciliation record | `docs/M12_EVIDENCE_RECONCILIATION.md` (commit `b3a47c8`) |
| Anchor gate + verdict manifest | `gd_anchor_verifier.py`, `anchor_validity_manifest.json` (commit `b3a47c8`) |
| Church Archive roadmap (CASE numbering, standing rules) | `docs/CHURCH_ARCHIVE_SEARCH_ROADMAP.md` (commit `70c60ec`) |
| M12 extraction cause | commit `016115e`; `gd_research_extract.py` v1.1.0 |
| Pre-M12 sidecar (immutable) | `/mnt/SanDisk-Backup/MASTER_BACKUPS/archive_research_sidecar_20261011_002538.db`, `23a5723c…` |
| Pre-M12 JSON export | `PCOG-Research-Archive/metadata/gd_bible_30730_findings_export.json`, `305eb647…` |
| Live sidecar (operating baseline) | `archive_research_sidecar.db`, `f8c20ede…`, 19,340 findings |
| Full HIGH research closeout | `docs/GD_FULL_HIGH_RESEARCH_CLOSEOUT_2026-10-13.md` (commit `4e621a6`) |
| Combined HIGH research artifact | `/home/liongateos/PCOG-Research-Archive/research/full-high-research-combined-v1/combined_high_research.jsonl`, SHA-256 `a9cc75dcc664e77811f646053b5c0748ad6a14907c7d84e2c2323abc93bda92a` |
| Verified preservation backup | `/mnt/SanDisk-Backup/MASTER_BACKUPS/GD-Bible/gd-bible-full-high-research-combined-v1-20261013-123012.tgz`, SHA-256 `8f49af0d45b69132cac7f1c24644bef2c546703e911887e5b69aaea9ac8189c6` |
---

## 8. Recovery to LionGateOS-Bible (2026-10-16)

### 8.1 Context

GD Bible research scripts and documentation were historically developed
inside the `pcog-archive-collector` worktree (CASE). This section records
their permanent recovery to the correct home repository: `LionGateOS-Bible`.

**Recovery source worktree:** `/home/liongateos/gd-bible-closeout`
(worktree of `pcog-archive-collector`, branch `gd-full-high-research-closeout`)

**Recovery target:** `/home/liongateos/LionGateOS-Bible`,
branch `gd-research-recovery-20261016`

### 8.2 Recovery commits

| Commit | Message |
|---|---|
| `ee3e147` | Recover GD Bible editorial research and revision tooling (Batches 1-2) |
| `2009a7a` | Recover GD Bible research pipelines and Track D tooling (Batch 3) |
| `1d79042` | Recover GD Bible M06-A1 runner and AI schema (Batch 4) |
| `c4d20c1` | Preserve historical GD M02-C architecture research |

62 files recovered total. All four batches plus historical M02-C planning
document now reside in this repository.

### 8.3 Repository separation safeguard

Going forward, the authoritative repository for GD Bible research work is
`LionGateOS-Bible`. GD Bible research must not be implemented in
`pcog-archive-collector` merely because historical scripts were located
there. See `docs/handoffs/GD_BIBLE_PERMANENT_HANDOFF_2026-10-16.md` for
the full ownership rules and session guidance.

### 8.4 §1 repository reference — corrected

Section 1 originally recorded the workspace as
`/home/liongateos/pcog-archive-collector` (correct at time of writing,
2026-10-13, when research scripts resided there). Section 1 has been
updated (2026-10-16) to identify `/home/liongateos/LionGateOS-Bible` as
the GD Bible repository. References to `pcog-archive-collector` elsewhere
in this document describe historical work locations or read-only CASE data
dependencies; they do not authorize future GD Bible development there.
