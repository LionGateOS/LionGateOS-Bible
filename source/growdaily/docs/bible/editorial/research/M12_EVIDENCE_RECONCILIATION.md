# M12 Evidence Reconciliation — Sidecar Generation Record

**Status:** Reconciliation documented and independently re-verified.
**Scope:** Research sidecar (`archive_research_sidecar.db`) — a *derived* layer.
**Canonical data:** Unchanged. No archive document, no `archive_search.db` row,
and no source file was modified by this record or by the P1 audit that produced it.

---

## 1. Summary

| | Pre-M12 baseline | Post-M12 live |
|---|---|---|
| Artifact | `archive_research_sidecar_20261011_002538.db` | `archive_research_sidecar.db` |
| Location | `/mnt/SanDisk-Backup/MASTER_BACKUPS/` | `/home/liongateos/pcog-archive-collector/` |
| SHA-256 | `23a5723caa11e81735235c68d06547b3d58e9c8594db3e10903bf2cc955f2d1e` | `f8c20ede53efdd71be00a71681e00a3f3141524ec1c1399561ebbd395e770d7c` |
| Size | 48,795,648 bytes | 48,795,648 bytes |
| `research_findings` rows | **30,730** | **19,340** |
| `rowid` range | 1 … 30,730 (contiguous) | 1 … 30,327 (**sparse**) |
| Documents represented | 2,377 | 2,060 |
| Written | 2026-10-11 00:24 EDT | 2026-10-11 16:24:40 EDT |
| `PRAGMA integrity_check` | ok | ok |

**Change:** 11,390 findings removed across 317 documents.
30,730 − 11,390 = 19,340.

This was an **intended evidence-reconciliation**, not data loss. The purpose was
to remove findings whose stored evidence offsets no longer resolved against the
corrected RTF extraction. The reduction is correct in intent; the sweep was
imperfect in execution (§5) and, until now, undocumented (§7).

---

## 2. Cause — the M12 RTF extraction correction

Commit `016115ebb0107db6e421d604d8f95fc3fec29c28`
— *"M12: Patch RTF extraction skip logic to suppress metadata leaks"* —
authored **2026-10-11T16:26:21-04:00**, touching `gd_research_extract.py`
(+195 / −24).

`EXTRACTOR_VERSION` was raised **1.0.0 → 1.1.0**. `_rtf_text()` was rewritten from
regular-expression stripping to a group-aware parser with an explicit
`_RTF_SKIP_DESTINATIONS` set:

```
fonttbl, colortbl, stylesheet, info, header, footer, headerl, headerr, headerf,
footerl, footerr, footerf, pict, object, annotation, field, fldinst, listtable,
listoverridetable, revtbl, generator, xmlnstbl, themedata, datastore, filetbl
```

**Why text changed.** The v1.0.0 extractor removed only `{\*...}` destination
groups (`_RTF_DESTINATION = re.compile(r"\{\\\*.*?\}", re.DOTALL)`). It therefore
leaked font tables, colour tables, `\info` metadata, embedded pictures and field
instructions into the extracted body text. The v1.1.0 parser skips those
destinations, producing **shorter and differently offset** text. This is a
deliberate correctness fix.

**Scope of re-extraction.** Exactly **547** of the corpus's **795**
`container='RTF'` documents changed text (451 `.rtf`, 95 `.doc`, 1 `.docx`
by filename — all sniffed as RTF containers; the extension is not the
classifier here).

---

## 3. Direct lineage evidence

The live sidecar is the **direct in-place descendant** of the audited baseline.
It was not rebuilt, regenerated, or merged from another source.

| Test | Result | Weight |
|---|---|---|
| **Sparse rowids** | Baseline `max(rowid)=30,730` with `count=30,730` (contiguous). Live `max(rowid)=30,327` with `count=19,340` (sparse). | **Decisive.** A rebuild would have produced contiguous rowids `1…19,340`. Sparse rowids bounded by 30,327 can only result from in-place deletion against the 30,730-row table. The trailing 403 rows were removed. |
| Survivor rowids preserved | Survivor `finding_uid` maps to rowid 1 in both baseline and live. | In-place retention, not re-insertion. |
| `created_at` preserved | Both generations carry `2026-10-11 04:24:01–02` UTC. | **Decisive.** The JSON export schema (`source_file, document, collection, source_sha256, chunk_id, pass, finding_index, finding`) contains **no** `created_at` field, so the live file cannot have been rebuilt from the export. |
| Field-level identity | 12/12 sampled survivors byte-identical across all 24 columns. | No re-derivation or field drift. |
| Set containment | live `finding_uid` ⊆ baseline `finding_uid`; live-only = 0. Live-only `(doc_path, quote)` pairs = 0. | No new rows. |
| Export ≡ baseline content | `(document, source_sha256, chunk_id, finding_index)` key sets **identical**: 27,548 distinct, 0 export-only, 0 baseline-only. Distinct quote sets identical: 28,450. Document sets identical: 2,377. | Ties the export and the baseline sidecar to the same finding population. |
| Timeline | 16:22:41 state doc → 16:23:26 `archive_search.db` → **16:24:40 sidecar reconciled** → 16:26:21 M12 commit. | Ordered and consistent. |

**Verified chain:**

```
Gemma/Qwen research run
        │  30,730 findings / 2,377 documents
        ├──────────────► gd_bible_30730_findings_export.json
        │                sha256 305eb647…  (2026-10-11 00:03 EDT)
        ▼
  baseline sidecar  sha256 23a5723c…  30,730 rows  (2026-10-11 00:24 EDT)
        │
        │   M12 RTF correction (gd_research_extract.py 1.0.0 → 1.1.0)
        │   547 RTF-container documents re-extracted
        ▼
  live sidecar (in-place deletion)  sha256 f8c20ede…  19,340 rows  (16:24:40 EDT)
```

---

## 4. Anchor validity of the surviving 19,340 findings

Re-verified deterministically by `gd_anchor_verifier.py` (see
`anchor_validity_manifest.json`).

| Verdict | Findings | Documents |
|---|---|---|
| `valid` | **18,626** | — |
| `out_of_bounds` | **112** | 27 |
| `mismatch` | **602** | 40 |
| **`invalid_total`** | **714** | **56** (union; 11 documents have both) |

Arithmetic: **18,626 + 112 + 602 = 19,340** ✔

Deterministic verdict-stream fingerprint (normalized verdicts only, in
`finding_uid` order):

```
7a335e805cb8bb4a24c70c35f8e419259a583680f5181eb0cdc5f6df50d76256
```

Manifest content fingerprint (excludes `generated_at`):

```
57e044ce379b5dd595cc8560e2f1d20b4717ac65395e32463dd7c2f94d89a012
```

All 56 affected documents have `container='RTF'`; collections WCG 37, PCG 18,
GRF Letters 1. Full enumeration in `anchor_validity_manifest.json`
(`affected_documents`, `quarantine`).

### 4.1 The strict guardrail over-quarantines — important

`gd_string_assertion.verify_evidence_span()` performs **literal substring equality
only** and has no normalization layer. Applied verbatim to the live sidecar it
yields:

| Semantics | valid | out_of_bounds | mismatch | invalid | docs |
|---|---|---|---|---|---|
| strict `verify_evidence_span` | 17,987 | 112 | 1,241 | **1,353** | 200 |
| normalization-aware (correct) | 18,626 | 112 | 602 | **714** | 56 |

The 639-finding / 144-document difference is entirely the 5,931
`whitespace_normalized` plus 35 `punct_normalized` rows. **Any consumer of the
guardrail must apply the normalization implied by `source_match_type`, or it will
discard 639 valid relationships.** `gd_anchor_verifier.classify()` implements this;
`gd_string_assertion.py` is unchanged.

---

## 5. Residue — the sweep was imperfect

Of the 342 baseline documents with at least one invalid anchor:

| Class | Documents | Findings | Meaning |
|---|---|---|---|
| Dropped **and** genuinely invalid | 286 | ~11,032 | Rule-conformant |
| Dropped but anchors **still valid** | 31 | **358** | **Over-deletion** |
| Retained but anchors **invalid** | 56 | **714** | **Under-deletion** |

The 11,390 removed findings decompose as: **358** still valid, **978**
out-of-bounds, **10,054** resolving to different text.

The applied predicate was **document-scoped** ("remove the document's findings"),
not finding-scoped, and it produced errors in both directions. The mechanism is
proven; the exact invocation is not recoverable — no script, commit, or log
performs or records the pruning (`.gitignore` excludes both `*.db` and `*.json`,
so neither generation is version-controlled).

**Do not restore the 11,390 blindly.** Approximately 5,950 of them still contain
their quote verbatim in the corrected text and are recoverable **by re-anchoring
alone**; the remainder need re-extraction or re-derivation. That work is a
**separate, unauthorized future milestone**.

---

## 6. `documents.char_count` is stale — never use it for anchor bounds

`documents.char_count` disagrees with `len(document_text.content)` in **547**
documents (Python-verified over all 5,439 rows; no embedded NULs). It reflects
pre-M12 extraction and was not refreshed when content was corrected. Examples:

| Document | `char_count` | actual `len(content)` |
|---|---|---|
| `GRF Letters/2007/09.07.07-Jerusalem_ES.doc` | 2,870,615 | 24,468 |
| `PCG/KOD transcripts/2015/KOD16-03 Prophecy Is Dual.docx` | 715,932 | 21,196 |
| `PCG/Booklets/ATK_EN_E03_2303-25K.rtf` | 434,308 | 413,196 |

Because the value is stale **and larger** than reality, the check
`char_end > documents.char_count` flags **0 of the 714 real failures** — a
verifier trusting it would accept every broken anchor.

> **Rule:** anchor bounds must be taken from `len(document_text.content)`.
> `documents.char_count` is a legacy ingest metric only.

---

## 7. `scripture_refs` — model-attributed ≠ verified

The sidecar's `scripture_refs` column holds the language model's **own**
structured output, not deterministic extraction. It is copied straight from the
LLM response (`gd_m02b_orchestrator.py`: `json.dumps([r.get("reference") for r in
finding.get("scripture_refs", [])])`); the parallel JSON shows
`"scripture_refs": ["Daniel 12:3"]` inside the model's own record.

Measured over the 19,340 live findings:

| Property | Value |
|---|---|
| Findings carrying ≥1 ref | 13,577 (70.2%) |
| Total ref entries / distinct | 15,612 / 7,147 (0 malformed) |
| Resolvable via `gd_scripture_engine` CANON/ALIASES | 12,984 (83.2%) |
| **Unresolvable** | **2,628 (16.8%)** |
| Ref present in its own `quote` | 6,045 (38.7%) |
| Ref absent from quote but present in `note` | 967 (6.2%) |
| **Ref not textually present anywhere in the finding** | **8,600 (55.1%)** |

Common unresolvable forms: Roman-numeral book names (`II Corinthians 4:4`,
`I Corinthians 2:11`, `II Peter 2:4` — the alias table has `"ii cor"` but not
`"ii corinthians"`) and **chapter-only references with no verse**
(`Revelation 17`, `Genesis 1`, `Romans 8`), which `SCRIPTURE_PATTERN` cannot match
because it requires `chapter:verse`.

> **Distinction to preserve:**
> **stored `scripture_refs`** = model-attributed annotations, unverified, and
> 55% ungrounded in their own finding text.
> **`gd_scripture_engine.extract_references(document_text)`** = deterministic,
> reproducible references computed against canonical text.
> These are two different evidentiary classes and must not be merged or
> presented as equivalent.

Of the 714 invalid-anchor findings, 576 carry `scripture_refs` holding 671 ref
entries — **4.3%** of all refs. Excluding them from downstream relationship
building is a small, reportable coverage cost.

---

## 8. Preservation and recovery status of the 30,730 state

The pre-M12 research is preserved in **two independent locations**, both verified:

1. **Baseline sidecar** — `/mnt/SanDisk-Backup/MASTER_BACKUPS/archive_research_sidecar_20261011_002538.db`
   `sha256 23a5723caa11e81735235c68d06547b3d58e9c8594db3e10903bf2cc955f2d1e`,
   30,730 rows, `integrity_check = ok`.
2. **JSON export** — `/home/liongateos/PCOG-Research-Archive/metadata/gd_bible_30730_findings_export.json`
   `sha256 305eb6475828dfde70def700c2b0543204de48e3090bae096b261a0194c70a5f`,
   30,730 records, 2,377 documents. Content-identical to the baseline sidecar on
   `(document, source_sha256, chunk_id, finding_index)` and on quotes.

Both are outside the production repository and outside version control.
**Recommendation:** keep both, and add hash manifests to version control so
lineage is verifiable without versioning the data itself.

> **Not a restore point:** `archive_research_sidecar.db.m02_backup` is
> byte-identical to the *already-pruned* live file (same SHA-256, same size,
> mtime matching to the nanosecond). It restores nothing.

---

## 9. Documented caveats

1. **Naming collision.** `audit_m06.py` in this repository uses "M06" for an
   older, unrelated metadata/search-quality/security audit. That file does **not**
   define the current M06 milestone (the planned Scripture Relationship Layer).
2. **`CURRENT_STATE.md` is inconsistent.** Lines 7 and 25 describe the *live*
   sidecar using the *baseline* hash and the 30,730 count. This should be
   corrected in a separate approved change — it was deliberately not touched
   under the P1 boundary.
3. **Not fully deterministic as a file.** `anchor_validity_manifest.json`
   contains a generation timestamp, so the file is not byte-reproducible. The
   deterministic elements are `verdict_stream_sha256` and
   `manifest_content_sha256`.
4. **Unauthorized work.** The reconciliation ran at 16:24:40, 119 seconds after
   `CURRENT_STATE.md` recorded that *"no database changes are authorized by this
   recovery closeout."* The work was legitimate; the documentation and the work
   were simply concurrent, and neither referenced the other.

---

## 10. Related artifacts

| Artifact | Role |
|---|---|
| `gd_anchor_verifier.py` | Normalization-aware anchor classifier + manifest generator. **The** gate for anything consuming evidence offsets. |
| `anchor_validity_manifest.json` | 19,340 per-finding verdicts + 714-entry quarantine. Auditable, hash-anchored. |
| `gd_string_assertion.py` | Original strict guardrail. Unchanged. Exact-match semantics only. |
| `gd_scripture_engine.py` | Deterministic scripture reference extraction (canon + aliases). |
| `gd_research_extract.py` | RTF/Word extraction. `EXTRACTOR_VERSION 1.1.0` as of M12. |
