# GD Bible — Permanent Handoff and Repository-Separation Safeguards

**Date:** 2026-10-16
**Repository:** `/home/liongateos/LionGateOS-Bible`
**Branch:** `gd-research-recovery-20261016`
**HEAD at creation:** `c4d20c1`

This document is the permanent session handoff for the GD Bible project.
Its purpose is to ensure future Claude, DeepSeek, and ChatGPT sessions do
not accidentally mix GD Bible development with CASE development, and can
orient themselves without relying on the owner's memory.

---

## 1. Repository identity

| Field | Value |
|---|---|
| Repository path | `/home/liongateos/LionGateOS-Bible` |
| GitHub repository | `LionGateOS/LionGateOS-Bible` (public) |
| Project name | GD Bible — Grow Daily |
| Git user | LionGateOS |
| Current active branch | `gd-research-recovery-20261016` |
| Main branch | `main` |
| HEAD at this handoff | `c4d20c1` |

**This is NOT `pcog-archive-collector`.** CASE (Church Archive Search
Engine) lives in `/home/liongateos/pcog-archive-collector`. GD Bible
research scripts that were historically developed in the CASE worktree have
now been recovered to this repository. They belong here.

---

## 2. Recovery branch — what was recovered and verified

### 2.1 Recovery commits (2026-10-16)

| Commit | Description |
|---|---|
| `ee3e147` | Recover GD Bible editorial research and revision tooling (Batches 1-2) |
| `2009a7a` | Recover GD Bible research pipelines and Track D tooling (Batch 3) |
| `1d79042` | Recover GD Bible M06-A1 runner and AI schema (Batch 4) |
| `c4d20c1` | Preserve historical GD M02-C architecture research |

These four commits together brought 62 files onto the recovery branch that
are not present on `main`.

### 2.2 Recovered file categories

**Research Python scripts** (`source/growdaily/scripts/bible/`):

| File | Class | Notes |
|---|---|---|
| `gd_ai_pipeline.py` | Class A (byte-identical) | Pydantic schema for XGrammar structured output |
| `gd_anchor_verifier.py` | Class A | Anchor validity gate |
| `gd_bible_revision_mapping.py` | Class A | Deterministic revision mapping |
| `gd_bible_revision_review_packets.py` | Class A | Revision review packet generator |
| `gd_canonical_coordinates.json` | Class A | Canonical coordinate data |
| `gd_m06_a1_stage_a_run.py` | Class B (adapted) | M06-A1 Stage A runner; separate `GD_M06_OUTPUT_ROOT` from `GD_PILOT_RUNS_ROOT`; `_FORBIDDEN_OUT` guard |
| `gd_research_benchmark.py` | Class A | Throughput benchmark harness |
| `gd_research_chunk.py` | Class A | Deterministic chunker |
| `gd_research_corpus.py` | Class A | Corpus selection |
| `gd_research_extract.py` | Class A | RTF extractor v1.1.0 |
| `gd_research_model.py` | Class A | Ollama HTTP client; allow-list, workload check |
| `gd_research_pipeline.py` | Class A | Core pipeline: offset derivation, verification chain |
| `gd_research_run.py` | Class A | Run state, atomic writes, resumability |
| `gd_research_supervise.py` | Class A | Batch supervisor; timeout, no-progress detection |
| `gd_research_triage.py` | Class A | HIGH/LOW triage |
| `gd_research_verify.py` | Class A | Quote verification and match classification |
| `gd_scripture_engine.py` | Class A | Deterministic scripture reference engine |
| `gd_string_assertion.py` | Class A | Byte-exact evidence span assertion firewall |
| `track_d_authorial_corrections_discovery.py` | Class A | Track D discovery |
| `track_d_discovery_v2.py` | Class A | Track D discovery v2 |

**Test suite** (`source/growdaily/scripts/bible/tests/`):

- `__init__.py`
- `test_gd_bible_revision_mapping.py`
- `test_gd_bible_revision_review_packets.py`
- `test_gd_scripture_engine.py`
- `test_orchestration.py`
- `test_track_d_discovery_v2.py`

**Editorial and research documentation**
(`source/growdaily/docs/bible/editorial/`):

| File | Description |
|---|---|
| `GD_BIBLE_CURRENT_STATE.md` | GD research program current state (authoritative) |
| `GD_BIBLE_EDITORIAL_REVIEW_V1.md` | Editorial review V1 design |
| `GD_BIBLE_REVISION_REVIEW_PACKETS_V1_AUDIT.md` | Revision review audit |
| `gd_bible_editorial_rule_review_registry.jsonl` | Rule review registry |
| `gd_bible_owner_review_inputs.json` | Owner review inputs |

**Research directory** (`source/growdaily/docs/bible/editorial/research/`):

| File | Description |
|---|---|
| `anchor_validity_manifest.json` | Anchor validity verdicts for 19,340 findings |
| `gd-bible-review-packets-v1-audit-complete.md` | Review packets audit |
| `gd-bible-review-packets-v1-final-ready.patch` | Review packets patch |
| `GD_FULL_ARCHIVE_EXTRACTION_READINESS.md` | Extraction readiness report |
| `GD_FULL_HIGH_RESEARCH_CLOSEOUT_2026-10-13.md` | Full HIGH research closeout |
| `GD_M02C_ARCHITECTURE_PLAN.md` | **HISTORICAL PLANNING ONLY — NOT AUTHORIZED** |
| `GD_TO_CASE_HANDOFF_2026-10-13.md` | GD → CASE research handoff |
| `M12_EVIDENCE_RECONCILIATION.md` | M12 RTF extraction reconciliation |
| `track-d-discovery-report.md` | Track D discovery report |
| `track-d-discovery-summary.json` | Track D discovery summary |
| `track-d-discovery-v2.jsonl` | Track D discovery v2 data — **EXCLUDED FROM PUBLIC PUBLICATION** (verbatim archive quotes; private original preserved on local recovery branch) |

**M06-A1 planning** (`source/growdaily/docs/bible/editorial/research/m06/`):
14 specification and design documents covering GD-M06-A0 baseline freeze,
A1 enrichment design, execution plan, schema, expansion input manifest,
input authority freeze, pilot design and contract, sample selection, smoke
test manifest, stage A pilot manifest, and translation enrichment spec.

**Editorial rule reviews** (`source/growdaily/docs/bible/editorial/rule_reviews/`):
README + R001, R002, R003, R015 rule review documents.

**Baseline checksum:** `source/growdaily/docs/bible/editorial-batch1-baseline.sha256` (stale entries for `anchor_validity_manifest.json` and `track-d-discovery-v2.jsonl` removed 2026-10-16; see publication sanitization note)

### 2.3 Class B adaptation detail — `gd_m06_a1_stage_a_run.py`

The original source used a single path root for both read-only inputs and
outputs. The recovered version separates them:

- `GD_PILOT_RUNS_ROOT` — controls read-only input paths (STAGE, EXP);
  default: sibling `pilot_runs/` directory.
- `GD_M06_OUTPUT_ROOT` — controls all output paths; default:
  `/home/liongateos/gd-m06-a1-runs`.
- `_FORBIDDEN_OUT` — tuple of six protected trees outputs must never enter.
- `check_out(p)` — validates output path lexically and via symlink
  resolution before any file write; raises `SystemExit` on violation.

### 2.4 Historical M02-C architecture plan

`GD_M02C_ARCHITECTURE_PLAN.md` is a preservation of session `f0246d21`
(DeepSeek, 2026-10-11). It is marked HISTORICAL PLANNING — NOT AUTHORIZED
FOR EXECUTION. It contains the M02-B audit findings (verified measurements)
and the M02-C architecture design (design only). Nothing in it authorizes
inference, GPU workloads, or production database writes.

---

## 3. What is complete versus future work

### 3.1 Complete

- GD full-HIGH research corpus (22,756 passages, 58,498 findings)
- Combined artifact: `combined_high_research.jsonl`, SHA-256
  `a9cc75dcc664e77811f646053b5c0748ad6a14907c7d84e2c2323abc93bda92a`
- M12 RTF extraction reconciliation and evidence documentation
- Anchor validity manifest (`anchor_validity_manifest.json`)
- Revision review packets V1 (Tracks A, B, C)
- Editorial review V1 audit for rule families R001, R002/R004/R006/R007/R008,
  R003/R005 (status: EVIDENCE_AUDIT)
- Track D authorial corrections discovery
- Scripture normalization and assertion tooling
- GD Bible recovery to this repository (all four batches + M02-C plan)

### 3.2 Pending owner decisions — no action without approval

| Item | Decision needed |
|---|---|
| Merge `gd-research-recovery-20261016` to `main` | Owner must approve merge |
| Push `main` to GitHub | Owner must approve push |
| GD-M06-A0.2 Baseline Freeze execution | Approval required per GD_BIBLE_CURRENT_STATE.md §6 |
| GD-M06-A1 enrichment run | Requires M06-A0.2 completion first; separate approval |
| GD-M02-C implementation | Requires five open decisions resolved (see GD_M02C_ARCHITECTURE_PLAN.md §6) |
| Track D — restore/re-anchor 11,390 suspended findings | Separate milestone, separate approval |
| CASE-safe research export sidecar | Requires explicit interface document |
| R009 reverential capitalization review | Deferred; separate scheduling |
| UK distribution authorization from Cambridge University Press | Rights process ongoing |

### 3.3 Active editorial work

Editorial Review V1 is the current phase. It establishes durable
repository-backed evidence records for each transformation rule family.
**No canonical Bible text is edited during this phase.**

Protected in this phase (must not change):
- `source/growdaily/assets/bible/en_kjv.json`
- `source/growdaily/assets/bible/kjv_modified.json`
- `source/growdaily/assets/red_letters/jesus_speech_map_custom.json`
- Production review packets
- Archive databases and archive originals

---

## 4. Canonical Bible text and protected source assets

### 4.1 Standard KJV

**File:** `source/growdaily/assets/bible/en_kjv.json`
**Purpose:** Authoritative reference-only standard KJV. Never modified.
**Structure:** 66 books, 1,189 chapters, 31,102 canonical verses, 0 missing.

### 4.2 GD custom Bible text

**File:** `source/growdaily/assets/bible/kjv_modified.json`
**Purpose:** The canonical GD custom text. Only edited through the
documented editorial lifecycle with owner approval.
**Current scope:** 335 unique verses changed (383 individual text operations).

### 4.3 Words-of-Jesus map

**File:** `source/growdaily/assets/red_letters/jesus_speech_map_custom.json`
**Current state:** 2,055 entries, 0 unexpected zero-red entries,
0 projection failures.

### 4.4 Archive originals

**Location:** `/home/liongateos/PCOG-Research-Archive/documents/`
**Count:** 21,469 files preserved
**Principle:** Bytes-immutable. No GD process rewrites them.

### 4.5 Protected research databases (CASE-side, read-only from GD)

| Database | Path | SHA-256 |
|---|---|---|
| Approved M12 operating baseline | `pcog-archive-collector/archive_research_sidecar.db` | `f8c20ede…` (19,340 findings) |
| Pre-M12 immutable recovery | `/mnt/SanDisk-Backup/MASTER_BACKUPS/archive_research_sidecar_20261011_002538.db` | `23a5723c…` (30,730 findings) |
| Pre-M12 JSON export | `PCOG-Research-Archive/metadata/gd_bible_30730_findings_export.json` | `305eb647…` |

No GD development work may write to `archive_research_sidecar.db` or
`archive_search.db` without explicit owner approval.

### 4.6 Verification evidence

| Evidence | Location |
|---|---|
| Full HIGH research closeout | `source/growdaily/docs/bible/editorial/research/GD_FULL_HIGH_RESEARCH_CLOSEOUT_2026-10-13.md` |
| GD → CASE research handoff | `source/growdaily/docs/bible/editorial/research/GD_TO_CASE_HANDOFF_2026-10-13.md` |
| M12 reconciliation | `source/growdaily/docs/bible/editorial/research/M12_EVIDENCE_RECONCILIATION.md` |
| Anchor validity manifest | `source/growdaily/docs/bible/editorial/research/anchor_validity_manifest.json` |
| Source checksums | `docs/SOURCE_CHECKSUMS.md` |
| Combined HIGH research artifact | `/home/liongateos/PCOG-Research-Archive/research/full-high-research-combined-v1/combined_high_research.jsonl` |
| Combined artifact preservation backup | `/mnt/SanDisk-Backup/MASTER_BACKUPS/GD-Bible/gd-bible-full-high-research-combined-v1-20261013-123012.tgz` |
| Revision review packets backup | `/mnt/SanDisk-Backup/MASTER_BACKUPS/GD-Bible/gd-bible-revision-review-packets-v1-production-20261015-153001.tgz` |

---

## 5. Repository ownership

### 5.1 GD Bible owns

- Bible text: `en_kjv.json`, `kjv_modified.json`, `jesus_speech_map_custom.json`
- Transformation rules, editorial review, and the editorial lifecycle
- Scripture processing: `gd_scripture_engine.py`
- Evidence extraction and verification:
  `gd_research_extract.py`, `gd_research_pipeline.py`,
  `gd_research_verify.py`, `gd_string_assertion.py`, `gd_anchor_verifier.py`
- Research orchestration: `gd_research_run.py`, `gd_research_supervise.py`,
  `gd_research_benchmark.py`, `gd_research_corpus.py`, `gd_research_triage.py`
- Translation enrichment: `gd_m06_a1_stage_a_run.py`, M06-A1 specifications
- GD-specific AI schema: `gd_ai_pipeline.py`
- Strong's alignment assets
- Generated e-Sword editions

### 5.2 CASE owns

- Archive collection, document management, and FTS indexing (`archive_search.db`)
- User library, search/retrieval/ranking UI
- Archive enrichment pipeline
- Application interface (`case-study-editor-e1`)
- CASE-specific derived search structures (reproducible from GD artifacts)

### 5.3 Shared interface — explicit boundary

GD provides read-only derived research artifacts (currently:
`combined_high_research.jsonl`) to CASE. The interface terms are defined
in `source/growdaily/docs/bible/editorial/research/GD_TO_CASE_HANDOFF_2026-10-13.md`.

Any change to the shared interface (new export, new format, new schema) requires:
1. A written interface document owned by GD
2. Explicit owner approval before implementation
3. CASE consuming as read-only; GD retaining provenance

**Principle:** CASE must not silently modify GD source artifacts, silently
promote model observations into authoritative facts, or rewrite GD
provenance.

### 5.4 What does NOT constitute authorization

- A script living in `pcog-archive-collector` at some past point does not
  make it a CASE component. GD research scripts belong in this repository.
- A DeepSeek session being stored in the CASE workspace does not mean the
  session's content belongs to CASE.
- Historical co-location of GD Bible and CASE conversations in one DeepSeek
  workspace does not authorize future mixing.

---

## 6. DeepSeek workspace rules

| Workspace label | Authorized use |
|---|---|
| `GD BIBLE TRANSLATION` | Active GD Bible development sessions |
| `CASE — GPU SEARCH ENRICHMENT` | Active CASE development sessions |
| `ARCHIVE — GD BIBLE + CASE` | **Historical reference only — do not use for new work** |

**Preservation rule for the historical mixed workspace:**
- Do not delete any conversation history.
- Do not move or rename it.
- Do not modify any past session content.
- It may be opened for reading/reference only.
- All new GD Bible sessions must use the `GD BIBLE TRANSLATION` workspace.
- All new CASE sessions must use the `CASE — GPU SEARCH ENRICHMENT` workspace.

**Workspace label ≠ repository path.** A workspace labeled "GD Bible" does
not authorize writes to `pcog-archive-collector`. A workspace labeled "CASE"
does not authorize writes to `LionGateOS-Bible`. Always confirm the actual
repository path before any write.

---

## 7. Future session guidance

**Before making any change, confirm:**

1. Which repository are you authorized to modify?
   - GD Bible: `/home/liongateos/LionGateOS-Bible`
   - CASE: `/home/liongateos/pcog-archive-collector`
   - Never assume from workspace label alone.

2. Which branch is active?
   - Recovery branch: `gd-research-recovery-20261016`
   - Main (public): `main`
   - Do not mix work between branches without owner instruction.

3. Read these documents in this order before any substantive work:
   - `CLAUDE.md` (repo root) — agent boundary rules
   - `source/growdaily/docs/bible/editorial/GD_BIBLE_CURRENT_STATE.md` — GD research program state
   - `docs/CURRENT_STATE.md` — GD Bible text and editions state
   - This document for full ownership rules

4. GPU workloads and archive sources that must remain untouched:
   - Do not start or stop any Ollama model.
   - Do not start the vLLM server.
   - Do not run GD-M02-C inference.
   - Do not run M06-A1 enrichment without owner approval.
   - Do not write to `archive_search.db` or `archive_research_sidecar.db`.
   - Do not write to `/home/liongateos/PCOG-Research-Archive/research/production/`.
   - The RTX 3090 Ti is not available for unsupervised workloads.

5. Tasks requiring explicit owner approval:
   - Any canonical Bible text edit
   - Any production database write
   - Any GPU workload start
   - Merging recovery branch to main
   - Pushing to GitHub
   - Any new CASE interface or cross-repository data transfer
   - Relocating components between repositories

6. Recovery is complete. The following are future development (not recovery):
   - GD-M06-A0.2 Baseline Freeze
   - GD-M06-A1 enrichment run
   - GD-M02-C bounded constrained extraction proof
   - Track D suspended findings restoration
   - Any new rule family evidence audit beyond R001–R003/R015

---

## 8. Remaining integration and GitHub publication decisions

| Decision | Status |
|---|---|
| Merge `gd-research-recovery-20261016` → `main` | Pending owner approval |
| Push `main` to GitHub | Pending owner approval; depends on merge decision |
| Privacy review of recovered files before public push | Not yet performed |
| UK Cambridge University Press distribution authorization | Rights process ongoing |
| Rights audit of all non-GD components | Ongoing (see `docs/RIGHTS_AND_SOURCES.md`) |
| GD-M02-C implementation authorization | Not yet authorized |
| Interpreter policy decision (venv vs system Python) | Not yet decided |
| Second GPU (3090 Ti) policy for M02-C | Not yet decided |

---

*This document was created on 2026-10-16 by the recovery session that
produced commits `ee3e147` through `c4d20c1`. It must not be deleted or
replaced without creating a successor handoff first.*
