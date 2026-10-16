# GD Bible — Full HIGH Research Corpus Closeout

**Date:** 2026-10-13
**Owner:** GD Bible workstream
**Status:** VERIFIED COMBINED CANDIDATE — source generations preserved unchanged

## Purpose

This record closes the full-archive HIGH-priority GD research expansion and
documents the verified reconciliation of:

1. the historical GD Gemma → Qwen production research, and
2. the 2026 full-archive fresh Gemma → Qwen production run.

No archive original was modified. The historical production output, fresh
production output, protected databases, and M12 recovery artifacts remain
preserved separately.

## Current full-archive HIGH target

The current full-archive triage contains:

- **22,756 distinct HIGH-priority passages**
- representing **8,221 documents**

The complete HIGH target is now accounted for by:

| Generation | Passages |
|---|---:|
| Fresh 2026 full-archive production | 16,788 |
| Historical validated reuse | 5,968 |
| **Total** | **22,756** |

There are no missing passage identities and no duplicate selections in the
combined candidate.

## Fresh full-archive production

Output root:

`/home/liongateos/PCOG-Research-Archive/research/full-archive-production-v1`

Workload:

`/home/liongateos/PCOG-Research-Archive/research/full-archive-index-21469-v1/high-definite-fresh-v1.jsonl`

Verified final state:

- HIGH passages screened by Gemma: **16,788 / 16,788**
- Qwen second-pass escalations required and completed: **861 / 861**
- Pending work: **0**
- Zero-finding audit queue: **1,903**
- Final verified findings: **42,605**
- Final quarantined findings: **68**
- Bad JSON files: **0**
- Missing screen passes: **0**
- Missing escalation passes: **0**
- Duplicate processed chunk identities: **0**

Gemma screen status:

- `ok`: **16,766**
- `unparsed`: **22**

All **22 / 22** Gemma-unparsed passages were successfully recovered by the
Qwen escalation pass.

Final finding types:

- capitalization: **194**
- scripture: **11,396**
- terminology: **12,608**
- translation: **13,544**
- wording: **4,863**

Final verified provenance classes:

- `in_chunk_exact`: **41,663**
- `in_chunk_normalized`: **900**
- `document_only`: **42**

Qwen escalation reasons:

- `unsupported_quote`: **804**
- `low_confidence_only`: **36**
- `json_unparsed`: **22**

Qwen escalation supervisor:

- 861 passages
- 5 batches
- wall time: **177.3 minutes**
- completion state: `work-complete`

Historical timing evidence from the original production run showed:

- historical Qwen passes with timing: **1,832**
- mean: **12.64 seconds**
- median: **11.94 seconds**
- historical total Qwen time: **6.43 hours**

The fresh Qwen phase completed in approximately **2 hours 57 minutes**.

## Historical reuse validation

Historical HIGH research:

`/home/liongateos/PCOG-Research-Archive/research/production`

Historical HIGH passages:

- **9,940**

Current and historical HIGH identity overlap:

- **7,611**

Of these:

- **1,643** were deliberately reprocessed in the fresh workload
- **5,968** were retained as historical reuse candidates

The 1,643 reprocessed passages correspond to material affected by the
extractor 1.0.0 → 1.1.0 transition, principally the corrected RTF path.

For the 5,968 historical reuse candidates:

- current chunks reconstructed: **5,968 / 5,968**
- historical passages validated: **5,968 / 5,968**
- historical verified findings checked: **15,893**
- findings still verified against current extraction: **15,893**
- findings no longer verified: **0**
- structural reuse check: **PASS**
- historical evidence recheck: **PASS**

Current quote verification of reused findings:

- in-chunk exact: **15,734**
- in-chunk normalized: **152**
- document-only exact: **7**

The 18 reuse candidates initially unresolved by current path were all resolved
by SHA-256 identity and matching extraction metadata:

- resolved by SHA-256: **18 / 18**
- still unresolved: **0**

Thus no additional Gemma/Qwen inference was required for the 5,968 historical
reuse passages.

## Extractor transition

Commit:

`016115e` — `M12: Patch RTF extraction skip logic to suppress metadata leaks`

changed:

- `EXTRACTOR_VERSION`: `1.0.0` → `1.1.0`
- RTF extraction logic

The non-RTF historical reuse population showed:

- metadata-identical candidates: **5,950**
- metadata-changed candidates: **0**
- 18 path/alias cases resolved by SHA-256

The changed historical RTF material was not reused blindly; the applicable
passages were covered by the fresh 2026 production run.

## Combined research candidate

Directory:

`/home/liongateos/PCOG-Research-Archive/research/full-high-research-combined-v1`

Combined artifact:

`combined_high_research.jsonl`

Manifest:

`manifest.json`

Verified contents:

- rows: **22,756**
- unique passage keys: **22,756**
- duplicate keys: **0**
- fresh passages: **16,788**
- historical validated-reuse passages: **5,968**
- documents represented: **8,221**
- verified findings: **58,498**
- quarantined findings retained in selected final passes: **149**
- malformed JSON lines: **0**

Combined artifact SHA-256:

`a9cc75dcc664e77811f646053b5c0748ad6a14907c7d84e2c2323abc93bda92a`

Manifest-recorded SHA-256 and independently recomputed SHA-256 matched exactly.

Final verification:

`COMBINED_ARTIFACT_VERIFICATION=PASS`

## Preservation checkpoint

Verified backup:

`/mnt/SanDisk-Backup/MASTER_BACKUPS/GD-Bible/gd-bible-full-high-research-combined-v1-20261013-123012.tgz`

Backup SHA-256:

`8f49af0d45b69132cac7f1c24644bef2c546703e911887e5b69aaea9ac8189c6`

Compressed size:

- approximately **21 MiB**

Backup archive readability:

`TGZ_READABILITY=PASS`

## Provenance and ownership rules

The combined artifact is derived research.

It does **not** replace or mutate:

- archive originals
- historical `research/production`
- fresh `full-archive-production-v1`
- `archive_search.db`
- `archive_research_sidecar.db`
- the pre-M12 recovery baseline
- the M12 reconciliation record

Each combined passage preserves its selected source generation and source
research-file provenance.

Selection policy:

- use the fresh 2026 result for every passage in the definite-fresh workload
- reuse historical results only for the independently revalidated 5,968
  current HIGH identities
- do not restore superseded historical RTF results over corrected fresh
  production results

The existing 19,340-row GD sidecar remains the protected approved M12 operating
baseline unless a later explicitly approved milestone replaces or supplements
it.

## Research classification note

The five model finding labels are **research finding types**, not document
subject topics:

- scripture
- terminology
- translation
- wording
- capitalization

They must remain distinct from any future CASE/GD subject-topic classification
layer.

## Closeout result

**PASS**

The complete current HIGH-priority GD research target is accounted for:

**22,756 / 22,756 passages**

with:

**58,498 verified research findings**

and no additional model rerun required for the validated historical reuse
population.
