# GD-M06-A1 Smoke Test Manifest

## Purpose

Tiny pre-Stage-A input set for validating prompt/output behavior before any 397-finding run.

## Input Identity

- source: `pilot_runs/gd_m06_a1/stage_a/gd_m06_a1_stage_a_input.jsonl`
- smoke_input: `pilot_runs/gd_m06_a1/smoke/gd_m06_a1_smoke_input.jsonl`
- smoke_sha256: `8826088fe91479822e811debf15e66ca1d3ad87a54e5ef0215968d7319c13c82`
- finding_count: 3

## Selected Findings

| # | anchor_verdict | topic | finding_uid | doc_path |
|---:|---|---|---|---|
| 1 | valid | capitalization | `0ebd865d02d87b88c97370a104520cc5d7f95627e2eb98a44e98911121d1e1f6` | `PCG/Booklets/MDS_EN_0912.rtf` |
| 2 | mismatch | scripture | `1f33b34ae53d14c66cf55139729bd5cd5e959d6be6d9ebc5209f371e3f7ae8e6` | `WCG/Booklets (Other)/WCG Booklet - A Tale of Two Prophets (1978 Version).doc` |
| 3 | out_of_bounds | terminology | `4b32bbba7d9f52ef6501e127eff9c811a2b84e93e7d38d94ac50e8bd560bc1f7` | `WCG/Booklets (Other)/WCG Booklet - Where is God's True Church Today (1973 Version).doc` |

No LLM/GPU execution is authorized by this manifest.

## Repository Tracking Policy

The raw smoke JSONL input remains a local derived pilot artifact under `pilot_runs/`.

The committed record is this manifest, including the JSONL hash and selected finding identities.
