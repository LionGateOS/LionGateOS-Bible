# GD-M06-A0.2 Baseline Freeze

## Purpose

This document freezes the approved GD Bible operating baseline before
Scripture Reference Normalization and Reference Assertion work.

This is an evidence record only. It does not modify production databases,
archive originals, or research artifacts.

## Frozen Sidecar Identity

Artifact:
`archive_research_sidecar.db`

SHA-256:
`f8c20ede53efdd71be00a71681e00a3f3141524ec1c1399561ebbd395e770d7c`

Size:
48,795,648 bytes

Research findings:
19,340

Documents:
2,060

Collections:
106

## Scripture Reference Population

Rows containing scripture_refs:
19,340

Null scripture_refs:
0

Empty scripture_refs:
0

Distinct scripture reference strings:
6,797

Status:
Model-attributed references remain unverified until GD-M06-A normalization
and assertion work is completed.

## Anchor Validation Baseline

Manifest:
`anchor_validity_manifest.json`

Manifest SHA-256:
`bbad07e41ede67edea585fd5d3c168ab4c1eabfc79c12d0bb04e851999a278f9`

Results:

- Total: 19,340
- Valid: 18,626
- Mismatch: 602
- Out of bounds: 112
- Invalid total: 714
- Affected documents: 56
- Unresolved documents: 0

## Engine Baseline

Git HEAD:

`d378c91982dc66d50492ffc461abd711c13ec21a`

Relevant components:

- archive_search_app.py
- app.py
- gd_research_extract.py
- gd_research_pipeline.py

## Known Constraints

- Archive originals remain immutable.
- Research sidecars remain derived artifacts.
- Scripture references are not authoritative until validated.
- Anchor validation is required for evidence consumers.
- Relationship graph work remains blocked until normalization quality is proven.

## Historical Enrichment Reference

Preserved preview artifacts:

- GD-Bible-Preview-1000-Complete-Review.md
- GD-Bible-Preview-1000-Reviewed.json

These are enrichment-layer artifacts and not authoritative source records.

