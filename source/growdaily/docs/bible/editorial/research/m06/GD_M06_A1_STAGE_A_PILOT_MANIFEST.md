# GD-M06-A1 Stage A Pilot Manifest

## Purpose

Stage A is the first bounded sub-pilot before any full pilot run.

## Identity

- source_input: `pilot_runs/gd_m06_a1/gd_m06_a1_pilot_input.jsonl`
- stage_a_input: `pilot_runs/gd_m06_a1/stage_a/gd_m06_a1_stage_a_input.jsonl`
- stage_a_sha256: `474c500a1df8bb774efa484cf94cbad493cce38348dd620e801376cd48afe5b9`
- document_count: 7
- finding_count: 397

## Selected Documents

| # | Findings | Reason | Collection | Document | Anchor verdicts | Topics |
|---:|---:|---|---|---|---|---|
| 1 | 60 | anchor-failure coverage | WCG/Booklets (Other) | `WCG/Booklets (Other)/WCG Booklet - A Tale of Two Prophets (1978 Version).doc` | mismatch:60 | scripture, terminology, translation, wording |
| 2 | 68 | anchor-failure coverage | WCG/Booklets (Other) | `WCG/Booklets (Other)/WCG Booklet - Where is God's True Church Today (1973 Version).doc` | mismatch:64, out_of_bounds:4 | scripture, terminology, translation, wording |
| 3 | 130 | bounded RTF stress case | PCG/Booklets | `PCG/Booklets/MDS_EN_0912.rtf` | valid:130 | capitalization, scripture, terminology, translation, wording |
| 4 | 43 | transcript coverage | WCG/HWA Transcripts/Sermon | `WCG/HWA Transcripts/Sermon/Sermon Transcript (HWA) - 1983 04 - Spiritual Health Checkup.doc` | valid:43 | capitalization, scripture, terminology, translation, wording |
| 5 | 45 | Bible correspondence course coverage | WCG/Bible Corresp Courses/32 | `WCG/Bible Corresp Courses/32/Ambassador College BCC (32 Version) - L 04 - The Coming Utopia -- Wonderful World Tomorrow .doc` | valid:45 | capitalization, scripture, terminology, translation, wording |
| 6 | 10 | KOD transcript coverage | PCG/KOD transcripts/2021 | `PCG/KOD transcripts/2021/KOD21-28AtTheEnd,ItShallSpeak.doc` | valid:10 | capitalization, scripture, terminology, translation, wording |
| 7 | 41 | balanced filler | WCG/HWA Transcripts/BS | `WCG/HWA Transcripts/BS/Bible Study Transcript (HWA) - 1981 09 11 - The Sabbath.doc` | valid:41 | capitalization, scripture, terminology, translation, wording |

## Topic Counts

- terminology: 139
- scripture: 133
- translation: 70
- wording: 48
- capitalization: 7

## Anchor Verdict Counts

- valid: 269
- mismatch: 124
- out_of_bounds: 4

## Gate

No LLM/GPU execution is authorized by this manifest.

## Repository Tracking Policy

The raw Stage A JSONL input remains a local derived pilot artifact under `pilot_runs/`.

The committed record is this manifest, including the JSONL hash and selection summary.
