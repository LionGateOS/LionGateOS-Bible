# GD-M06-A1 Stage A Output Schema Review

## Purpose

Freeze the Stage A enrichment output contract before scaling from the
3-finding smoke test to the 397-finding pilot.

This document defines GD-owned research enrichment fields.

It does not define CASE search, embeddings, vectors, ranking, or retrieval
fields.

## Smoke Validation

The Stage A smoke test validated:

- JSON parsing
- finding_uid preservation
- quote preservation
- anchor-aware handling
- schema validation
- valid anchor handling
- mismatch anchor handling
- out_of_bounds anchor handling

## GD-Owned Fields

### Identity and provenance

- finding_uid
  - Stable link back to the source finding.

- quote_echo
  - Exact preserved quote from the input finding.

- model_identity
  - Model used for enrichment.

- generation_timestamp
  - Time of enrichment generation.

### Translation research

- topic
  - Existing research category.

- research_observation
  - Human-readable research observation.

- translation_relevance
  - Whether the finding has translation relevance.

- translation_issue_type
  - Type of translation-related issue.

- word_or_phrase_under_review
  - Specific wording under examination.

- scripture_refs_raw
  - Original scripture reference input.

- scripture_refs_normalized
  - Structured scripture references.

- scripture_ref_confidence
  - Confidence in reference handling.

### Research notes

- terminology_note
- wording_note
- capitalization_note
- doctrinal_or_contextual_theme
- evidence_summary

These fields describe research context. They are not search ranking metadata.

### Verification and review

- evidence_strength
- quote_verification
- verification_status
- requires_original_language_check
- requires_human_review
- human_review_priority
- risk_flags

These fields help preserve uncertainty and review requirements.

## Explicitly Excluded From GD Output

The following belong to CASE, not GD:

- embeddings
- vector identifiers
- similarity scores
- retrieval scores
- ranking signals
- search phrases
- query expansion terms
- hybrid search metadata

## Ownership Boundary

GD:

- preserves evidence
- enriches research findings
- records translation observations

CASE:

- consumes approved artifacts
- builds retrieval indexes
- performs semantic/vector retrieval
- presents search results

## Approval Gate

Before the 397-finding Stage A run:

- schema approved
- smoke validation passed
- raw outputs preserved
- provenance preserved
- no CASE responsibilities added to GD enrichment
