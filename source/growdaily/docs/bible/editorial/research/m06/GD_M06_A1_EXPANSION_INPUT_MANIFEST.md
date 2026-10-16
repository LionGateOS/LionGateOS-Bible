# GD-M06-A1 Expansion Input Manifest

Generated: 2026-10-12T07:11:26.739207+00:00

## Purpose

Prepare the deterministic Phase 2 enrichment input population.

This manifest does not authorize model execution.
Phase 2 execution remains gated on successful Stage A pilot validation.

## Inputs

- research sidecar: `archive_research_sidecar.db`
- research sidecar SHA-256: `f8c20ede53efdd71be00a71681e00a3f3141524ec1c1399561ebbd395e770d7c`
- anchor manifest: `anchor_validity_manifest.json`
- anchor manifest SHA-256: `bbad07e41ede67edea585fd5d3c168ab4c1eabfc79c12d0bb04e851999a278f9`
- Stage A pilot input: `pilot_runs/gd_m06_a1/stage_a/gd_m06_a1_stage_a_input.jsonl`
- Stage A pilot SHA-256: `474c500a1df8bb774efa484cf94cbad493cce38348dd620e801376cd48afe5b9`

## Expansion Queue

- path: `pilot_runs/gd_m06_a1/expansion/gd_m06_a1_expansion_input.jsonl`
- SHA-256: `6569f2c87c9584c29cebf5260080ad578e52e39c4dc12ac61df36e076642e3d8`
- findings: 19340
- distinct documents: 2060
- unique finding UIDs: 19340
- Stage A records verified as exact subset: 397
- Stage A record mismatches: 0

## Anchor Verdicts

- valid: 18626
- mismatch: 602
- out_of_bounds: 112

## Topics

- translation: 5950
- terminology: 5810
- scripture: 5158
- wording: 2327
- capitalization: 95

## Safety Boundary

- Archive originals are untouched.
- `archive_research_sidecar.db` is read-only.
- No existing research finding is overwritten.
- No model or GPU was invoked.
- No CASE search, embedding, vector, ranking, or UI artifact is produced.
- Expansion model execution requires successful Stage A pilot validation first.
