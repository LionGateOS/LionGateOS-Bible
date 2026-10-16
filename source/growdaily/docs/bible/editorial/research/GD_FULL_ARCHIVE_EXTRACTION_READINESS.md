# GD Full Archive Extraction Readiness Report

Generated: 2026-10-12T06:28:54.444847+00:00

## Scope

This report summarizes the bounded proof for creating a new derived
full-corpus-style archive search database.

The complete 21,469-file extraction has not been run.

## Boundaries Preserved

- archive_search.db was not modified.
- archive_research_sidecar.db was not modified.
- preserved archive originals were not modified.
- GD-M06-A1 pilot artifacts were not modified.
- CASE vector/index artifacts were not modified.
- No embeddings, vector generation, LLM enrichment, or GPU workload ran.

## Proof Artifact

- proof_db: `/home/liongateos/pcog-archive-collector/archive_search_full_proof.db`
- proof_db_sha256: `90766e26eb9cbd637c84d7f430dbf7c57483aef149437fcc1401dbeab86a2baf`
- proof_report_json: `proof_reports/archive_search_full_proof_20261012T061932Z.json`

## Extractor Identity

- extractor_path: `/home/liongateos/pcog-archive-collector/gd_research_extract.py`
- extractor_sha256: `cf73e35f7a40cffbddb8d323880551676a64557ed590ac669207d325ddb9b916`
- EXTRACTOR_VERSION: `1.1.0`

## Production DB Safety

- production_dbs_unchanged: `True`
- `/home/liongateos/pcog-archive-collector/archive_research_sidecar.db`
  - before: `f8c20ede53efdd71be00a71681e00a3f3141524ec1c1399561ebbd395e770d7c`
  - after:  `f8c20ede53efdd71be00a71681e00a3f3141524ec1c1399561ebbd395e770d7c`
- `/home/liongateos/pcog-archive-collector/archive_search.db`
  - before: `e95462fe671fb0a7bc1cded3807524540e733f9bb6a2f5ecd1313e741ccb3262`
  - after:  `e95462fe671fb0a7bc1cded3807524540e733f9bb6a2f5ecd1313e741ccb3262`

Production SQLite side artifacts:
- `/home/liongateos/pcog-archive-collector/archive_research_sidecar.db` wal=False shm=False journal=False
- `/home/liongateos/pcog-archive-collector/archive_search.db` wal=False shm=False journal=False

- source_files_unchanged: `True`

## Proof Counts

- documents: `12`
- document_text: `12`
- documents_fts: `12`
- status_counts: `{'success': 12}`

## Sample Results

| # | Status | Container | Chars | Reason | Path |
|---:|---|---|---:|---|---|
| 1 | success | RTF | 9090 | normal RTF | `GRF Letters/2000/CoworkerDec2000.rtf` |
| 2 | success | OLE2 | 9905 | OLE2 Word document | `GRF Letters/1999/3 Sept 99.doc` |
| 3 | success | ZIP | 31201 | DOCX/ZIP document | `GRF Letters/2010/083010_1009 In Prophecy.docx` |
| 4 | success | OLE2 | 216057 | Non Church document | `Non Church/King James Bible (KJV)/1. OT/KJV 01 Genesis.doc` |
| 5 | success | OLE2 | 18532 | unsupported/problem PDF | `PCG/KOD transcripts/2019/KOD 19-35 lit.pdf` |
| 6 | success | RTF | 15271 | unsupported/problem no-extension file | `PCG/Philadelphia Trumpet/2007/PT0607 EU Anniversary--Crisis Before Solution` |
| 7 | success | RTF | 45435 | filename variant A | `PCG/ACBCC/BCC04_EN/Old reprints/BCC04_EN A Wonderful World Tomorrow .rtf` |
| 8 | success | RTF | 34241 | filename variant B | `PCG/ACBCC/BCC04_EN/Old reprints/BCC04_EN A Wonderful World Tomorrow  .rtf` |
| 9 | success | RTF | 2922 | whitespace-normalized filename variant A | `PCG/ACBCC/BCCT8_EN/BCCT8_EN  an open letter from the staff.rtf` |
| 10 | success | RTF | 31478 | whitespace-normalized filename variant B | `PCG/ACBCC/BCCT8_EN/BCCT8_EN an open letter from the staff.rtf` |
| 11 | success | OLE2 | 46258 | duplicate-text/source-record pair A | `WCG/Bible Corresp Courses/32/Ambassador College BCC (32 Version) - L 19 - What and Why the Church .doc` |
| 12 | success | OLE2 | 46258 | duplicate-text/source-record pair B | `WCG/Bible Corresp Courses/58/Ambassador College BCC (58 Version) - L 32 - Mark of the Beast to be Enforced Again.doc` |

## Duplicate and Variant Identity

The proof preserved each selected source as its own record.
Filename variants were not collapsed.
Duplicate-text/source-record pairs were not collapsed.

Duplicate text groups:
- `f899d1b40b5cee73b8999b453a0d42ee9425f67bbf7bfbd8c6f9ac5034b3fce0` count=2
  - `WCG/Bible Corresp Courses/32/Ambassador College BCC (32 Version) - L 19 - What and Why the Church .doc`
  - `WCG/Bible Corresp Courses/58/Ambassador College BCC (58 Version) - L 32 - Mark of the Beast to be Enforced Again.doc`

## Negative-Path Verification

- path: `PCG/Royal Vision/2015/Archive.zip`
- sha256: `5f38af61ab467cb7f40ce778f0d7cd05f569996039b1432673879baba248fd92`
- detected_container: `ZIP`
- result: `MalformedDocument`
- error: `ZIP container has no word/document.xml`

Interpretation: the extractor returns an explicit failure reason for a
problematic archive file instead of silently dropping it.

## Runtime

- proof_extraction_seconds: `0.054594392073340714`
- proof_db_fts_seconds: `0.0046939910389482975`
- proof_total_seconds: `0.06924497603904456`
- linear_full_estimate_minutes: `2.064750542475344`

Operational estimate for the full 21,469-file build:

- likely: under 10 minutes
- conservative allowance: 30 minutes
- stop and inspect if runtime exceeds 60 minutes without progress output

## Schema Sufficiency

The current schema is sufficient for the full-corpus artifact:

- doc_path
- filename
- collection
- source_url
- file_sha256
- text_sha256
- container
- char_count
- status
- error
- document_text
- documents_fts

Extractor SHA-256 and EXTRACTOR_VERSION should be stored in the build
manifest/report, not repeated on every row.

## Recommendation

Do not run the old ingest_full_corpus.py unchanged.

Proceed with a bounded full-build implementation path that:

- requires explicit output path `archive_search_full.db`
- refuses to write `archive_search.db`
- refuses to write `archive_research_sidecar.db`
- preserves one row per source file
- keeps unsupported/error rows visible
- writes final JSON/MD build reports
- verifies production DB before/after hashes

## Current Decision

Ready for a bounded full-build implementation step.

Not authorized here:

- embeddings
- CASE vector generation
- replacing any existing database
- committing or pushing
- running the complete full build without explicit owner approval
