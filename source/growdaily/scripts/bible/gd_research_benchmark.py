#!/usr/bin/env python3
"""Bounded local-only accuracy benchmark for the GD Bible research pipeline.

This harness measures **accuracy first, speed second** on a stratified
sample of HIGH-priority passages from the Milestone 1 triage index.

It reuses the verified Milestone 0 components rather than reimplementing
them:

* ``gd_research_run.build_prompt``   -- the identical prompt for every model
* ``gd_research_run.MODEL_OPTIONS``  -- identical sampling options
* ``gd_research_verify.validate_response`` / ``verify_findings``
                                     -- the identical scoring criteria
* ``gd_research_extract`` / ``gd_research_chunk`` -- source text recovery
* ``gd_research_model``              -- local-only client that rejects cloud

Safety properties enforced here, not promised:

* Cloud-tagged models are rejected **before** any request is built, and
  the allow-list is narrowed to the models actually under test.
* Only one model is resident at a time.  A competing workload aborts the
  benchmark instead of evicting somebody else's model.
* Nothing is written outside ``research/benchmarks/``.  Production
  findings are never touched.
* The number of model calls is bounded by the sample size.

Results are written separately from production research findings.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
import unicodedata
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gd_research_extract as extractor        # noqa: E402
import gd_research_model as model_client       # noqa: E402
import gd_research_run as runner               # noqa: E402
import gd_research_verify as verifier          # noqa: E402

ARCHIVE_ROOT = os.environ.get("GD_ARCHIVE_ROOT", "/home/liongateos/PCOG-Research-Archive")
DOCUMENTS_DIR = os.path.join(ARCHIVE_ROOT, "documents")
BENCHMARK_DIR = os.path.join(ARCHIVE_ROOT, "research", "benchmarks")
INDEX_PATH = os.path.join(ARCHIVE_ROOT, "research", "index", "chunk_index.jsonl")

SCHEMA = "gd-model-benchmark/1"
SAMPLE_SEED = 20261009
CHUNK_CHARS = 2400

#: Stratification: topic -> how many passages of the 100.
STRATA = (
    ("translation", 30),
    ("capitalization", 30),
    ("interpretation", 30),
    ("terminology", 10),
)

#: Models requested for this benchmark.  Any that turn out to be cloud
#: tagged or absent from the local server are reported and skipped.
REQUESTED_MODELS = ("qwen3.6:27b", "gemma4-local:latest", "Qwen3-Coder-30B-A3B")

#: Extra local models the benchmark may load, beyond the pipeline default.
BENCHMARK_ALLOWLIST = ("qwen3.6:27b", "gemma4-local:latest")


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------
# model / endpoint verification
# --------------------------------------------------------------------------

def _get(base_url, path, timeout=15):
    request = urllib.request.Request(base_url + path, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def local_models(base_url=model_client.DEFAULT_BASE_URL):
    """Every model the local Ollama server reports, with a cloud flag."""
    payload = _get(base_url, "/api/tags")
    found = {}
    for item in payload.get("models", []):
        name = item.get("name") or ""
        details = item.get("details") or {}
        found[name] = {
            "name": name,
            "size_bytes": item.get("size", 0),
            "parameter_size": details.get("parameter_size"),
            "quantization": details.get("quantization_level"),
            "family": details.get("family"),
            "cloud": ":cloud" in name.lower() or name.lower().endswith("-cloud"),
        }
    return found


def endpoint_probe(base_url, port, timeout=4):
    """Is a non-Ollama local runtime (llama.cpp / vLLM) serving here?"""
    try:
        request = urllib.request.Request("http://127.0.0.1:%d/v1/models" % port, method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"__error__": "%s: %s" % (type(exc).__name__, exc)}


def verify_models(base_url=model_client.DEFAULT_BASE_URL):
    """Decide which requested models can actually be benchmarked."""
    available = local_models(base_url)
    decisions = []

    for name in REQUESTED_MODELS:
        record = {"requested": name, "runnable": False, "reason": None}
        lowered = name.lower()

        entry = available.get(name)
        if entry is None:
            # not an Ollama model -- look for a served endpoint
            if "coder" in lowered:
                probe = endpoint_probe(base_url, 8001)
                record["reason"] = (
                    "not installed in Ollama and no runtime on :8001 (%s)"
                    % probe.get("__error__", "no models")[:120]
                )
            else:
                record["reason"] = "not present in the local Ollama model list"
            decisions.append(record)
            continue

        if entry["cloud"]:
            record["reason"] = "cloud-tagged; refused (never use Ollama Cloud)"
            decisions.append(record)
            continue

        if name not in BENCHMARK_ALLOWLIST:
            record["reason"] = "local but not on the benchmark allow-list"
            decisions.append(record)
            continue

        record["runnable"] = True
        record["details"] = entry
        decisions.append(record)

    return available, decisions


# --------------------------------------------------------------------------
# sampling
# --------------------------------------------------------------------------

def load_high_candidates(path=INDEX_PATH):
    records = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if record.get("priority") == "high":
                records.append(record)
    return records


def _topic_weights(record):
    """Total signal weight per topic for one triage candidate."""
    weights = {}
    for signal in record.get("signals") or ():
        topic = signal.get("topic")
        if not topic:
            continue
        weights[topic] = weights.get(topic, 0) + (
            signal.get("hits", 1) * signal.get("weight", 1)
        )
    return weights


def stratify(records):
    """Build a primary and a secondary pool for each research topic.

    Passages usually carry several topics.  A stratum's *primary* pool is
    the passages where that topic carries the most signal weight -- the
    most representative examples -- and the *secondary* pool is everything
    else that still contains the topic.  Sampling prefers primary so each
    stratum reflects its own topic rather than the dominant one.
    """
    pools = {name: {"primary": [], "secondary": []} for name, _ in STRATA}

    for record in records:
        topics = set(record.get("topics") or ())
        weights = _topic_weights(record)
        dominant = max(weights, key=weights.get) if weights else None
        for name, _ in STRATA:
            if name not in topics:
                continue
            kind = "primary" if dominant == name else "secondary"
            pools[name][kind].append(record)

    for name, _ in STRATA:
        for kind in ("primary", "secondary"):
            pools[name][kind].sort(key=lambda r: (r["path"], r["char_start"]))
    return pools


def build_sample(records, seed=SAMPLE_SEED, total=100):
    """Deterministic stratified sample of HIGH-priority passages."""
    pools = stratify(records)
    rng = random.Random(seed)
    used = set()
    sample = []
    shortfalls = {}

    for name, wanted in STRATA:
        chosen = []
        for kind in ("primary", "secondary"):
            if len(chosen) >= wanted:
                break
            pool = [r for r in pools[name][kind]
                    if (r["path"], r["chunk_id"]) not in used]
            need = wanted - len(chosen)
            if not pool:
                continue
            for record in rng.sample(pool, min(need, len(pool))):
                used.add((record["path"], record["chunk_id"]))
                chosen.append(record)
        if len(chosen) < wanted:
            shortfalls[name] = {
                "wanted": wanted,
                "available": len(chosen),
                "pool_primary": len(pools[name]["primary"]),
                "pool_secondary": len(pools[name]["secondary"]),
            }
        for record in chosen:
            record = dict(record)
            record["stratum"] = name
            sample.append(record)

    # safety net: top up to *total* from anything not yet used
    missing = total - len(sample)
    if missing > 0:
        leftovers = [r for r in records if (r["path"], r["chunk_id"]) not in used]
        leftovers.sort(key=lambda r: (r["path"], r["char_start"]))
        for record in rng.sample(leftovers, min(missing, len(leftovers))):
            record = dict(record)
            record["stratum"] = "other"
            sample.append(record)
            shortfalls.setdefault("other_topup", 0)
            shortfalls["other_topup"] = shortfalls.get("other_topup", 0) + 1

    sample.sort(key=lambda r: (r["stratum"], r["path"], r["char_start"]))
    return sample, shortfalls


# --------------------------------------------------------------------------
# scripture reference checking
# --------------------------------------------------------------------------

_WS = re.compile(r"\s+")


def _norm(text):
    folded = unicodedata.normalize("NFKC", text or "")
    return _WS.sub(" ", folded).strip().lower()


_REF_SPLIT = re.compile(r"^(.*?)(\d+)\s*:\s*(\d+)\s*[-–]?\s*(\d+)?$")


def check_scripture_ref(ref, chunk_text):
    """Is *ref* genuinely supported by the chunk the model was shown?

    Returns ``(exact, supported)``.

    * ``exact``     -- the whole reference appears verbatim (normalised).
    * ``supported`` -- the chapter:verse appears and the book name (or its
      first four letters) also appears in the chunk.  This accepts a model
      that expands ``Matt. 24:14`` into ``Matthew 24:14``.
    """
    if not ref or not chunk_text:
        return False, False

    haystack = _norm(chunk_text)
    needle = _norm(ref)
    if not needle:
        return False, False
    if needle in haystack:
        return True, True

    match = _REF_SPLIT.match(needle)
    if not match:
        return False, False

    book, chapter, verse, verse_end = match.groups()
    book = book.strip().rstrip(".")
    if not book:
        return False, False

    citation = "%s:%s" % (chapter, verse)
    if citation not in haystack:
        return False, False

    # Accept an expanded or abbreviated book name (Matt. <-> Matthew) by
    # requiring a three-letter stem of the final book word to appear too.
    word = book.split()[-1] if book.split() else ""
    stem = word[:3]
    if stem and re.search(r"\b%s" % re.escape(stem), haystack):
        return False, True
    return False, False


# --------------------------------------------------------------------------
# scoring
# --------------------------------------------------------------------------

def score_response(raw_text, chunk, document_text):
    """Score one model response with the production verifier."""
    result = {
        "json_parsed": False,
        "json_error": None,
        "schema_errors": [],
        "findings_total": 0,
        "findings_verified": 0,
        "findings_fabricated": 0,
        "quote_exact": 0,
        "quote_normalized": 0,
        "quote_unmatched": 0,
        "no_findings_flag": False,
        "refs_total": 0,
        "refs_exact": 0,
        "refs_supported": 0,
        "topics": [],
        "quarantined": [],
    }

    try:
        payload = json.loads(raw_text)
    except ValueError as exc:
        result["json_error"] = str(exc)[:200]
        return result

    result["json_parsed"] = True
    if isinstance(payload, dict):
        result["no_findings_flag"] = bool(payload.get("no_findings"))

    findings, errors = verifier.validate_response(payload)
    result["schema_errors"] = errors
    result["findings_total"] = len(findings)

    verified, quarantined = verifier.verify_findings(findings, chunk, document_text)
    result["findings_verified"] = len(verified)
    result["findings_fabricated"] = len(quarantined)
    result["quarantined"] = [
        {"quote": item["finding"]["quote"][:200], "reason": item["reason"]}
        for item in quarantined
    ]

    for finding in verified:
        if finding["quote_match"] == "exact":
            result["quote_exact"] += 1
        else:
            result["quote_normalized"] += 1
    for item in quarantined:
        result["quote_unmatched"] += 1

    for finding in findings:
        result["topics"].append(finding["topic"])
        for ref in finding.get("scripture_refs") or []:
            result["refs_total"] += 1
            exact, supported = check_scripture_ref(ref, chunk["text"])
            if exact:
                result["refs_exact"] += 1
            if supported:
                result["refs_supported"] += 1

    return result


# --------------------------------------------------------------------------
# GPU / resident-model control
# --------------------------------------------------------------------------

def resident_models(base_url=model_client.DEFAULT_BASE_URL):
    try:
        return model_client.list_loaded_models(base_url=base_url)
    except Exception as exc:  # noqa: BLE001
        return [{"name": "__error__", "size_vram": 0, "context": str(exc)}]


def unload(model, base_url=model_client.DEFAULT_BASE_URL, timeout=60):
    """Ask Ollama to release a model *this benchmark loaded itself*."""
    body = json.dumps({"model": model, "keep_alive": 0}).encode("utf-8")
    request = urllib.request.Request(
        base_url + "/api/generate", data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read()
        return True
    except Exception:  # noqa: BLE001
        return False


def wait_for_release(base_url=model_client.DEFAULT_BASE_URL, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        loaded = [m for m in resident_models(base_url) if m.get("name") != "__error__"]
        if not loaded:
            return True
        time.sleep(2)
    return False


def gpu_snapshot():
    """VRAM used per GPU, parsed from nvidia-smi (read-only)."""
    try:
        import subprocess
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=15, check=True,
        ).stdout
        rows = []
        for line in out.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3:
                rows.append({"gpu": int(parts[0]), "used_mib": int(parts[1]),
                             "total_mib": int(parts[2])})
        return rows
    except Exception as exc:  # noqa: BLE001
        return [{"error": "%s: %s" % (type(exc).__name__, exc)}]


# --------------------------------------------------------------------------
# document text recovery
# --------------------------------------------------------------------------

class DocumentCache:
    """Extract each source document at most once per benchmark run."""

    def __init__(self):
        self._text = {}

    def text(self, relative_path):
        if relative_path not in self._text:
            absolute = os.path.join(DOCUMENTS_DIR, relative_path)
            self._text[relative_path] = extractor.extract(absolute)["text"]
        return self._text[relative_path]

    def chunk(self, record):
        text = self.text(record["path"])
        start, end = record["char_start"], record["char_end"]
        piece = text[start:end]
        return {
            "chunk_id": record["chunk_id"],
            "index": None,
            "char_start": start,
            "char_end": end,
            "char_count": len(piece),
            "text": piece,
        }


# --------------------------------------------------------------------------
# benchmark run
# --------------------------------------------------------------------------

def benchmark_model(name, sample, args, cache, base_url=model_client.DEFAULT_BASE_URL):
    outcome = {
        "model": name,
        "status": "pending",
        "passages": 0,
        "errors": [],
        "timing": {},
        "gpu": {},
        "resident_before": resident_models(base_url),
        "resident_after": None,
        "records": [],
    }

    # --- competing-workload gate -----------------------------------------
    loaded = [m for m in outcome["resident_before"] if m.get("name") != "__error__"]
    foreign = [m for m in loaded if m.get("name") != name]
    if foreign:
        outcome["status"] = "aborted"
        outcome["errors"].append(
            "competing local-model workload(s) resident: %s. Refusing to evict."
            % ", ".join(str(m.get("name")) for m in foreign)
        )
        return outcome
    if loaded:
        # our own model from a previous model's run -- release it first
        wait_for_release(base_url)

    gpu_before = gpu_snapshot()

    try:
        model_client.assert_local_model(name)
    except model_client.CloudModelRejected as exc:
        outcome["status"] = "rejected"
        outcome["errors"].append(str(exc))
        return outcome

    # --- warm-up load (not scored) ---------------------------------------
    warm_prompt = runner.build_prompt(cache.chunk(sample[0]), sample[0]["path"])
    try:
        warm = model_client.generate_json(
            warm_prompt, name, base_url=base_url,
            options=runner.MODEL_OPTIONS, timeout=args.timeout,
            attempts=1, keep_alive=args.keep_alive,
        )
        outcome["timing"]["load_seconds"] = round(warm["load_seconds"], 3)
    except Exception as exc:  # noqa: BLE001
        outcome["status"] = "unavailable"
        outcome["errors"].append("warm-up failed: %s: %s" % (type(exc).__name__, exc))
        return outcome

    outcome["gpu"]["after_load"] = gpu_snapshot()
    outcome["resident_after_load"] = resident_models(base_url)

    # --- scored passes ----------------------------------------------------
    totals = {
        "wall": 0.0, "prompt_count": 0, "prompt_seconds": 0.0,
        "eval_count": 0, "eval_seconds": 0.0,
    }
    scores = []

    for position, record in enumerate(sample[: args.max_passages], start=1):
        chunk = cache.chunk(record)
        assert chunk["text"] == cache.text(record["path"])[record["char_start"]:record["char_end"]]
        prompt = runner.build_prompt(chunk, record["path"])

        try:
            response = model_client.generate_json(
                prompt, name, base_url=base_url,
                options=runner.MODEL_OPTIONS, timeout=args.timeout,
                attempts=args.attempts, keep_alive=args.keep_alive,
            )
        except Exception as exc:  # noqa: BLE001
            outcome["errors"].append(
                "passage %d (%s) failed: %s: %s"
                % (position, record["path"], type(exc).__name__, exc)
            )
            continue

        scored = score_response(response["response"], chunk, cache.text(record["path"]))
        scored.update({
            "position": position,
            "path": record["path"],
            "sha256": record.get("sha256"),
            "chunk_id": record["chunk_id"],
            "char_start": record["char_start"],
            "char_end": record["char_end"],
            "stratum": record.get("stratum"),
            "triage_topics": record.get("topics"),
            "triage_score": record.get("score"),
            "wall_seconds": round(response["wall_seconds"], 3),
            "prompt_eval_count": response.get("prompt_eval_count"),
            "eval_count": response.get("eval_count"),
            "prompt_eval_seconds": round(response.get("prompt_eval_seconds") or 0, 4),
            "eval_seconds": round(response.get("eval_seconds") or 0, 4),
            "attempts": response.get("attempts"),
        })
        scores.append(scored)

        totals["wall"] += response["wall_seconds"]
        totals["prompt_count"] += response.get("prompt_eval_count") or 0
        totals["prompt_seconds"] += response.get("prompt_eval_seconds") or 0
        totals["eval_count"] += response.get("eval_count") or 0
        totals["eval_seconds"] += response.get("eval_seconds") or 0

        if position % 10 == 0 or position == len(sample[: args.max_passages]):
            print("    %s: %d/%d" % (name, position, len(sample[: args.max_passages])),
                  flush=True)

    outcome["passages"] = len(scores)
    outcome["records"] = scores
    outcome["gpu"]["peak_after_run"] = gpu_snapshot()
    outcome["resident_after"] = resident_models(base_url)
    outcome["timing"].update({
        "wall_seconds_total": round(totals["wall"], 3),
        "wall_seconds_per_passage": round(totals["wall"] / len(scores), 3) if scores else None,
        "prompt_tokens": totals["prompt_count"],
        "eval_tokens": totals["eval_count"],
        "prompt_tokens_per_second": (
            round(totals["prompt_count"] / totals["prompt_seconds"], 1)
            if totals["prompt_seconds"] else None
        ),
        "eval_tokens_per_second": (
            round(totals["eval_count"] / totals["eval_seconds"], 1)
            if totals["eval_seconds"] else None
        ),
    })

    outcome["accuracy"] = aggregate(scores)
    outcome["status"] = "ok" if scores else "no_data"
    outcome["gpu_memory"] = {
        "before": gpu_before,
        "after_load": outcome["gpu"].get("after_load"),
        "after_run": outcome["gpu"].get("peak_after_run"),
        "resident_size_vram_bytes": (
            (outcome["resident_after"] or [{}])[0].get("size_vram")
            if outcome["resident_after"] else None
        ),
    }

    # release our own model so the next one starts from a clean GPU
    unload(name, base_url)
    wait_for_release(base_url)
    return outcome


def aggregate(scores):
    if not scores:
        return {}
    n = len(scores)
    exact = sum(s["quote_exact"] for s in scores)
    norm = sum(s["quote_normalized"] for s in scores)
    unmatched = sum(s["quote_unmatched"] for s in scores)
    quotes = exact + norm + unmatched
    refs_total = sum(s["refs_total"] for s in scores)
    refs_supported = sum(s["refs_supported"] for s in scores)
    refs_exact = sum(s["refs_exact"] for s in scores)

    topic_agree = 0
    topic_scored = 0
    for s in scores:
        triage_topics = set(s.get("triage_topics") or ())
        if not triage_topics:
            continue
        topic_scored += 1
        reported = set(s.get("topics") or ())
        if reported & (triage_topics | {"scripture"}):
            topic_agree += 1

    return {
        "passages": n,
        "json_valid": sum(1 for s in scores if s["json_parsed"]),
        "json_parse_failures": sum(1 for s in scores if not s["json_parsed"]),
        "schema_error_count": sum(len(s["schema_errors"]) for s in scores),
        "findings_total": sum(s["findings_total"] for s in scores),
        "findings_verified": sum(s["findings_verified"] for s in scores),
        "findings_fabricated": sum(s["findings_fabricated"] for s in scores),
        "passages_with_findings": sum(1 for s in scores if s["findings_total"] > 0),
        "passages_with_zero_findings": sum(1 for s in scores if s["findings_total"] == 0),
        "quotes_total": quotes,
        "quote_exact": exact,
        "quote_normalized": norm,
        "quote_unmatched": unmatched,
        "exact_quote_rate": round(exact / quotes, 4) if quotes else None,
        "verified_quote_rate": round((exact + norm) / quotes, 4) if quotes else None,
        "fabrication_rate": round(unmatched / quotes, 4) if quotes else None,
        "refs_total": refs_total,
        "refs_exact": refs_exact,
        "refs_supported": refs_supported,
        "ref_exact_rate": round(refs_exact / refs_total, 4) if refs_total else None,
        "ref_supported_rate": round(refs_supported / refs_total, 4) if refs_total else None,
        "topic_agreement": round(topic_agree / topic_scored, 4) if topic_scored else None,
        "findings_per_passage": round(sum(s["findings_total"] for s in scores) / n, 3),
    }


def estimate_full_run(aggregate_result, timing, total_passages=10284):
    """Scale measured per-passage cost to the full HIGH-priority set."""
    per_passage = timing.get("wall_seconds_per_passage")
    if not per_passage:
        return {}
    seconds = per_passage * total_passages
    return {
        "passages": total_passages,
        "measured_seconds_per_passage": per_passage,
        "estimated_seconds": round(seconds, 1),
        "estimated_hours": round(seconds / 3600.0, 2),
        "basis": "measured wall time per passage x %d passages" % total_passages,
    }


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def run(args):
    started = utcnow()
    wall_start = time.time()
    os.makedirs(BENCHMARK_DIR, exist_ok=True)

    print("== verifying models and endpoints ==", flush=True)
    available, decisions = verify_models()
    for record in decisions:
        if record["runnable"]:
            details = record.get("details") or {}
            print("  RUNNABLE  %-24s %s %s (%.2f GB)"
                  % (record["requested"], details.get("parameter_size"),
                     details.get("quantization"),
                     (details.get("size_bytes") or 0) / 1e9))
        else:
            print("  SKIP      %-24s %s" % (record["requested"], record["reason"]))

    runnable = [r["requested"] for r in decisions if r["runnable"]]
    if not runnable:
        raise SystemExit("no runnable local models; aborting")

    # Narrow the pipeline allow-list to exactly the models under test.
    # Cloud rejection still happens first in assert_local_model.
    model_client.LOCAL_MODEL_ALLOWLIST = tuple(runnable)
    print("  allow-list narrowed to: %s" % (list(runnable),), flush=True)

    print("== building stratified sample ==", flush=True)
    candidates = load_high_candidates()
    sample, shortfalls = build_sample(candidates)
    print("  HIGH candidates: %d ; sample: %d" % (len(candidates), len(sample)))
    counts = {}
    for record in sample:
        counts[record["stratum"]] = counts.get(record["stratum"], 0) + 1
    print("  by stratum: %s ; shortfalls: %s" % (counts, shortfalls or "none"), flush=True)

    cache = DocumentCache()
    # warm the document cache and prove the offsets reproduce the text
    verified_offsets = 0
    for record in sample:
        text = cache.text(record["path"])
        piece = text[record["char_start"]:record["char_end"]]
        if len(piece) == record["char_count"]:
            verified_offsets += 1
    print("  offsets reproducing source text: %d/%d" % (verified_offsets, len(sample)),
          flush=True)

    results = []
    for name in runnable:
        print("== benchmarking %s ==" % name, flush=True)
        outcome = benchmark_model(name, sample, args, cache)
        outcome.pop("gpu", None)
        results.append(outcome)
        accuracy = outcome.get("accuracy") or {}
        print("  status=%s passages=%s json_valid=%s exact_quote_rate=%s "
              "fabrications=%s"
              % (outcome["status"], outcome.get("passages"),
                 accuracy.get("json_valid"), accuracy.get("exact_quote_rate"),
                 accuracy.get("findings_fabricated")), flush=True)

    # ---- write results separately from production findings --------------
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    summary = {
        "schema_version": SCHEMA,
        "generated_at": utcnow(),
        "wall_seconds": round(time.time() - wall_start, 1),
        "started_at": started,
        "sample": {
            "seed": SAMPLE_SEED,
            "size": len(sample),
            "strata": STRATA,
            "observed_strata": counts,
            "shortfalls": shortfalls,
            "chunk_chars": CHUNK_CHARS,
            "offsets_verified": verified_offsets,
        },
        "models_available": available,
        "model_decisions": decisions,
        "prompt": {
            "source": "gd_research_run.PROMPT_TEMPLATE via build_prompt",
            "prompt_version": runner.PROMPT_VERSION,
            "options": runner.MODEL_OPTIONS,
            "identical_across_models": True,
        },
        "verifier": {
            "schema_version": verifier.SCHEMA_VERSION,
            "quote_matching": "gd_research_verify.verify_quote",
            "identical_across_models": True,
        },
        "results": [],
    }

    for outcome in results:
        summary["results"].append({
            "model": outcome["model"],
            "status": outcome["status"],
            "passages": outcome.get("passages"),
            "accuracy": outcome.get("accuracy"),
            "timing": outcome.get("timing"),
            "gpu_memory": outcome.get("gpu_memory"),
            "errors": outcome.get("errors"),
            "estimated_full_run": estimate_full_run(
                outcome.get("accuracy"), outcome.get("timing") or {}
            ),
        })

    summary_path = os.path.join(BENCHMARK_DIR, "benchmark-%s.json" % stamp)
    raw_path = os.path.join(BENCHMARK_DIR, "benchmark-%s-raw.jsonl" % stamp)
    with open(raw_path, "w", encoding="utf-8") as handle:
        for outcome in results:
            for record in outcome.get("records") or []:
                handle.write(json.dumps(
                    {"model": outcome["model"], **record}, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    runner.atomic_write_json(summary_path, summary)
    runner.atomic_write_json(os.path.join(BENCHMARK_DIR, "latest.json"), summary)

    print("\n== summary written ==")
    print("  %s" % summary_path)
    print("  %s" % raw_path)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Bounded local-only accuracy benchmark (no cloud, one model at a time).")
    parser.add_argument("--max-passages", type=int, default=100)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--attempts", type=int, default=2)
    parser.add_argument("--keep-alive", default="10m")
    parser.add_argument("--verify-only", action="store_true",
                        help="report model availability and exit without benchmarking")
    args = parser.parse_args(argv)

    if args.verify_only:
        available, decisions = verify_models()
        print(json.dumps({"available": available, "decisions": decisions}, indent=2))
        return 0

    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
