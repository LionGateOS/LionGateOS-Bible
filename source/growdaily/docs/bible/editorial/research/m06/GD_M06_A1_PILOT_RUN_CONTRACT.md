# GD-M06-A1 Pilot Run Contract

## Purpose

This document defines the controlled execution contract for the GD-M06-A1
enrichment pilot.

The pilot validates the enrichment workflow before any archive-wide execution.

This is a derived research operation only.

It does not modify:
- archive originals
- canonical extraction databases
- production research artifacts

## Input Authority

Authoritative text input:

`archive_search.db`

Source:

`document_text.content`

Identity fields:

- documents.file_sha256
- documents.text_sha256
- documents.doc_path

Frozen input record:

`docs/GD_M06_A1_INPUT_AUTHORITY_FREEZE.md`

## Pilot Scope

Stage A pilot:

- controlled document subset
- approximately 250-400 findings
- includes:
  - large document stress case
  - multiple collections
  - multiple document formats
  - anchor mismatch examples

The full 37-document pilot is deferred until Stage A validation succeeds.

## Model Execution

Required settings:

- deterministic generation
- temperature: 0
- strict JSON output
- no silent repair of invalid output
- raw model output preserved

Initial local model:

To be selected after final hardware/model validation.

GPU allocation:

GD enrichment:
- assigned GPU

CASE:
- separate GPU for embedding/vector workloads

## Input Record

Each model request must preserve:

- finding_uid
- source document path
- source hash
- collection
- topic
- quote
- scripture_refs
- anchor status
- char_start
- char_end

## Required Output Schema

Each output object must contain:

- finding_uid
- observation
- normalized_scripture_refs
- confidence
- quote_verification
- model_identity
- generation_timestamp
- verification_status

## Validation Gates

Before accepting results:

1. JSON parsing success
2. Finding UID equality
3. No duplicate findings
4. No invented findings
5. Provenance completeness
6. Quote verification
7. Schema validation
8. Scripture reference validation where applicable
9. Human sample review

## Preservation Requirements

Every pilot run must preserve:

- input manifest
- input hash
- model identity
- model settings
- raw outputs
- parsed outputs
- validation results
- run timestamp

Raw outputs are immutable research evidence.

## Failure Conditions

Pilot fails if:

- provenance is missing
- findings cannot be traced back
- output schema is inconsistent
- unsupported claims exceed acceptance threshold
- validation cannot reproduce results

## Approval Gate

Archive-wide enrichment is blocked until:

- Stage A succeeds
- validation report exists
- comparison criteria are met
- human approval is recorded

