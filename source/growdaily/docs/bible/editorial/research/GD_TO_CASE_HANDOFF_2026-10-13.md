# GD Bible → CASE Research Handoff

**Date:** 2026-10-13
**Owner of source research:** GD Bible
**Consumer:** Church Archive Search Engine (CASE)
**Repository:** `LionGateOS/Church-Archive-Search`
**GitHub main at handoff preparation:** `245119eaf6faf8b1fce1a79f2231717fa7fa6199`

## 1. Purpose

This document hands the completed GD Bible full-HIGH archive research corpus to CASE
for read-only search, retrieval, ranking, filtering, evidence display, and other
presentation-layer use.

GD retains ownership of extraction lineage, research generation, evidence verification,
and provenance. CASE owns search/retrieval/ranking/UI concerns.

CASE must not silently modify GD source research artifacts or promote model observations
into authoritative facts.

## 2. Completed full-HIGH research corpus

The current full-archive HIGH target is completely covered:

- Current unique HIGH passages: **22,756**
- Covered passages: **22,756 / 22,756**
- Documents represented: **8,221**
- Fresh 2026 research passages: **16,788**
- Revalidated historical passages reused: **5,968**
- Verified findings in the combined candidate: **58,498**
- Quarantined findings retained separately in provenance: **149**
- Missing passage identities: **0**
- Duplicate selected passage identities: **0**

The historical reuse population was independently reconstructed using the current
extractor/chunker and all **15,893 historical verified findings** associated with those
5,968 passages were rechecked against current text. Evidence failures: **0**.

No additional model rerun is required for this completed HIGH population.

## 3. Primary CASE-consumable artifact

Combined research artifact:

`/home/liongateos/PCOG-Research-Archive/research/full-high-research-combined-v1/combined_high_research.jsonl`

Manifest:

`/home/liongateos/PCOG-Research-Archive/research/full-high-research-combined-v1/manifest.json`

Combined JSONL SHA-256:

`a9cc75dcc664e77811f646053b5c0748ad6a14907c7d84e2c2323abc93bda92a`

Independent artifact verification confirmed:

- rows: 22,756
- unique passage keys: 22,756
- duplicate keys: 0
- fresh selections: 16,788
- historical reuse selections: 5,968
- verified findings: 58,498
- quarantined findings: 149
- malformed JSON rows: 0
- manifest digest matches artifact: PASS

CASE should consume this artifact **read-only**.

## 4. Preservation backup

Verified backup:

`/mnt/SanDisk-Backup/MASTER_BACKUPS/GD-Bible/gd-bible-full-high-research-combined-v1-20261013-123012.tgz`

SHA-256:

`8f49af0d45b69132cac7f1c24644bef2c546703e911887e5b69aaea9ac8189c6`

Archive readability check: **PASS**.

## 5. Research finding types

The five GD research finding types are:

- `scripture`
- `translation`
- `terminology`
- `wording`
- `capitalization`

These are **research finding types**, not document subjects or sermon topics.

CASE UI, facets, schemas, or APIs should label them accordingly, for example
**Research Finding Type**.

Do not present these five values as a subject-topic taxonomy.

A future subject/doctrine/topic classification layer is a separate GD-derived layer.

## 6. Finding totals by research finding type

The completed fresh research generation produced:

- `translation`: 13,544
- `terminology`: 12,608
- `scripture`: 11,396
- `wording`: 4,863
- `capitalization`: 194

The combined 58,498-finding corpus includes both fresh verified results and independently
revalidated historical results. Consumers should use the combined artifact itself for
combined-population filtering and counting rather than assuming the fresh-only topic
totals above describe all 58,498 findings.

## 7. Evidence semantics

GD evidence verification is deterministic.

Accepted evidence provenance includes:

- `in_chunk_exact`
- `in_chunk_normalized`
- `document_only`

A finding is a model-generated research observation whose quoted evidence has passed the
GD verification rules. It is not automatically an authoritative theological, historical,
linguistic, or editorial conclusion.

Fabricated or unsupported evidence is quarantined rather than silently accepted.

## 8. Scripture-reference boundary

`scripture_refs` attached to research findings are **model-attributed strings**.

They are not equivalent to the separate deterministic GD scripture-reference engine and
must not be represented by CASE as deterministically verified scripture references unless
a later GD normalization/assertion layer explicitly establishes that status.

Preserve original scripture-reference strings verbatim.

Do not silently repair, normalize, merge, or reinterpret them.

## 9. Protected M12 operating baseline

The existing protected research sidecar remains:

`archive_research_sidecar.db`

Current approved operating baseline:

- findings: **19,340**
- documents: **2,060**
- SHA-256: `f8c20ede53efdd71be00a71681e00a3f3141524ec1c1399561ebbd395e770d7c`

The 58,498-finding combined artifact **does not replace this database**.

No automatic migration, overwrite, merge, or production-database write is authorized by
this handoff.

Any future migration from the combined artifact into a database requires a separate,
explicitly approved milestone with validation and rollback protection.

## 10. Archive and extraction baseline

Archive originals:

`/home/liongateos/PCOG-Research-Archive/documents`

Preserved files: **21,469**

Canonical corrected full extraction database:

`archive_search_full_v2.db`

SHA-256:

`c181edc8bdc01fa3bfaa7030f11647d1c18bba229db6caa02d07fa5534f0baa6`

Extraction results:

- documents: 21,469
- searchable/extracted text: 20,475
- unsupported: 986
- extraction errors: 8

Archive originals are immutable source evidence and must never be rewritten by CASE.

## 11. CASE permissions for this handoff

CASE may:

- read the combined HIGH research artifact
- index it into CASE-owned derived search structures
- build search facets over verified GD research metadata
- rank and retrieve findings
- link findings back to source documents/passages
- expose provenance and evidence in UI
- build CASE-owned caches or indexes that are reproducible from the GD artifact

CASE must:

- preserve source provenance
- distinguish model observations from authoritative source text
- keep GD finding types distinct from subject-topic classification
- retain the source passage/document identity needed to trace every result
- treat the combined artifact as read-only upstream evidence

CASE must not:

- modify archive originals
- modify the combined GD artifact
- modify the protected 19,340-row sidecar
- silently promote quarantined findings
- silently repair model-attributed scripture references
- rewrite GD provenance
- treat 58,498 as rows already installed in the protected sidecar
- infer that every archive document has HIGH research findings

## 12. Authoritative closeout records

Primary full-HIGH closeout:

`docs/GD_FULL_HIGH_RESEARCH_CLOSEOUT_2026-10-13.md`

Canonical GD current state:

`docs/GD_BIBLE_CURRENT_STATE.md`

The closeout records the reconstruction of the historical two-model research process,
fresh production run, historical reuse validation, combined artifact construction,
checksums, and preservation backup.

## 13. Recommended CASE integration pattern

Preferred boundary:

`GD immutable/verified derived research`
→ `read-only CASE ingestion`
→ `CASE-owned search/index/ranking structures`
→ `CASE presentation`

CASE-specific schemas and indexes should be regenerable from the GD source artifact rather
than becoming the only surviving representation of GD research.

Any discovered defect in GD research should be reported back to GD and corrected in a new
versioned GD-derived artifact. CASE should not silently patch the upstream evidence.

## 14. Handoff status

**GD full-HIGH research generation: COMPLETE**

**GD evidence/reuse verification: PASS**

**Combined artifact verification: PASS**

**Preservation backup: PASS**

**Protected M12 sidecar mutated by this work: NO**

**Archive originals mutated by this work: NO**

**Ready for CASE read-only integration planning: YES**
