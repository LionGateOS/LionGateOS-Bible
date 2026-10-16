# GD-M06-A1 Pilot Design

## Purpose

Define a controlled pilot for GD Bible enrichment processing.

The pilot validates the enrichment design before archive-wide execution.

## Pilot Objective

Validate the GD-M06-A1 enrichment design and schema on a small, controlled
sample so that archive-wide execution proceeds only on demonstrated quality.

The pilot validates:

- extraction quality
- schema compatibility
- provenance preservation
- duplicate handling
- model usefulness

The pilot produces derived pilot artifacts only. It writes no production
databases and modifies no archive originals.

## Sample Selection Method

The sample is drawn from the approved GD-M06-A operating baseline
(19,340 findings across 2,060 documents in 106 collections — see
`docs/GD_M06_A0_2_BASELINE_FREEZE.md`):

- Stratify by collection: documents drawn from multiple collections,
  not a single collection.
- Stratify by extraction source/type: include RTF-container documents
  (extractor v1.1.0 text) and other text classes present in the baseline.
- Include anchor-status strata: predominantly anchor-valid documents, plus a
  small set drawn from the 56 documents holding mismatch or out-of-bounds
  findings, to exercise failure paths.
- Fixed size decided before selection (on the order of 25-40 documents,
  roughly 1-2% of the baseline).
- Selection uses a recorded, reproducible rule (collection + document
  identifier); the frozen sample list is recorded before processing begins.

No full archive processing.

## Model Comparison Method

- Run the identical sample and prompts through each candidate model:
  local GPU model and stronger cloud model.
- Deterministic checks run before AI interpretation in every run.
- Raw outputs are preserved separately per model and compared on:
  - agreement rate on scripture references and classifications
  - useful discoveries beyond deterministic checks
  - false positives and unsupported claims
  - schema compliance
  - provenance completeness

Comparison results are recorded side by side in a pilot report.

## Provenance Requirements

Every pilot output must carry the core provenance fields defined in
`docs/GD_M06_A1_ENRICHMENT_SCHEMA.md`:

- finding_uid, source document, source hash, quote, collection,
  extraction source
- model used and generated timestamp for every AI observation
- verification status on every observation

Raw model output is never discarded, never silently repaired, and never
overwrites existing research findings.

## Success Criteria

Pilot succeeds if:

- outputs preserve source traceability
- schema fields are populated correctly
- results are useful for human review
- verification workflow is practical

## Failure Criteria

Stop and revise if:

- provenance is lost
- output cannot be verified
- models produce excessive unsupported claims
- duplicate enrichment is created

## Approval Gate

Full archive processing — including GPU processing — is authorized only when:

- the pilot has completed on the recorded sample
- a pilot report records results against every success and failure criterion
- all success criteria are met and no failure criterion triggered
- Phase 2 (Expansion) begins only after a recorded human approval

Without recorded approval, processing stops at the pilot boundary.

## Current Status

Planning only.

