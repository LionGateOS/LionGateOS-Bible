# GD Bible Archive — M02-C Architecture Plan

> **HISTORICAL PLANNING DOCUMENT — NOT AUTHORIZED FOR EXECUTION**
>
> This document preserves a planning session that occurred on 2026-10-11.
> Nothing in this document constitutes authorization to run inference, write to
> any production database, or start any GPU workload. All implementation steps
> require explicit owner approval before execution.

---

## Provenance

- **Source session:** `f0246d21` (DeepSeek local session, DSH workspace
  `/home/liongateos/.dsh/workspaces/gd-bible-closeout/`)
- **Session title:** GD-M02-B Pipeline Audit
- **Session created:** 2026-10-11 21:00:25 UTC (Unix ms: 1791766825)
- **Session ended:** 2026-10-11 ~22:09 UTC (last turn seq=181)
- **Recovered to this repository:** 2026-10-16, Batch 4 session-content
  comparison
- **Recovery reason:** Session contained the only substantive M02-C
  architecture design; no equivalent document existed elsewhere in the
  recovered files.

The session covered two consecutive tasks: (1) a full M02-B pipeline audit,
and (2) M02-C architecture design. Both are preserved here. The audit
findings are the verified measurements on which the M02-C design rests;
neither should be read without the other.

---

## Part 1 — M02-B Pipeline Audit (verified measurements)

### Evidence base (what was actually verified in session)

| Check | Result |
|---|---|
| `gd_m02b_orchestrator.py` | 169 lines, reviewed in full |
| `m02b_test_sidecar.db` | 12,288 B, **3 pages, 0 rows**, mtime `18:03:44` = creation time |
| `m02b_quarantine.json` | **does not exist** — never written |
| `m02b_metrics.json` | **does not exist** — never written |
| Qwen2.5-32B-AWQ checkpoint | **19,328,804,864 B (19.33 GB), all 5 shards present, structurally valid** (header lengths + `data_offsets` sum exactly to file size; mid-file samples 100% non-zero) |
| `quantization_config` | `bits=4, group_size=128, zero_point=true, quant_method=awq, version="gemm"` |
| Runtime (used interpreter) | `/usr/bin/python3` + `~/.local/...`: torch **2.10.0**, transformers **5.19.0**, accelerate ✓, **gptqmodel 7.5.0** ✓, autoawq ✗ |
| Runtime (project venv) | torch 2.14.1, transformers 5.19.0, **accelerate ✗, gptqmodel ✗, autoawq ✗, vllm ✗** |
| GPUs | RTX 3090 (01:00.0) + **RTX 3090 Ti** (03:00.0), driver 580.173.02, both healthy |
| Shell history | 6+ launches, at least one `pkill`, one process observed alive at **1h05m**; last line = `pip install gptqmodel --break-system-packages && python3 gd_m02b_orchestrator.py` |

### Diagnosis

**M02-B never executed a single document to completion.** Stated by the
artifacts:

- 0 rows in the sidecar (a 3-page DB proves zero inserts ever committed,
  since even one row forces a 4th page)
- no quarantine file and no metrics file, both of which are written **only
  after** the loop finishes
- the process died, hung, or was killed **before or inside** the first
  iteration

The GPU work observed was **not** the 15-document extraction loop. The
arithmetic forecloses it:

> 15 documents × ≤512 new tokens = **7,680 output tokens**. Even at a
> pathological 5 tok/s that is ~26 minutes; at a normal AWQ 3090 rate
> (~35–50 tok/s) it is **~3 minutes**.

A multi-hour GPU-idle CPU-pegged process was doing something else. The
shell history supplies the missing half: an earlier process (PID 3792178,
started 17:29:40) was launched while the 19.33 GB checkpoint was still
downloading (shard symlinks land 17:11, 17:12, **17:33**, **17:35**; the
`.locks` dir settles 17:35). At 18:35 it was still alive at 1h06m. That
signature — GPU busy in bursts, then GPU idle with CPU pinned, no stdout,
no output file — is a **model-acquisition/engine-init stall, not inference**.

The script was rewritten at 18:03:42, a run started at 18:03:44 which
created the empty DB and then stopped. The DB mtime never advanced, so no
later run ever got as far as the DB — the final `gptqmodel` attempt died
before line 31.

**Net:** the milestone produced a valid empty database, a verified-complete
model download, and no experimental result.

### Root causes

**RC-1 — AWQ backend absent for every attempt (deterministic)**

transformers 5.19's `AwqQuantizer.validate_environment()` is a hard gate:

```python
if not is_gptqmodel_available():
    raise ImportError("Loading an AWQ quantized model requires gptqmodel.")
if not is_accelerate_available():
    raise ImportError("Loading an AWQ quantized model requires accelerate")
```

There is **no silent fp16 fallback**. The project venv is unusable for this
task — it has neither `gptqmodel` nor `accelerate`. `pip install gptqmodel
--break-system-packages` installs into the system interpreter's user-site
(`~/.local/lib/python3.12/site-packages`), *not* into `venv/`. It
"succeeded" while leaving the venv broken. Every run before that install
hit `ImportError` at `from_pretrained()`, after the DB was already created.
That exactly reproduces the observed end state: 12 KB empty DB, no
quarantine, no metrics, no output.

**RC-2 — Multi-hour stalls from non-inference phases**

Three mechanisms in order of evidential support:
1. **Checkpoint acquisition racing the run.** `from_pretrained` fetches/verifies ~19 GB of shards; CPU+IO bound, prints nothing to a non-TTY, leaves the GPU idle.
2. **Host memory pressure.** 61 GB RAM, 2 GB of swap presently in use, 43 GB in page cache. Materialising 19.33 GB of weights against a page cache already full of the same file invites reclaim/swap thrash — GPU idle waiting on the copy, CPU burning in the kernel.
3. **vLLM engine init in pre-pivot runs.** Engine construction (weight repacking) is CPU-heavy and slow for 32B on one card, and the multiprocess worker model was the original failure.

No stdout was captured anywhere, which is itself the finding. The exact
phase is not recoverable from surviving artifacts.

**RC-3 — The extraction contract is unsatisfiable (the deepest defect)**

The prompt made the model emit `char_start` / `char_end`, and the firewall
required byte-exact character offsets into the source. Language models
cannot do character-offset arithmetic. Even if this runner had completed
perfectly, the accepted-finding rate would have been approximately 0. The
empty DB is consistent with that prediction.

**RC-4 — The pivot discarded constrained decoding**

vLLM's `GuidedDecodingParams` / XGrammar was grammar-constrained decoding
— the mechanism that makes schema-valid JSON near-certain.
`gd_ai_pipeline.py` had already proven the schema compiles. The pivot to
raw Transformers replaced that with a JSON Schema pasted into the prompt
and a ` ```json ` fence-string heuristic. The deterministic firewall is a
verifier, not a generator: it can reject bad output but cannot produce good
output. Removing constrained decoding while keeping a strict verifier is
how you get 100% rejection.

**RC-5 — No chat template**

```python
inputs = tokenizer(prompt, return_tensors="pt")  # hand-rolled text
```

Qwen2.5-Instruct is a ChatML model. Without `apply_chat_template`, the
model runs in raw-completion mode: degraded instruction-following, weak EOS
pressure, no reliable termination.

**RC-6 — The harness cannot observe its own failures**

| Missing facility | Consequence |
|---|---|
| Progress logging / heartbeat | No way to know which phase ran for hours |
| Per-document timeout | One stall consumes the whole budget silently |
| Checkpointing / resumability | `os.remove(tmp_db)` at line 32 **guarantees** no resume is possible |
| Intermediate metrics | `metrics.json` and `quarantine.json` written **only after the loop** — any crash destroys 100% of the diagnostic record |
| Environment/version capture | No record of interpreter, package versions, or CLI args |

Additional latent bugs found in review:

- `metrics["docs_processed"] = len(docs)` set **before** the loop — it
  would report 15 even if zero documents ran
- `offset_in_chunk` populated with the **absolute** `char_start` (should
  be chunk-relative)
- `finding_uid = sha256(doc_path + start + end)` is **not
  content-derived**: two genuinely different findings at identical offsets
  collide and the second is silently swallowed as `IntegrityError`
- `failure_categories["source_mismatch"]` declared and **never incremented**

**RC-7 — The "controlled 15-document validation" was not controlled**

The selection query is `LIMIT 5` per extension with no seed, no
stratification, and no recorded manifest. It returned documents of
2,382–53,143 chars while the prompt is `content[:4000]` — up to 92% of a
document is silently discarded. German documents appeared despite the
language-exclusion intent, because the filter only matches `%_ger%` not
all German variants.

### Scale reality check — the 30,000 figure is wrong by ~8×

| Measure | Value |
|---|---|
| Documents in `archive_search.db` | **5,459** (5,439 with text) |
| Eligible under M02-B's filter | **3,766** |
| Eligible text volume | **99,358,774 chars (99.4 MB)** |
| Chunks @ 3,500 chars | **≈28,389** |
| Naive single-stream HF loop (~15 s/chunk) | **≈118 h** |
| vLLM continuous batching, one 3090 (est.) | **≈6–15 h** |
| Inventory preserved but **not yet indexed** | 21,452 files vs 5,459 indexed (~25%) |

The "30,000" is the **existing findings count** in the M09 sidecar, not a
document count. The real extraction workload is ~28.4k chunks — **a single
overnight run on vLLM**, not a multi-day campaign. *These figures are
planning envelopes, not measurements; no benchmark was run under this
read-only audit.*

### Constraint compliance and baseline hashes (verified in session)

Both required databases were read-only and unmodified by M02-B (mtimes
precede the 18:03 run).

```
archive_search.db               261,984,256 B   e95462fe671fb0a7bc1cded3807524540e733f9bb6a2f5ecd1313e741ccb3262
archive_research_sidecar.db      48,795,648 B   f8c20ede53efdd71be00a71681e00a3f3141524ec1c1399561ebbd395e770d7c
m02b_test_sidecar.db                 12,288 B   0 rows — disposable
```

**Documentation drift requiring reconciliation before planning scale:**

- `docs/CURRENT_STATE.md` records `archive_search.db` as `9b386a2f…` and
  the sidecar as `23a5723c…`; actual hashes are the above. The divergence
  is plausibly the authorised M12 RTF-extraction / ingestion work
  (16:23–16:24), not M02-B — but it must be confirmed and the doc refreshed.
- The doc claims **30,730** findings in the sidecar; the live DB contains
  **19,340** rows across **2,060** distinct documents (all
  `pipeline_verified=1`). A 37% gap needing an explicit explanation.
- The sidecar cannot be opened with `?mode=ro` alone (only with
  `&immutable=1`) — affects any future read-only consumer.

### What M02-B did buy (genuinely valuable)

1. **Model + runtime viability confirmed.** Qwen2.5-32B-AWQ is fully
   present (19.33 GB, 5/5 shards structurally valid) and fits comfortably
   in 24 GB. It does **not** need tensor parallelism.
2. **The AWQ dependency chain is now known exactly:** transformers 5.19
   requires `gptqmodel` ≥5.0 (7.5.0 present) **and** `accelerate`, in the
   *same* interpreter — and `--break-system-packages` does not reach the
   venv.
3. **A decisive negative result:** schema-in-prompt + strict offset
   verification + no chat template ⇒ ~0% acceptance. Do not build on this
   contract.
4. **M02-A remains a clean deterministic baseline** and is reusable as the
   regression gate: 15 rows inserted, 60 quarantined, 15 duplicates handled.
5. **Constraint compliance verified:** both production databases opened
   read-only; M02-B wrote nothing to production.

---

## Part 2 — M02-C Architecture Design

### Design objective

Prove, on a frozen 15-document set, that *constrained decoding +
derived-offset verification* yields a high, measured accept rate with zero
silent drops — under a run harness that cannot repeat the M02-B failure
mode. Nothing more.

**AUTHORIZATION STATUS: NOT AUTHORIZED. Design only. No implementation
steps may be taken without explicit owner approval.**

---

### 1. Exact implementation boundary

#### 1.1 New artifacts (all isolated)

| Artifact | Purpose |
|---|---|
| `gd_m02c_config.py` | Frozen constants: model id + revision, server URL, `chunk_chars`, max tokens, per-call/global timeouts, call ceiling, run root. Single source of truth. |
| `gd_m02c_client.py` | vLLM-backed HTTP client, structurally parallel to `gd_research_model.py` (allow-list, bounded attempts, backoff, hard timeout, workload check). **New sibling — does not replace the Ollama client.** |
| `gd_m02c_extract.py` | The client process: load frozen manifest → chunk → call → locate → assert → classify → insert → log → checkpoint. |
| `gd_m02c_schema.sql` | The verbatim existing 24-column `research_findings` DDL, so M02-A / M02-B / M02-C rows are schema-identical and directly comparable. |
| `m02c_manifest.json` | The frozen 15-document manifest: `doc_path`, `text_sha256`, `char_count`, `container`, `collection`. Committed **before** any inference. |
| `tests/test_m02c_deterministic.py` | Offline unit tests for the locator/assert contract, idempotency, and resume logic. **No model calls.** |

#### 1.2 Run-scoped write surface

```
m02c_runs/<UTC-stamp>/
  m02c_test_sidecar.db     isolated findings DB
  run_events.jsonl         append-only, flushed per event
  metrics.json             rewritten atomically after every chunk
  quarantine.json          rewritten atomically after every chunk
  run_state.json           resumable checkpoint
  server.log               captured from the vLLM process
  preflight.json           recorded pre-flight evidence (hashes, versions, results)
```

Nothing is written outside this directory.

#### 1.3 Explicitly frozen (read-only, must remain byte-identical)

- `archive_search.db` — opened `?mode=ro` only; never `ATTACH`ed
  read-write, never `VACUUM`ed, FTS5 never rebuilt.
- `archive_research_sidecar.db` and `archive_research_sidecar.db.m02_backup`.
- Everything under `/home/liongateos/PCOG-Research-Archive/research/production/`.
- `gd_string_assertion.py` — the frozen firewall. **Wrap, never edit.**
- `gd_research_verify.py`, `gd_research_pipeline.py`,
  `gd_research_chunk.py`, `gd_research_run.py`, `gd_research_model.py` —
  imported, not modified.
- `gd_m02a_orchestrator.py`, `m02a_test_sidecar.db`, `m02_quarantine.json`
  — the regression oracle.

#### 1.4 Process topology

**Two processes, never one.** The M02-B pivot abandoned vLLM because
`LLM(...)` inside the batch script fought its own worker tree. M02-C starts
vLLM as a **managed background job** exposing an OpenAI-compatible
endpoint, and runs the client separately over HTTP. The server may be
restarted without losing batch progress; the client may be killed without
losing server state.

Server spec (flag spellings to be confirmed against `vllm serve --help`
before any run):

- model `Qwen/Qwen2.5-32B-Instruct-AWQ`, pinned revision `5c7cb76a…`
- `--quantization awq` (real AWQ path; `gptqmodel 7.5.0` + `accelerate`
  are present in the user-site interpreter)
- structured-outputs backend pinned to **`xgrammar`**, not `auto`
- `--max-model-len 8192`, `--gpu-memory-utilization` set conservatively,
  `CUDA_VISIBLE_DEVICES=0`
- `--served-model-name` fixed and recorded; `--api-key` to prevent stray
  local clients

#### 1.5 Hard invariants

1. **No offsets from the model.** `ExtractionResponse` must contain no
   `char_start`/`char_end` fields.
2. **Every accepted row passed `verify_evidence_span`** with
   locator-derived offsets.
3. **No DB deletion.** Idempotent `INSERT OR IGNORE` on a content-derived
   UID.
4. **Nothing is written only at the end.** Events, metrics, quarantine and
   state are durable after every chunk.
5. **Bounded by program constants**, not by promises: 15 docs, ≤2
   chunks/doc, ≤30 model calls, 120 s per call, 45 min global, abort
   after 3 consecutive timeouts.
6. **`archive_search.db` is never opened in a writable mode.**

---

### 2. Required files/components to reuse

| Component | Reuse as | Why it is the right vehicle |
|---|---|---|
| `gd_string_assertion.verify_evidence_span` + error classes | **Final byte-exact gate** | Frozen, mandatory, already unit-tested. |
| `gd_research_verify.verify_quote`, `normalize_for_match` | Locator + agreement oracle | Does chunk-then-document `str.find` and returns offsets. |
| `gd_research_pipeline.locate_normalized` | **Offset derivation** | Offset-preserving NFKC/smart-quote/whitespace normalization that re-normalizes the slice it points at before returning an offset — a provable offset by construction. |
| `gd_research_pipeline.classify_finding` | Provenance + `source_match_type` | Returns `provenance`, `verified`, `in_chunk`, `ambiguous`, `occurrences`, `char_start`, `char_end` — and its docstring guarantees it agrees with `verify_quote`. |
| `gd_research_pipeline.chunk_key`, `options_fingerprint` | Idempotency / `finding_uid` seed | Content- and version-addressed across extractor, chunker, prompt, analysis, model, options. This is what makes resume real. |
| `gd_research_chunk.chunk_text` (`CHUNKER_VERSION`, `DEFAULT_CHUNK_CHARS=2400`, `c%04d` ids) | Chunking | Produces real `chunk_id`, `char_start`, `char_end` — replaces `content[:4000]`. |
| `gd_research_pipeline.MIN_EVIDENCE_CHARS = 8` | Trivial-match suppression | Policy already encoded: short normalized-only matches quarantine as ambiguous. |
| `gd_research_pipeline.check_gpu_environment`, `verify_gpu_resident` | GPU pre-flight | Already handles the `/dev/nvidia*`-masked-by-sandbox trap that nearly derailed the M02-B audit. |
| `gd_research_run.atomic_write_json`, `load_json`, `utcnow`, `sha256_text` | Durable state writes | Proven atomic-write helpers. |
| `gd_m02a_orchestrator.py` + `m02a_test_sidecar.db` + `m02_quarantine.json` | Regression oracle | 15 inserted / 60 quarantined / 15 duplicates is a real, executable baseline. |
| `gd_ai_pipeline.ExtractionResponse` | The guided-JSON schema | Already written; `.model_json_schema()` feeds XGrammar directly. |

#### 2.1 Precision note on the verification chain

`gd_research_verify.verify_quote` is **not** the right offset source: in
its document-level normalized branch it stores `haystack.find(needle)`,
which is a *normalized* index, not a source offset, and in the chunk-level
normalized branch it sets `char_start` without `char_end`.

The chain must be:

```
verify_quote            → agreement oracle / match classification only
locate_normalized       → authoritative source offsets (self-checking)
classify_finding        → provenance, occurrences, ambiguous
verify_evidence_span    → final byte-exact assertion on the derived offsets
```

`classify_finding` already routes through `locate_normalized`, so the
authoritative path exists. `verify_quote` is retained as a cross-check so
the two verifiers cannot silently diverge.

---

### 3. What existing GD pipeline components should be connected

The central M02-B finding: **a mature, resilient pipeline already existed
and was bypassed**. M02-C's wiring is the fix.

**Transport.** A new vLLM client mirroring `gd_research_model.py`'s
disciplines: explicit model allow-list (now the served name), refusal of
non-allow-listed names before any request, bounded attempts with backoff, a
hard per-request timeout, and a workload check adapted from `/api/ps` to
`/v1/models` plus GPU residency. The Ollama path stays intact as the
fallback.

**Chunking.** `gd_research_chunk.chunk_text` replaces M02-B's silent
`content[:4000]`. Long documents are covered rather than truncated,
coverage becomes measurable, and `chunk_id` becomes real.

**Verification.** The mandated chain in §2.1 becomes the *only* path to an
inserted row. Nothing bypasses it.

**State and resume.** Adopt `gd_research_run.py`'s schema-versioned state
discipline — re-pointed at the M02-C run directory instead of
`RESEARCH_DIR`. This turns "resumability" from an aspiration into a
property.

**Supervision semantics.** M02-C mirrors `gd_research_supervise.py`'s
discipline — a per-batch timeout, a declared call ceiling (the spirit of
`BULK_CEILING = 450`, reduced to M02-C's own ceiling of 30), and a
stop-on-no-progress rule — inside a single bounded batch. The full
supervisor is not run.

**Budget enforcement.** Declare M02-C's ceiling as a module constant and
assert on it before and after every call, so exceeding the budget is a
program property, not a promise.

**Sidecar contract.** Write the same 24-column `research_findings` schema,
populating: real `chunk_id`; **chunk-relative** `offset_in_chunk` (the
M02-B bug); `source_match_type` ∈ {`exact`, `whitespace_normalized`,
`punctuation_normalized`}; `occurrences`; `ambiguous`; `pipeline_verified
= 1` only after `verify_evidence_span`; `pass_type = "M02C_vLLM_XGrammar"`;
`provenance = "vLLM_<model>@<revision>"`; and `raw_finding_json` for full
auditability.

**Observability.** `run_events.jsonl` with a heartbeat per phase
(`preflight_*`, `server_ready`, `doc_start`, `chunk_start`, `chunk_done`,
`chunk_timeout`, `doc_done`, `run_end`), flushed per event. This is the
single change that would have made the M02-B audit a five-minute job.

---

### 4. Pre-flight checks before any inference

**P0 — environment and integrity (no GPU, no model)**

1. Record SHA-256 of `archive_search.db`, `archive_research_sidecar.db`,
   and `gd_string_assertion.py` as the frozen baseline. Write to
   `preflight.json`.
2. **Resolve the interpreter split explicitly.** The client and the server
   must both see `torch`, `transformers`, `vllm`, `xgrammar`, `accelerate`,
   `gptqmodel`. Pin one interpreter, record its path and every version.
   *This is the RC-1 trap that silently voids the whole run.*
3. Confirm `xgrammar` imports and that the configured backend resolves to
   `xgrammar` — not silently to `auto`.
4. Confirm the checkpoint revision equals `5c7cb76a…`, all 5 shards
   present, and each shard's `header_len + max(data_offsets) == file size`
   (19,328,804,864 B).
5. Confirm `archive_search.db` opens `?mode=ro`, and that the frozen
   manifest resolves to exactly 15 documents with matching `text_sha256`.

**P1 — contract and schema (no GPU)**

6. Compile `ExtractionResponse.model_json_schema()` through XGrammar
   (extending `gd_ai_pipeline`'s existing check). Assert the schema
   contains **no** offset fields.
7. Offline locator/assert tests: exact match; normalized match;
   multi-occurrence → ambiguous; not-found → quarantine;
   locator-derived offsets accepted by `verify_evidence_span`;
   mutated/shifted/fabricated quotes rejected.
8. Re-run the M02-A oracle; require 15 inserted / 60 quarantined unchanged.

**P2 — server bring-up (GPU, no batch inference)**

9. Launch vLLM as a managed background job; capture `server.log`; record
   measured startup seconds and steady VRAM.
10. Confirm the exact structured-outputs flag spelling from `vllm serve
    --help` before depending on it.
11. Health: `GET /v1/models` returns the served name; `/health` returns 200.
12. **Throughput micro-benchmark:** one document, one chunk, with
    `torch.cuda.synchronize()` around timing. Record prefill tok/s, decode
    tok/s, peak VRAM, wall time. **This replaces every estimate in the M02-B
    audit with a measurement, and the batch does not start if it fails.**

**P3 — dry run and kill test**

13. One document end-to-end with the 120 s timeout and event logging live;
    confirm `metrics.json`, `quarantine.json` and `run_state.json` are
    durable *during* the run, not only at the end.
14. **Kill `-9` the client mid-run**, then re-invoke and confirm it resumes
    without duplication and without loss. This is the decisive proof that
    the M02-B failure mode cannot recur.
15. Confirm `inserted + quarantined == emitted`, and that the run wrote
    nothing outside its run directory.

---

### 5. Success criteria

#### Must-pass (all eleven)

| # | Criterion |
|---|---|
| C1 | **Schema validity ≥ 90%** of responses — proves XGrammar is genuinely engaged. |
| C2 | **≥ 12 of 15 documents** yield ≥ 1 firewall-accepted finding (≥ 80%). |
| C3 | **`inserted + quarantined == emitted`** — zero silent drops across the whole run. |
| C4 | **100% of inserted rows carry locator-derived offsets**, each re-asserted by `verify_evidence_span`; zero model-supplied offsets anywhere in schema, DB, or logs. |
| C5 | `source_match_type`, `occurrences`, `ambiguous`, and chunk-relative `offset_in_chunk` populated from classification — no hard-coded `"exact"`, no absolute offset in the chunk column. |
| C6 | **Negative control:** mutated, shifted, out-of-bounds, and fabricated quotes are rejected and quarantined **with a reason**. |
| C7 | **M02-A regression unchanged:** 15 inserted / 60 quarantined / 15 duplicates handled. |
| C8 | **Bounds held:** ≤ 15 docs, ≤ 30 model calls, p95 call ≤ 120 s, total ≤ 45 min, ≤ 2 chunks/doc. |
| C9 | **Resumability proven:** the P3 kill-and-resume run completes remaining documents with no duplication, and completed chunks become `INSERT OR IGNORE` no-ops. |
| C10 | **`archive_search.db` and `archive_research_sidecar.db` byte-identical** before and after; nothing written outside the run directory. |
| C11 | **`metrics.json` reconciles** with `run_events.jsonl`: `docs_processed == docs_attempted`, per-phase timings, token counts, and no heartbeat gap > 60 s. |

#### Must-not-happen (any occurrence is an automatic fail)

- In-process `LLM(...)` construction.
- Deletion of any existing database.
- Any write to a production database or to `PCOG-Research-Archive/research/production/`.
- An unlogged gap exceeding the heartbeat cadence.
- A run that terminates without `metrics.json`.

#### Scale-out gate (explicit non-goal for M02-C)

M02-C **does not authorize** the corpus run. Promotion requires C1–C11
passing *and* a measured throughput projection from P2. Two scoping facts
must also be settled before any large run:

- The real workload is **3,766 eligible documents / ~28,389 chunks / 99.4
  MB** — an overnight vLLM run, not a multi-day campaign.
- `archive_search.db` indexes **5,459** documents while the preserved
  archive holds **21,452** — ingestion, not inference, is the larger gap.

---

### 6. Open decisions requiring owner approval before P0

1. **Interpreter policy** — install `gptqmodel` + `accelerate` into
   `venv/`, or standardize on `/usr/bin/python3` with `~/.local`? Pin
   exactly one; record it.
2. **Corpus scope** — is M02-C strictly the 15-document proof, or should
   it be a 100-document calibration for a better throughput estimate?
3. **Inventory gap** — resolve 5,459 indexed vs 21,452 preserved before
   setting any production target.
4. **Second GPU** — leave the 3090 Ti idle for M02-C, or plan a second
   server as a data-parallel worker once the single-GPU path is proven?
5. **Manifest selection rule** — confirm the deterministic selection
   (seeded stratified sample, English-only by explicit suffix allow-list)
   before freezing the manifest.

---

## Architectural diagram (proposed)

```
archive_search.db ──(read-only)──► chunker ──► work queue (JSONL, resumable)
                                                   │
                    ┌──────────────────────────────┴───────────────────┐
                    │  vLLM server #1  (RTX 3090,  :8000)               │
                    │  --quantization awq                                │
                    │  --guided-decoding-backend xgrammar                │
                    │  CUDA_VISIBLE_DEVICES=0                            │
                    └──────────────────────────────┬───────────────────┘
                                                   │  guided_json (ExtractionResponse schema)
                    gd_m02c_client.py (HTTP, retries, hard timeouts)
                                                   │
                    verify_quote ──► locate_normalized ──► classify_finding
                                                   │
                                        verify_evidence_span()  ◄── MANDATORY GATE
                                                   │
                    run_events.jsonl + metrics.json + run_state.json  (atomic, per-chunk)
                                                   │
                    m02c_test_sidecar.db  (isolated)   ── never production
```

---

*End of document. Nothing in this document authorizes execution. All
implementation and inference steps require explicit owner approval.*
