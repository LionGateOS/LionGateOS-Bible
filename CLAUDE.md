# GD Bible — Agent Session Instructions

**Repository:** `/home/liongateos/LionGateOS-Bible`
**This is NOT CASE.** CASE lives in `/home/liongateos/pcog-archive-collector`.

---

## Identity check — read this first

This repository is the **GD Bible (Grow Daily)** — Bible text, editorial
review, transformation rules, Scripture processing, and Bible-specific
research tooling.

The Church Archive Search Engine (CASE) is a **separate project** in a
separate repository. GD Bible research scripts are located in this
repository; CASE search/index/application files remain in
`pcog-archive-collector`. Do not treat them as interchangeable.

If a task description says "pcog-archive-collector" or "CASE" and you are
working in this repository, stop and confirm with the owner which repository
is the intended target.

---

## Current active state

**Branch:** `gd-research-recovery-20261016`
**HEAD:** `c4d20c1` (as of 2026-10-16)
**Read these documents first:**
1. `source/growdaily/docs/bible/editorial/GD_BIBLE_CURRENT_STATE.md` — GD research program state
2. `docs/CURRENT_STATE.md` — GD Bible text and editions state
3. `docs/handoffs/GD_BIBLE_PERMANENT_HANDOFF_2026-10-16.md` — full repository handoff and ownership rules

---

## Critical boundaries

**Do not modify without explicit owner approval:**
- `source/growdaily/assets/bible/en_kjv.json` — canonical standard KJV text
- `source/growdaily/assets/bible/kjv_modified.json` — canonical GD custom text
- `source/growdaily/assets/red_letters/` — Jesus speech map
- Any file in `editions/` — generated e-Sword outputs
- `source/growdaily/docs/bible/editorial/research/anchor_validity_manifest.json`
- Production review packets in `/home/liongateos/PCOG-Research-Archive/`

**Do not start any AI inference or GPU workload** from this repository.
GD-M02-C (bounded constrained extraction proof) is planning-only and is NOT
authorized for execution. See `source/growdaily/docs/bible/editorial/research/GD_M02C_ARCHITECTURE_PLAN.md`.

**Do not write to CASE databases:**
- `/home/liongateos/pcog-archive-collector/archive_search.db`
- `/home/liongateos/pcog-archive-collector/archive_research_sidecar.db`

**DeepSeek workspace rules:**
- Active GD Bible workspace: `GD BIBLE TRANSLATION`
- Active CASE workspace: `CASE — GPU SEARCH ENRICHMENT`
- Historical mixed workspace `ARCHIVE — GD BIBLE + CASE` is preserved for
  reference only — do not delete or modify its conversation history.

---

## Repository ownership summary

| Domain | Owner |
|---|---|
| Bible text (KJV + GD custom) | GD Bible (`LionGateOS-Bible`) |
| Transformation rules and editorial review | GD Bible |
| Scripture processing and normalization | GD Bible |
| Bible-specific research tooling (`gd_research_*.py`) | GD Bible |
| Archive collection, search, and indexing | CASE (`pcog-archive-collector`) |
| User library, archive enrichment, application UI | CASE |
| Shared interfaces (research export to CASE) | Requires explicit interface document and owner approval |

---

## Tasks requiring explicit owner approval before any action

- Any canonical Bible text edit (`en_kjv.json`, `kjv_modified.json`)
- Any production database write
- Starting GD-M02-C inference or any GPU workload
- Merging the recovery branch to main
- Pushing to GitHub
- Relocating any CASE component into this repository
- Relocating any GD Bible component into CASE
- Any change to the pre-M12 recovery artifacts
