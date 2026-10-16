# GD-M06-A1 Input Authority Freeze

## Purpose

This document freezes the approved text input authority for GD-M06-A1
enrichment pilot processing.

This is an evidence record only.

It does not modify archive originals, databases, extraction pipelines,
or research artifacts.

## Authoritative Text Source

GD-M06-A1 uses:

`archive_search.db`

Text source:

`document_text.content`

Identity mapping:

`documents.id = document_text.id`

## Database Identity

archive_search.db SHA-256:

`e95462fe671fb0a7bc1cded3807524540e733f9bb6a2f5ecd1313e741ccb3262`

archive_research_sidecar.db SHA-256:

`f8c20ede53efdd71be00a71681e00a3f3141524ec1c1399561ebbd395e770d7c`

## Existing Text Identity Fields

The authoritative database already provides:

- documents.file_sha256
- documents.text_sha256
- documents.doc_path
- document_text.content

CASE and GD consumers must use these identities rather than independently
re-extracting archive documents.

## Extractor Boundary

Current extractor marker:

`EXTRACTOR_VERSION = "1.1.0"`

No new extraction run is authorized by this freeze.

Future extractor changes require:
- new extractor identity,
- text hash comparison,
- anchor revalidation,
- explicit migration decision.

## Pilot Artifact Identity

Pilot sample list:

`docs/GD_M06_A1_PILOT_SAMPLE_LIST.md`

SHA-256:

`b69ac2250218300d6ae849a5864b07c022baa3cab39dedf967801ffecc9db9d6`

Pilot input:

`pilot_runs/gd_m06_a1/gd_m06_a1_pilot_input.jsonl`

SHA-256:

`a9568f46f5b3138707c2958886e7312aad3525e70ea923c4ec4585eaed17a594`

## Ownership Boundary

GD Bible owns:
- archive preservation,
- extraction lineage,
- research generation,
- enrichment outputs.

CASE owns:
- derived search indexes,
- embeddings,
- vector retrieval,
- ranking.

Both consume frozen source identities.

## Status

Approved input authority for GD-M06-A1 pilot preparation.
