#!/usr/bin/env python3
"""Milestone 2: bounded, resumable, local-only two-pass research runner.

Design
------
**Two passes, two models, at most two model loads per run.**

* *screen*   -- ``gemma4-local:latest`` reads every pending HIGH chunk.
  Measured at 2.94 s/passage on the validation set with an 8.8% fabrication
  rate, ~4x faster than the 27B baseline.
* *escalate* -- ``qwen3.6:27b`` re-reads only the chunks the screen pass
  could not settle: an unparsed response, an unsupported (invented)
  quotation, or nothing but low-confidence findings.  The validation
  measured 29/31 (94%) of unsupported-quote chunks recovering real evidence
  on the second pass, which is easily worth 10.95 s/passage.

  A chunk the screen pass simply found *nothing* in is deliberately **not**
  re-read: that trigger recovered only 1/29 (3%) while costing ~4.5 h across
  the corpus.  Those passages are appended to a zero-finding audit queue
  for later recall review, so no passage is ever discarded.

Both passes run for *all* selected chunks before the other model is
needed, so a run loads each model once instead of thrashing per document.

Escalation policy
-----------------
Which chunks earn a second pass is an explicit, versioned data structure
(:data:`ESCALATION_POLICY`).  Changing it changes only *selection*: it is
deliberately kept out of the checkpoint identity, so tightening or relaxing
the policy never forces the corpus to be re-inferred.

Bounded batches
---------------
One run may make at most :data:`BULK_CEILING` model calls.  Candidates are
filtered to *pending* work **before** the limit is applied -- filtering
afterwards would make every batch after the first re-select the same top-N,
skip all of them, and do nothing.  ``--status`` reports what remains.

Chunk identity is content-addressed, so byte-identical documents saved
under different names are one research unit; the other filenames are
recorded as ``aliases`` on the findings document.

Checkpointing and resume
------------------------
Each chunk result is durably recorded, keyed on a content-addressed
identity::

    key = sha256(sha256 || chunk_id || extractor_version || chunker_version
                 || prompt_version || analysis_version || model
                 || options_fingerprint)

A chunk is reprocessed only when its key no longer matches, so an
interrupted run resumes exactly where it stopped and unchanged inputs are
never re-analysed.  The document findings file is written with the
collector's established atomic pattern (temp file, fsync, ``os.replace``,
directory fsync) after every chunk, so a crash can lose at most the chunk
in flight -- never earlier work.

Provenance is stricter than Milestone 0
---------------------------------------
``gd_research_verify.verify_quote`` falls back to searching the **whole
document**, so a quotation that never appeared in the chunk the model was
shown still comes back ``match="exact", verified=True`` with
``offset_in_chunk=None``.  That silently over-credits a model that
invents plausible text from elsewhere in the file.

This runner classifies every quotation into four provenance classes and
only the first two count as evidence the model actually saw:

* ``in_chunk_exact`` / ``in_chunk_normalized`` -- verified, in-window
* ``document_only``                            -- real text, but from
  outside the model's evidence window: recorded, never promoted
* ``fabricated``                               -- found nowhere:
  quarantined with the reason

Safety
------
* Strict local allow-list; cloud-tagged names are refused before any
  request is built.
* A model this run did not load is never evicted.  A foreign resident
  model aborts the run instead.
* Every write is asserted to land inside ``research/``.  The runner never
  opens the canonical GD Bible tree and never modifies ``documents/``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gd_research_chunk as chunker            # noqa: E402
import gd_research_extract as extractor        # noqa: E402
import gd_research_model as model_client       # noqa: E402
import gd_research_run as runner               # noqa: E402
import gd_research_verify as verifier          # noqa: E402

PIPELINE_VERSION = "2.0.0"
FINDINGS_SCHEMA = "gd-research-findings/2"
PROMPT_VERSION = runner.PROMPT_VERSION          # "analyse-v1"

#: Bumped whenever the *verification* logic changes, so that checkpoints
#: produced by an older classifier are re-derived instead of being
#: trusted.  Kept separate from PIPELINE_VERSION so that an unrelated
#: code change does not force a full re-inference of the corpus.
ANALYSIS_VERSION = "provenance-3"

ARCHIVE_ROOT = os.environ.get("GD_ARCHIVE_ROOT", "/home/liongateos/PCOG-Research-Archive")
DOCUMENTS_DIR = os.path.join(ARCHIVE_ROOT, "documents")
RESEARCH_DIR = os.path.join(ARCHIVE_ROOT, "research")
INDEX_PATH = os.path.join(RESEARCH_DIR, "index", "chunk_index.jsonl")
FINDINGS_DIR = os.path.join(RESEARCH_DIR, "findings")
STATE_DIR = os.path.join(RESEARCH_DIR, "state")
STATE_PATH = os.path.join(STATE_DIR, "pipeline_state.json")

#: Auditable queue of passages the screen pass returned nothing for.  Those
#: passages are *never* discarded -- they are set aside for later recall
#: review instead of being re-read by the second-pass model.
AUDIT_QUEUE_PATH = os.path.join(STATE_DIR, "zero_finding_queue.jsonl")

#: Canonical GD Bible assets.  Listed only so the runner can *refuse* to
#: write there; it never reads or opens them.
PROTECTED_TREES = ("/home/liongateos/LionGateOS-Bible-Backups", "/home/liongateos/LionGateOS-Bible")

SCREEN_MODEL = "gemma4-local:latest"
ESCALATE_MODEL = "qwen3.6:27b"

#: The only models this runner may load.  Both are genuinely local.
LOCAL_MODEL_ALLOWLIST = (SCREEN_MODEL, ESCALATE_MODEL)

#: Milestone 0 used num_predict=700.  The benchmark proved that truncates
#: ~12% of qwen3.6:27b and ~2% of gemma4-local responses mid-JSON.  1500
#: returned 14/14 valid in the diagnostic, so it is the floor here.
MODEL_OPTIONS = {
    "num_predict": 1500,
    "num_ctx": 8192,
    "temperature": 0,
    "top_p": 0.9,
}

DEFAULT_CHUNK_CHARS = 2400
DEFAULT_TIMEOUT = 300
DEFAULT_ATTEMPTS = 2

#: Hard ceiling for one run.  Bulk inference is refused in code, not by
#: convention.  450 covers an authorised 200-passage validation at worst
#: case (200 screen + 200 escalate) while still refusing anything on the
#: scale of the 10,284-passage corpus.
BULK_CEILING = 450

#: Versioned escalation policy.  This governs *which* chunks the second-pass
#: model re-reads.  It deliberately does not affect how any individual chunk
#: is analysed, so existing per-chunk checkpoints remain valid across a
#: policy change and nothing has to be re-inferred.
ESCALATION_POLICY_VERSION = "escalate-v2"

ESCALATION_POLICY = {
    "version": ESCALATION_POLICY_VERSION,
    #: A second pass is still worth its 10.95 s/passage for these.
    #: ``unsupported_quote`` is the high-yield trigger: the validation
    #: measured 29/31 (94%) of those chunks recovering real evidence on the
    #: second pass.
    "escalate_on": ("json_unparsed", "unsupported_quote", "low_confidence_only"),
    #: Deliberately NOT escalated.  ``zero_findings`` recovered only 1/29
    #: (3%) on the second pass while costing ~4.5 h over the full corpus, so
    #: those passages are queued for recall review instead of re-run.
    "audit_only": ("zero_findings", "missing_result"),
    #: Where an audited passage goes.  Nothing is dropped.
    "audit_disposition": "zero_finding_queue",
}

#: Every reason the policy knows about, whether escalated or audited.
ESCALATION_REASONS = (tuple(ESCALATION_POLICY["escalate_on"])
                      + tuple(ESCALATION_POLICY["audit_only"]))

STATE_SCHEMA = "gd-pipeline-state/1"


class PipelineError(Exception):
    """Base class for runner failures."""


class BulkRefused(PipelineError):
    """Raised when a requested batch exceeds the milestone ceiling."""


class ForeignModelResident(PipelineError):
    """Raised rather than evicting a model this run did not load."""


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------
# path safety
# --------------------------------------------------------------------------

def assert_inside_research(path):
    """Refuse to write anywhere outside the research tree."""
    resolved = os.path.realpath(path)
    research = os.path.realpath(RESEARCH_DIR)
    if not (resolved == research or resolved.startswith(research + os.sep)):
        raise PipelineError("refusing to write outside research/: %s" % resolved)
    for protected in PROTECTED_TREES:
        real = os.path.realpath(protected)
        if resolved == real or resolved.startswith(real + os.sep):
            raise PipelineError("refusing to write into protected tree: %s" % resolved)
    return resolved


def write_json(path, payload):
    assert_inside_research(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    runner.atomic_write_json(path, payload)


# --------------------------------------------------------------------------
# identity
# --------------------------------------------------------------------------

def options_fingerprint(options):
    blob = json.dumps(options, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def chunk_key(sha256, chunk_id, model, options):
    """Content-addressed identity for one chunk analysis."""
    parts = [
        sha256 or "",
        chunk_id or "",
        extractor.EXTRACTOR_VERSION,
        chunker.CHUNKER_VERSION,
        PROMPT_VERSION,
        ANALYSIS_VERSION,
        model,
        options_fingerprint(options),
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:24]


# --------------------------------------------------------------------------
# provenance classification (stricter than Milestone 0)
# --------------------------------------------------------------------------

#: A quotation shorter than this, matched only after normalisation, is too
#: weak to serve as editorial evidence and is quarantined as ambiguous.
MIN_EVIDENCE_CHARS = 8


def normalize_with_offsets(text):
    """Normalise like :func:`gd_research_verify.normalize_for_match`, but
    keep a map from each normalised character back to its source offsets.

    Returns ``(normalized_text, triples)`` where ``triples[i]`` is
    ``(char, source_start, source_end)`` for normalised index *i*.
    """
    triples = []
    for index, char in enumerate(text):
        for folded in unicodedata.normalize("NFKC", char):
            folded = verifier._SMART_QUOTES.get(folded, folded)  # noqa: SLF001
            if folded:
                triples.append((folded, index, index + 1))

    out = []
    last_was_space = True          # drops leading whitespace
    for char, start, end in triples:
        if char.isspace():
            if last_was_space:
                continue
            out.append((" ", start, end))
            last_was_space = True
        else:
            out.append((char, start, end))
            last_was_space = False
    while out and out[-1][0] == " ":     # drop trailing whitespace
        out.pop()

    return "".join(t[0] for t in out), out


def locate_normalized(needle, text):
    """Sentence-level ``(start, end, occurrences)`` for a normalised match.

    The offset is self-checked by re-normalising the slice it points at;
    an offset that cannot be proved is never returned.  ``(None, None, n)``
    means the text is present but not precisely locatable.
    """
    if not needle:
        return None, None, 0
    normalized, triples = normalize_with_offsets(text)
    if not normalized:
        return None, None, 0

    occurrences = normalized.count(needle)
    index = normalized.find(needle)
    if index < 0:
        return None, None, 0

    start = triples[index][1]
    end = triples[index + len(needle) - 1][2]
    if verifier.normalize_for_match(text[start:end]) != needle:
        return None, None, occurrences
    return start, end, occurrences


def classify_finding(finding, chunk, document_text):
    """Classify one quotation by where it can actually be found.

    Returns a dict with ``provenance``, ``verified``, ``in_chunk`` and the
    absolute offsets.  ``verified`` always agrees with
    ``gd_research_verify.verify_quote`` so the two verifiers cannot drift.
    """
    quote = finding.get("quote") or ""
    result = {
        "provenance": "fabricated",
        "verified": False,
        "in_chunk": False,
        "ambiguous": False,
        "occurrences": 0,
        "offset_in_chunk": None,
        "char_start": None,
        "char_end": None,
    }

    if not quote:
        return result

    # 1. exact, inside the chunk the model was shown
    position = chunk["text"].find(quote)
    if position >= 0:
        absolute = chunk["char_start"] + position
        result.update({
            "provenance": "in_chunk_exact", "verified": True, "in_chunk": True,
            "occurrences": chunk["text"].count(quote),
            "offset_in_chunk": position,
            "char_start": absolute, "char_end": absolute + len(quote),
        })
        return result

    # 2. exact, but only elsewhere in the document
    position = document_text.find(quote)
    if position >= 0:
        result.update({
            "provenance": "document_only", "verified": True, "in_chunk": False,
            "char_start": position, "char_end": position + len(quote),
        })
        return result

    # 3. normalised fallback (curly quotes, dashes, whitespace runs)
    needle = verifier.normalize_for_match(quote)
    if needle:
        start, end, occurrences = locate_normalized(needle, chunk["text"])
        if occurrences:
            result.update({
                "provenance": "in_chunk_normalized", "verified": True,
                "in_chunk": True, "occurrences": occurrences,
            })
            if start is not None:
                # sentence-level offset, proved by re-normalising the slice
                result["char_start"] = chunk["char_start"] + start
                result["char_end"] = chunk["char_start"] + end
                result["offset_in_chunk"] = start
            else:
                # present, but not precisely locatable
                result["char_start"] = chunk["char_start"]
            if len(needle) < MIN_EVIDENCE_CHARS:
                result.update({"provenance": "ambiguous", "ambiguous": True})
            return result

        start, end, occurrences = locate_normalized(needle, document_text)
        if occurrences:
            result.update({
                "provenance": "document_only_normalized", "verified": True,
                "in_chunk": False, "occurrences": occurrences,
                "char_start": start, "char_end": end,
            })
            if len(needle) < MIN_EVIDENCE_CHARS:
                result.update({"provenance": "ambiguous", "ambiguous": True})
            return result

    return result


def analyse_response(raw_text, chunk, document_text):
    """Parse, validate and verify one response; never trust the model."""
    outcome = {
        "status": "ok",
        "json_parsed": False,
        "json_error": None,
        "schema_errors": [],
        "verified": [],
        "quarantined": [],
        "provenance": {
            "in_chunk_exact": 0, "in_chunk_normalized": 0,
            "document_only": 0, "document_only_normalized": 0,
            "fabricated": 0, "ambiguous": 0,
        },
        "findings_total": 0,
    }

    try:
        payload = json.loads(raw_text)
    except ValueError as exc:
        outcome["status"] = "unparsed"
        outcome["json_error"] = str(exc)[:200]
        return outcome

    outcome["json_parsed"] = True
    findings, errors = verifier.validate_response(payload)
    outcome["schema_errors"] = errors
    outcome["findings_total"] = len(findings)

    for finding in findings:
        check = classify_finding(finding, chunk, document_text)

        # keep the two verifiers honest
        reference = verifier.verify_quote(finding["quote"], chunk, document_text)
        if reference["verified"] != check["verified"]:
            raise PipelineError(
                "provenance classifier disagrees with gd_research_verify for %r"
                % finding["quote"][:60]
            )

        enriched = dict(finding)
        enriched.update(check)
        outcome["provenance"][check["provenance"]] += 1

        if check["provenance"] == "fabricated":
            outcome["quarantined"].append({
                "reason": "quote not found in the chunk shown or in the document",
                "finding": enriched,
            })
        elif check["provenance"] == "ambiguous":
            outcome["quarantined"].append({
                "reason": "ambiguous: quotation is shorter than %d characters once "
                          "normalised, too weak to certify as editorial evidence"
                          % MIN_EVIDENCE_CHARS,
                "finding": enriched,
            })
        else:
            outcome["verified"].append(enriched)

    return outcome


# --------------------------------------------------------------------------
# escalation policy
# --------------------------------------------------------------------------

def escalation_reasons(pass_result):
    """Why (if at all) a screened chunk needs the second-pass model."""
    reasons = []
    if not pass_result:
        return ["missing_result"]
    if not pass_result.get("json_parsed"):
        reasons.append("json_unparsed")
    if pass_result.get("provenance", {}).get("fabricated", 0) > 0:
        reasons.append("unsupported_quote")
    if pass_result.get("findings_total", 0) == 0:
        reasons.append("zero_findings")
    confidences = {f.get("confidence") for f in pass_result.get("verified", [])}
    if confidences and confidences <= {"low"}:
        reasons.append("low_confidence_only")
    return reasons


def escalation_decision(pass_result):
    """Apply the versioned policy to a screened chunk.

    Returns ``(escalate, reasons, audited)``: *reasons* are the policy's
    escalation triggers, *audited* are reasons recorded for recall review
    without spending a second pass on them.
    """
    reasons = escalation_reasons(pass_result)
    escalate_on = set(ESCALATION_POLICY["escalate_on"])
    audit_only = set(ESCALATION_POLICY["audit_only"])
    triggered = [r for r in reasons if r in escalate_on]
    audited = [r for r in reasons if r in audit_only]
    return bool(triggered), triggered, audited


# --------------------------------------------------------------------------
# zero-finding audit queue (no passage is ever discarded)
# --------------------------------------------------------------------------

def load_audit_queue(path=None):
    """Every passage already set aside for recall review."""
    path = path or AUDIT_QUEUE_PATH
    entries = []
    if not os.path.isfile(path):
        return entries
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        return entries
    return entries


def audit_queue_keys(entries):
    """Identity of every queued passage, for idempotent appends."""
    return {(entry.get("sha256"), entry.get("chunk_id")) for entry in entries}


def record_audit(record, screen_result, reasons, path=None):
    """Append a zero-finding passage to the audit queue.  Append-only + fsync,
    so a crash can cost at most the line in flight and never a prior entry."""
    path = path or AUDIT_QUEUE_PATH
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    entry = {
        "queued_at": utcnow(),
        "document": record.get("path"),
        "sha256": record.get("sha256"),
        "chunk_id": record.get("chunk_id"),
        "char_start": record.get("char_start"),
        "char_end": record.get("char_end"),
        "priority": record.get("priority"),
        "topics": record.get("topics"),
        "score": record.get("score"),
        "collection": record.get("collection"),
        "reasons": list(reasons),
        "findings_total": (screen_result or {}).get("findings_total"),
        "json_parsed": (screen_result or {}).get("json_parsed"),
        "screen_key": (screen_result or {}).get("key"),
        "model": (screen_result or {}).get("model"),
        "policy_version": ESCALATION_POLICY_VERSION,
        "disposition": ESCALATION_POLICY["audit_disposition"],
    }
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return entry


# --------------------------------------------------------------------------
# model lifecycle (never evict what we did not load)
# --------------------------------------------------------------------------

def call_model(prompt, model, options, timeout, attempts, keep_alive):
    """Single indirection so tests can substitute a stub model."""
    return model_client.generate_json(
        prompt, model, base_url=model_client.DEFAULT_BASE_URL,
        options=options, timeout=timeout, attempts=attempts,
        keep_alive=keep_alive,
    )


def ensure_model_ready(model, owned, release_owned=True, base_url=None):
    """Load *model* only if no foreign model would be evicted.

    ``owned`` is the set of models *this run* already loaded.  Releasing
    one of those is a deliberate, recorded action; touching anything else
    is refused outright.
    """
    base_url = base_url or model_client.DEFAULT_BASE_URL
    target = model_client.assert_local_model(model)
    resident = [
        item for item in model_client.list_loaded_models(base_url=base_url)
        if item.get("name") and item.get("name") != "__error__"
    ]
    names = {item["name"] for item in resident}

    foreign = names - set(owned) - {target}
    if foreign:
        raise ForeignModelResident(
            "resident model(s) %s were not loaded by this run; refusing to "
            "evict them" % ", ".join(sorted(foreign))
        )

    if target in names:
        return {"loaded": False, "already_resident": True, "released": []}

    released = []
    if release_owned:
        for name in sorted(names & set(owned)):
            release_model(name, base_url=base_url)
            released.append(name)
    return {"loaded": True, "already_resident": False, "released": released}


def release_model(model, base_url=None, timeout=60):
    """Ask Ollama to drop a model this run loaded itself."""
    import urllib.request
    base_url = base_url or model_client.DEFAULT_BASE_URL
    body = json.dumps({"model": model, "keep_alive": 0}).encode("utf-8")
    request = urllib.request.Request(
        base_url + "/api/generate", data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read()
        return True
    except Exception:  # noqa: BLE001 - best effort, never fatal
        return False


# --------------------------------------------------------------------------
# GPU availability gate
# --------------------------------------------------------------------------

class SafetyCheckFailed(PipelineError):
    """Raised when a pre-flight or post-load safety check fails."""


def check_gpu_environment():
    """Probe GPU availability *before* any model is loaded.

    Two independent probes are used because a sandboxed shell can mask
    ``/dev/nvidia*`` while the driver and Ollama are perfectly healthy.
    ``confirmed`` means direct evidence was visible; when it is False the
    caller must fall back to :func:`verify_gpu_resident`, which is the
    authoritative check.
    """
    import glob
    import subprocess
    import urllib.request

    report = {
        "device_nodes": sorted(glob.glob("/dev/nvidia*")),
        "nvidia_smi": None,
        "ollama_version": None,
        "confirmed": False,
        "notes": [],
    }

    try:
        proc = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,name,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=20,
        )
        if proc.returncode == 0:
            rows = []
            for line in proc.stdout.strip().splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 4:
                    rows.append({"gpu": parts[1], "used_mib": int(parts[2]),
                                 "total_mib": int(parts[3])})
            report["nvidia_smi"] = rows
        else:
            report["notes"].append("nvidia-smi rc=%d: %s"
                                   % (proc.returncode, proc.stderr.strip()[:120]))
    except Exception as exc:  # noqa: BLE001
        report["notes"].append("nvidia-smi unavailable: %s" % exc)

    try:
        request = urllib.request.Request(
            model_client.DEFAULT_BASE_URL + "/api/version", method="GET")
        with urllib.request.urlopen(request, timeout=10) as response:
            report["ollama_version"] = json.loads(
                response.read().decode("utf-8")).get("version")
    except Exception as exc:  # noqa: BLE001
        report["notes"].append("ollama unreachable: %s" % exc)

    report["confirmed"] = bool(report["nvidia_smi"]) or bool(report["device_nodes"])
    if not report["confirmed"]:
        report["notes"].append(
            "no direct GPU evidence from this shell (likely a sandbox masking "
            "/dev/nvidia*); GPU use will be verified after model load")
    return report


def verify_gpu_resident(model, base_url=None):
    """Authoritative GPU check: is the loaded model actually in VRAM?

    A model served entirely from system RAM still answers correctly but
    runs ~10x slower, which would silently wreck a 10,284-passage run.
    This is therefore a hard gate, not a warning.
    """
    base_url = base_url or model_client.DEFAULT_BASE_URL
    try:
        loaded = model_client.list_loaded_models(base_url=base_url)
    except Exception as exc:  # noqa: BLE001
        raise SafetyCheckFailed("cannot query resident models: %s" % exc)

    entry = next((m for m in loaded if m.get("name") == model), None)
    if entry is None:
        raise SafetyCheckFailed(
            "model %r is not resident after a successful call; cannot confirm "
            "GPU placement" % model)

    size_vram = entry.get("size_vram") or 0
    if size_vram <= 0:
        raise SafetyCheckFailed(
            "model %r reports 0 bytes in VRAM -- it is running on CPU. "
            "Refusing to continue with GPU inference unavailable." % model)
    return {
        "model": model,
        "size_vram_bytes": size_vram,
        "size_vram_gib": round(size_vram / float(1 << 30), 2),
        "context": entry.get("context"),
    }


# --------------------------------------------------------------------------
# candidate selection
# --------------------------------------------------------------------------

#: Topic priority for stratified pilot sampling.
_TOPIC_ORDER = ("translation", "capitalization", "interpretation",
                "terminology", "speaker")


def _stratified_selection(records, limit):
    """Round-robin across topics so a small pilot stays representative."""
    buckets = {}
    for record in records:
        topics = set(record.get("topics") or ())
        key = next((t for t in _TOPIC_ORDER if t in topics), "other")
        buckets.setdefault(key, []).append(record)
    for bucket in buckets.values():
        bucket.sort(key=lambda r: (-(r.get("score") or 0), r["path"], r["char_start"]))

    order = list(_TOPIC_ORDER) + ["other"]
    selected = []
    depth = 0
    while len(selected) < limit:
        added = False
        for key in order:
            bucket = buckets.get(key) or []
            if depth < len(bucket):
                selected.append(bucket[depth])
                added = True
                if len(selected) >= limit:
                    break
        if not added:
            break
        depth += 1
    return selected


def scan_findings(findings_dir=None):
    """Map a stored *chunk key* -> recorded pass state for this output root.

    Keyed on the content-addressed chunk key, not ``(sha256, chunk_id)``.
    A document's records can disagree with its document-level hash, and the
    key is the identity checkpointing actually uses -- keying on anything
    else makes a finished chunk look pending, so it is selected as work and
    then skipped, wasting batch slots.
    """
    directory = findings_dir or FINDINGS_DIR
    status = {}
    if not os.path.isdir(directory):
        return status
    for dirpath, _dirnames, filenames in os.walk(directory):
        for name in filenames:
            if not name.endswith(".json"):
                continue
            try:
                with open(os.path.join(dirpath, name), "r", encoding="utf-8") as handle:
                    document = json.load(handle)
            except (ValueError, OSError):
                continue
            for entry in (document.get("chunks") or {}).values():
                passes = entry.get("passes") or {}
                screen = passes.get("screen")
                if not screen or not screen.get("key"):
                    continue
                status[screen["key"]] = {
                    "screen": screen,
                    "escalate_key": (passes.get("escalate") or {}).get("key"),
                }
    return status


def dedupe_records(records):
    """Collapse chunks whose *content* is identical.

    85 sha256 values in this archive are shared by two byte-identical files
    saved under different names (170 documents in total).  Chunk identity is
    content-addressed, so those are the same research unit: analysing both
    would spend double the inference for exactly the same text.  The
    lexicographically first path becomes canonical and the rest are recorded
    as aliases on the findings document, so no passage is hidden.
    """
    best = {}
    for record in records:
        key = (record.get("sha256"), record.get("chunk_id"))
        current = best.get(key)
        if current is None or (record.get("path") or "") < (current.get("path") or ""):
            best[key] = record
    return list(best.values())


def content_aliases(index_path=INDEX_PATH):
    """``{sha256: [paths]}`` for content shared by more than one document."""
    by_hash = {}
    with open(index_path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            sha256 = record.get("sha256")
            if sha256:
                by_hash.setdefault(sha256, set()).add(record.get("path"))
    return {sha: sorted(paths) for sha, paths in by_hash.items() if len(paths) > 1}


def pending_chunks(status, records, stage, options=None):
    """Which of *records* still owe work for *stage*.

    ``both`` keeps chunks that are unscreened **or** screened-but-still-owing
    an escalation, so a batch that died during escalation is finished by the
    next batch instead of being skipped forever.
    """
    options = options if options is not None else MODEL_OPTIONS
    pending = []
    for record in records:
        screen_key = chunk_key(record.get("sha256"), record.get("chunk_id"),
                               SCREEN_MODEL, options)
        escalate_key = chunk_key(record.get("sha256"), record.get("chunk_id"),
                                 ESCALATE_MODEL, options)
        state = status.get(screen_key)

        if stage in ("screen", "both"):
            if state is None:
                pending.append(record)
                continue

        if stage in ("escalate", "both"):
            if state is None:
                continue
            needs, _reasons, _audited = escalation_decision(state.get("screen"))
            if needs and state.get("escalate_key") != escalate_key:
                pending.append(record)
    return pending


def pending_report(index_path=INDEX_PATH, collections=None, status=None,
                   stage="both", options=None):
    """Corpus counts for planning a bounded unattended batch (no inference)."""
    options = options if options is not None else MODEL_OPTIONS
    status = status if status is not None else {}
    every = []
    with open(index_path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if record.get("priority") != "high":
                continue
            if collections and not any(
                (record.get("collection") or "").startswith(c) for c in collections):
                continue
            every.append(record)

    raw_total = len(every)
    every = dedupe_records(every)

    screened = 0
    escalated = 0
    for record in every:
        key = chunk_key(record.get("sha256"), record.get("chunk_id"),
                        SCREEN_MODEL, options)
        state = status.get(key)
        if state is None:
            continue
        screened += 1
        if state.get("escalate_key"):
            escalated += 1

    return {
        "high_total": len(every),
        "high_records": raw_total,
        "duplicate_records": raw_total - len(every),
        "screened": screened,
        "escalated": escalated,
        "pending": len(pending_chunks(status, every, stage, options)),
        "stage": stage,
    }


def select_candidates(index_path=INDEX_PATH, limit=None, collections=None,
                      priority="high", stratified=False, status=None,
                      stage=None, options=None):
    """Best-first HIGH-priority candidates from the Milestone 1 index.

    With ``stratified`` the first *limit* records are chosen round-robin
    across topics instead of purely by score, so a small pilot reflects
    the whole HIGH-priority population rather than one dominant topic.

    With *status* and *stage*, already-satisfied chunks are removed
    **before** the limit is applied.  Filtering after the limit would make
    every batch after the first re-select the same top-N and do no work.
    """
    matching = []
    with open(index_path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if record.get("priority") != priority:
                continue
            if collections and not any(
                (record.get("collection") or "").startswith(c) for c in collections
            ):
                continue
            matching.append(record)

    matching = dedupe_records(matching)

    if status is not None and stage:
        matching = pending_chunks(status, matching, stage, options)

    if stratified:
        return _stratified_selection(
            matching, limit if limit is not None else len(matching))

    matching.sort(key=lambda r: (-(r.get("score") or 0), r["path"], r["char_start"]))
    if limit is not None:
        matching = matching[:limit]
    return matching


def group_by_document(records):
    grouped = {}
    for record in records:
        grouped.setdefault(record["path"], []).append(record)
    for chunks in grouped.values():
        chunks.sort(key=lambda r: r["char_start"])
    return grouped


# --------------------------------------------------------------------------
# document text (extract once per document per run)
# --------------------------------------------------------------------------

class DocumentCache:
    def __init__(self):
        self._text = {}
        self.extractions = 0

    def text(self, relative_path):
        if relative_path not in self._text:
            absolute = os.path.join(DOCUMENTS_DIR, relative_path)
            self._text[relative_path] = extractor.extract(absolute)["text"]
            self.extractions += 1
        return self._text[relative_path]

    def chunk(self, record):
        text = self.text(record["path"])
        start, end = record["char_start"], record["char_end"]
        piece = text[start:end]
        return {
            "chunk_id": record["chunk_id"], "index": None,
            "char_start": start, "char_end": end,
            "char_count": len(piece), "text": piece,
        }


def slugify(name):
    import re
    stem = os.path.splitext(name)[0]
    return re.sub(r"[^A-Za-z0-9]+", "-", stem).strip("-").lower()[:80] or "document"


def findings_path(relative_doc, sha256):
    collection = os.path.dirname(relative_doc)
    relative_collection = os.path.relpath(collection, "documents")
    if relative_collection.startswith(".."):
        relative_collection = ""
    target = os.path.join(FINDINGS_DIR, relative_collection)
    return os.path.join(target, "%s.%s.json" % (
        slugify(os.path.basename(relative_doc)), (sha256 or "nohash")[:8]))


def load_findings(path):
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (ValueError, OSError):
        return None


# --------------------------------------------------------------------------
# the run
# --------------------------------------------------------------------------

def plan_run(records, stage="both"):
    """Decide how many model calls the run would make (no inference)."""
    grouped = group_by_document(records)
    return {
        "documents": len(grouped),
        "chunks": sum(len(v) for v in grouped.values()),
        "stage": stage,
    }


def run(args):
    global FINDINGS_DIR, STATE_DIR, STATE_PATH, AUDIT_QUEUE_PATH

    started = utcnow()
    wall_start = time.time()

    stage = args.stage
    limit = args.limit
    dry_run = getattr(args, "dry_run", False)
    stratified = getattr(args, "stratified", False)
    verify_gpu = getattr(args, "verify_gpu", True)

    # A single run can never exceed the milestone ceiling, whatever the
    # caller asks for.  ``min`` is deliberate belt-and-braces: even if the
    # explicit refusal below were removed, the in-flight guard would still
    # stop the run at BULK_CEILING model calls.
    if args.max_chunks is not None and args.max_chunks > BULK_CEILING:
        raise BulkRefused(
            "max-chunks %d exceeds the Milestone 2 ceiling of %d; bulk "
            "inference is refused" % (args.max_chunks, BULK_CEILING)
        )
    if args.max_chunks is not None and args.max_chunks < 1:
        raise BulkRefused("max-chunks must be at least 1")
    if limit is not None and limit < 1:
        raise BulkRefused("limit must be at least 1")
    ceiling = (min(args.max_chunks, BULK_CEILING)
               if args.max_chunks is not None else BULK_CEILING)

    # --- keep pilot output away from production findings ----------------
    output_root = getattr(args, "output_root", None)
    if output_root:
        root = assert_inside_research(os.path.abspath(output_root))
        FINDINGS_DIR = os.path.join(root, "findings")
        STATE_DIR = os.path.join(root, "state")
        STATE_PATH = os.path.join(STATE_DIR, "pipeline_state.json")

    # Always derived from the *resolved* state directory.  Deriving it only
    # in the output_root branch would leave the audit queue pointing at
    # production whenever STATE_DIR is redirected some other way.
    AUDIT_QUEUE_PATH = os.path.join(STATE_DIR, "zero_finding_queue.jsonl")

    # strict allow-list for this run
    models = []
    if stage in ("screen", "both"):
        models.append(SCREEN_MODEL)
    if stage in ("escalate", "both"):
        models.append(ESCALATE_MODEL)
    model_client.LOCAL_MODEL_ALLOWLIST = tuple(models)

    # --- GPU availability gate (before any load) ------------------------
    gpu_report = check_gpu_environment()
    if not gpu_report["confirmed"] and not gpu_report["ollama_version"]:
        raise SafetyCheckFailed(
            "no GPU evidence and the local Ollama server is unreachable; "
            "refusing to start")

    status = scan_findings(FINDINGS_DIR)
    report = pending_report(args.index, args.collection or None, status, stage,
                            MODEL_OPTIONS)

    if getattr(args, "status", False):
        print("== pending work (no inference) ==")
        print("  output root     : %s"
              % (os.path.abspath(output_root) if output_root else RESEARCH_DIR))
        print("  HIGH passages   : %d distinct" % report["high_total"])
        print("  index records   : %d (%d identical-content duplicates collapsed)"
              % (report["high_records"], report["duplicate_records"]))
        print("  screened        : %d" % report["screened"])
        print("  escalated       : %d" % report["escalated"])
        print("  pending (%s): %d" % (stage, report["pending"]))
        print("  ceiling per run : %d" % BULK_CEILING)
        print("  audit queue     : %d queued passage(s)"
              % len(load_audit_queue()))
        return {"status": report}

    candidates = select_candidates(
        index_path=args.index, limit=limit, collections=args.collection or None,
        stratified=stratified, status=status, stage=stage,
        options=MODEL_OPTIONS,
    )
    grouped = group_by_document(candidates)
    plan = plan_run(candidates, stage)

    print("== Milestone 2 run plan ==")
    print("  pipeline        : %s" % PIPELINE_VERSION)
    print("  stage           : %s" % stage)
    print("  models          : %s" % ", ".join(models))
    print("  candidates      : %d HIGH chunks in %d documents%s"
          % (plan["chunks"], plan["documents"],
             " (stratified)" if stratified else ""))
    print("  ceiling         : %d chunks" % ceiling)
    print("  num_predict     : %d" % MODEL_OPTIONS["num_predict"])
    print("  options fp      : %s" % options_fingerprint(MODEL_OPTIONS))
    print("  findings dir    : %s" % FINDINGS_DIR)
    print("  state path      : %s" % STATE_PATH)
    print("  gpu confirmed   : %s" % gpu_report["confirmed"])
    if gpu_report["nvidia_smi"]:
        for row in gpu_report["nvidia_smi"]:
            print("    %-24s %d/%d MiB" % (row["gpu"], row["used_mib"], row["total_mib"]))
    if gpu_report["device_nodes"]:
        print("    device nodes    : %s" % ", ".join(gpu_report["device_nodes"]))
    for note in gpu_report["notes"]:
        print("    note            : %s" % note)

    if args.dry_run:
        print("  DRY RUN: no model calls made")
        return {"dry_run": True, "plan": plan, "models": models}

    state = {
        "schema_version": STATE_SCHEMA,
        "pipeline_version": PIPELINE_VERSION,
        "prompt_version": PROMPT_VERSION,
        "options": MODEL_OPTIONS,
        "options_fingerprint": options_fingerprint(MODEL_OPTIONS),
        "models": models,
        "started_at": started,
        "stage": stage,
        "counters": {
            "documents": 0, "chunks_screened": 0, "chunks_escalated": 0,
            "chunks_skipped": 0, "escalation_pending": 0,
            "verified": 0, "quarantined": 0,
            "document_only": 0, "audited": 0, "errors": 0,
        },
        "errors": [],
        "model_lifecycle": [],
        "gpu_environment": gpu_report,
        "gpu_verification": {},
        "model_release": [],
        "output_root": os.path.abspath(output_root) if output_root else RESEARCH_DIR,
    }

    cache = DocumentCache()
    model_calls = 0

    # Byte-identical documents share a content hash and are analysed once.
    # Their other filenames are recorded on the findings so a reviewer can
    # still find every path the research covers.
    alias_map = content_aliases(args.index)

    # A model recorded in this output root's own state was loaded by *this*
    # pipeline, so it is provably ours and may be released on switch.
    # Anything else resident is foreign and refuses the run.
    prior_state = load_findings(STATE_PATH) or {}
    owned = set(prior_state.get("owned_models") or ())
    for entry in prior_state.get("model_lifecycle") or ():
        if isinstance(entry, dict) and entry.get("model"):
            owned.add(entry["model"])
    if owned:
        print("  reclaiming prior-run models: %s" % ", ".join(sorted(owned)),
              flush=True)

    # Passages already set aside for recall review.  Loaded so a resumed run
    # never appends a duplicate audit entry for the same chunk.
    audited_keys = audit_queue_keys(load_audit_queue())
    if audited_keys:
        print("  audit queue already holds %d passage(s)" % len(audited_keys),
              flush=True)

    def flush():
        state["updated_at"] = utcnow()
        state["counters"]["model_calls"] = model_calls
        state["owned_models"] = sorted(owned)
        write_json(STATE_PATH, state)

    def finish_models():
        """Release models this run loaded so the next run is not blocked."""
        if getattr(args, "keep_models", False):
            state["owned_models"] = sorted(owned)
            return
        for name in sorted(owned):
            state["model_release"].append(
                {"model": name, "released": bool(release_model(name))})
        owned.clear()
        state["owned_models"] = []

    def confirm_gpu(model):
        """Hard gate: the loaded model must actually be in VRAM."""
        if not verify_gpu or model in state["gpu_verification"]:
            return
        info = verify_gpu_resident(model)
        state["gpu_verification"][model] = info
        print("    GPU OK: %s resident in %.2f GiB VRAM"
              % (model, info["size_vram_gib"]), flush=True)

    try:
        # ---------------- pass 1: screen -------------------------------
        if stage in ("screen", "both"):
            lifecycle = ensure_model_ready(SCREEN_MODEL, owned,
                                           release_owned=args.release_owned)
            state["model_lifecycle"].append({"model": SCREEN_MODEL, **lifecycle})
            owned.add(SCREEN_MODEL)
            flush()

            for path, chunks in sorted(grouped.items()):
                target = findings_path(path, chunks[0]["sha256"])
                document = load_findings(target) or {
                    "schema_version": FINDINGS_SCHEMA,
                    "pipeline_version": PIPELINE_VERSION,
                    "document": path,
                    "sha256": chunks[0]["sha256"],
                    "collection": chunks[0].get("collection"),
                    "prompt_version": PROMPT_VERSION,
                    "options_fingerprint": options_fingerprint(MODEL_OPTIONS),
                    "chunks": {},
                }
                document.setdefault("aliases", alias_map.get(chunks[0]["sha256"], []))
                document.setdefault("chunks", {})
                document_text = None
                changed = False

                for record in chunks:
                    entry = document["chunks"].get(record["chunk_id"])
                    expected = chunk_key(record["sha256"], record["chunk_id"],
                                         SCREEN_MODEL, MODEL_OPTIONS)
                    if entry and entry.get("passes", {}).get("screen", {}).get("key") == expected:
                        # Already screened.  This candidate may still be here
                        # for its *second* pass (a run that died during
                        # escalation re-selects it), which pass 2 will run --
                        # that is legitimate work, not a skipped chunk.
                        awaiting = False
                        if stage == "both":
                            needs, _triggers, _audited = escalation_decision(
                                entry["passes"]["screen"])
                            escalate_expected = chunk_key(
                                record["sha256"], record["chunk_id"],
                                ESCALATE_MODEL, MODEL_OPTIONS)
                            awaiting = needs and (entry.get("passes", {})
                                                  .get("escalate", {})
                                                  .get("key")) != escalate_expected
                        if awaiting:
                            state["counters"]["escalation_pending"] += 1
                            print("    hold   %-8s %s  (screened; second pass owed)"
                                  % (record["chunk_id"],
                                     os.path.basename(path)[:40]), flush=True)
                        else:
                            state["counters"]["chunks_skipped"] += 1
                            print("    skip   %-8s %s  (already complete)"
                                  % (record["chunk_id"],
                                     os.path.basename(path)[:40]), flush=True)
                        continue
                    if model_calls >= ceiling:
                        raise BulkRefused(
                            "chunk ceiling of %d reached; stopping before bulk "
                            "inference" % ceiling)

                    if document_text is None:
                        document_text = cache.text(path)
                    chunk = cache.chunk(record)

                    entry = entry or {
                        "chunk_id": record["chunk_id"],
                        "char_start": record["char_start"],
                        "char_end": record["char_end"],
                        "char_count": record["char_count"],
                        "priority": record.get("priority"),
                        "topics": record.get("topics"),
                        "score": record.get("score"),
                        "passes": {},
                    }

                    prompt = runner.build_prompt(chunk, path)
                    try:
                        response = call_model(prompt, SCREEN_MODEL, MODEL_OPTIONS,
                                              args.timeout, args.attempts, args.keep_alive)
                    except Exception as exc:  # noqa: BLE001
                        state["counters"]["errors"] += 1
                        state["errors"].append({
                            "stage": "screen", "path": path,
                            "chunk_id": record["chunk_id"],
                            "error": "%s: %s" % (type(exc).__name__, exc),
                        })
                        if state["counters"]["errors"] >= args.max_failures:
                            raise PipelineError(
                                "failure ceiling reached (%d); state saved"
                                % state["counters"]["errors"])
                        continue

                    model_calls += 1
                    confirm_gpu(SCREEN_MODEL)
                    analysis = analyse_response(response["response"], chunk, document_text)
                    analysis.update({
                        "key": expected, "model": SCREEN_MODEL,
                        "options_fingerprint": options_fingerprint(MODEL_OPTIONS),
                        "wall_seconds": round(response["wall_seconds"], 3),
                        "eval_count": response.get("eval_count"),
                        "prompt_eval_count": response.get("prompt_eval_count"),
                        "analysed_at": utcnow(),
                    })
                    entry["passes"]["screen"] = analysis
                    document["chunks"][record["chunk_id"]] = entry
                    changed = True

                    state["counters"]["chunks_screened"] += 1
                    state["counters"]["verified"] += len(analysis["verified"])
                    state["counters"]["quarantined"] += len(analysis["quarantined"])
                    state["counters"]["document_only"] += (
                        analysis["provenance"]["document_only"]
                        + analysis["provenance"]["document_only_normalized"])

                    # A passage the screen pass found nothing for, and which
                    # the policy will not escalate, is queued for recall
                    # review.  Written before the findings checkpoint so a
                    # crash can never mark a chunk done while losing its
                    # place in the queue.
                    needs_escalation, _triggered, audited = escalation_decision(analysis)
                    audit_key = (record.get("sha256"), record.get("chunk_id"))
                    if audited and not needs_escalation:
                        if audit_key not in audited_keys:
                            record_audit(record, analysis, audited)
                            audited_keys.add(audit_key)
                        state["counters"]["audited"] += 1

                    # per-chunk checkpoint
                    document["updated_at"] = utcnow()
                    write_json(target, document)
                    flush()
                    print("    screen %-8s %s  +%d verified  %d quarantined"
                          % (record["chunk_id"], os.path.basename(path)[:40],
                             len(analysis["verified"]), len(analysis["quarantined"])),
                          flush=True)

                state["counters"]["documents"] += 1
                if changed:
                    document["updated_at"] = utcnow()
                    write_json(target, document)
                flush()

        # ---------------- pass 2: escalate -----------------------------
        if stage in ("escalate", "both"):
            lifecycle = ensure_model_ready(ESCALATE_MODEL, owned,
                                           release_owned=args.release_owned)
            state["model_lifecycle"].append({"model": ESCALATE_MODEL, **lifecycle})
            owned.add(ESCALATE_MODEL)
            flush()

            for path, chunks in sorted(grouped.items()):
                target = findings_path(path, chunks[0]["sha256"])
                document = load_findings(target)
                if document is None:
                    continue
                document_text = None

                for record in chunks:
                    entry = document["chunks"].get(record["chunk_id"])
                    if entry is None:
                        continue
                    screen = entry.get("passes", {}).get("screen")
                    needs_escalation, reasons, audited = escalation_decision(screen)
                    if not needs_escalation:
                        # In a "both" run the screen stage already counted this
                        # passage; only an escalate-only run counts it here.
                        if audited and stage == "escalate":
                            state["counters"]["audited"] += 1
                        continue

                    expected = chunk_key(record["sha256"], record["chunk_id"],
                                         ESCALATE_MODEL, MODEL_OPTIONS)
                    if entry.get("passes", {}).get("escalate", {}).get("key") == expected:
                        state["counters"]["chunks_skipped"] += 1
                        print("    skip   %-8s %s  (already escalated)"
                              % (record["chunk_id"], os.path.basename(path)[:40]),
                              flush=True)
                        continue
                    if model_calls >= ceiling:
                        raise BulkRefused(
                            "chunk ceiling of %d reached; stopping before bulk "
                            "inference" % ceiling)

                    if document_text is None:
                        document_text = cache.text(path)
                    chunk = cache.chunk(record)
                    prompt = runner.build_prompt(chunk, path)

                    try:
                        response = call_model(prompt, ESCALATE_MODEL, MODEL_OPTIONS,
                                              args.timeout, args.attempts, args.keep_alive)
                    except Exception as exc:  # noqa: BLE001
                        state["counters"]["errors"] += 1
                        state["errors"].append({
                            "stage": "escalate", "path": path,
                            "chunk_id": record["chunk_id"],
                            "error": "%s: %s" % (type(exc).__name__, exc),
                        })
                        if state["counters"]["errors"] >= args.max_failures:
                            raise PipelineError(
                                "failure ceiling reached (%d); state saved"
                                % state["counters"]["errors"])
                        continue

                    model_calls += 1
                    confirm_gpu(ESCALATE_MODEL)
                    analysis = analyse_response(response["response"], chunk, document_text)
                    analysis.update({
                        "key": expected, "model": ESCALATE_MODEL,
                        "options_fingerprint": options_fingerprint(MODEL_OPTIONS),
                        "wall_seconds": round(response["wall_seconds"], 3),
                        "eval_count": response.get("eval_count"),
                        "prompt_eval_count": response.get("prompt_eval_count"),
                        "analysed_at": utcnow(),
                    })
                    entry["passes"]["escalate"] = analysis
                    entry["escalated"] = True
                    entry["escalation_reasons"] = reasons

                    state["counters"]["chunks_escalated"] += 1
                    state["counters"]["verified"] += len(analysis["verified"])
                    state["counters"]["quarantined"] += len(analysis["quarantined"])
                    state["counters"]["document_only"] += (
                        analysis["provenance"]["document_only"]
                        + analysis["provenance"]["document_only_normalized"])

                    document["updated_at"] = utcnow()
                    write_json(target, document)
                    flush()
                    print("    escalate %-8s %s  reasons=%s"
                          % (record["chunk_id"], os.path.basename(path)[:40],
                             ",".join(reasons)), flush=True)

    except (BulkRefused, ForeignModelResident, PipelineError) as exc:
        # An aborted run must never destroy a previous good summary.
        entry = {
            "aborted_at": utcnow(),
            "reason": str(exc),
            "stage": stage,
            "counters_this_run": dict(state["counters"]),
        }
        aborts = list(prior_state.get("aborts") or [])
        aborts.append(entry)
        for key in ("counters", "finished_at", "wall_seconds", "started_at",
                    "model_lifecycle", "gpu_environment", "gpu_verification"):
            if prior_state.get(key) is not None:
                state[key] = prior_state[key]
        state["aborts"] = aborts[-20:]
        state["last_abort"] = entry
        finish_models()
        write_json(STATE_PATH, state)
        print("\n!! run stopped: %s" % exc)
        print("   state saved to %s (previous run summary preserved)" % STATE_PATH)
        raise

    state["finished_at"] = utcnow()
    state["wall_seconds"] = round(time.time() - wall_start, 1)
    state["counters"]["model_calls"] = model_calls
    finish_models()
    write_json(STATE_PATH, state)

    print("\n== Milestone 2 run complete ==")
    for key, value in sorted(state["counters"].items()):
        print("  %-18s %s" % (key, value))
    print("  wall_seconds       %s" % state["wall_seconds"])
    return state


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Bounded resumable local-only two-pass research runner.")
    parser.add_argument("--stage", choices=("screen", "escalate", "both"),
                        default="both")
    parser.add_argument("--limit", type=int, default=25,
                        help="max HIGH candidates to consider")
    parser.add_argument("--max-chunks", type=int, default=None,
                        help="hard model-call ceiling (<= %d)" % BULK_CEILING)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--attempts", type=int, default=DEFAULT_ATTEMPTS)
    parser.add_argument("--max-failures", type=int, default=5)
    parser.add_argument("--keep-alive", default="10m")
    parser.add_argument("--collection", action="append", default=None,
                        help="restrict to collection prefix (repeatable)")
    parser.add_argument("--index", default=INDEX_PATH)
    parser.add_argument("--output-root", default=None,
                        help="write findings/state under this directory, keeping "
                             "a pilot separate from production findings")
    parser.add_argument("--stratified", action="store_true",
                        help="sample across topics rather than purely by score")
    parser.add_argument("--verify-gpu", dest="verify_gpu", action="store_true",
                        default=True,
                        help="hard-fail if a loaded model is not resident in VRAM")
    parser.add_argument("--no-verify-gpu", dest="verify_gpu", action="store_false",
                        help="skip the post-load VRAM gate (tests only)")
    parser.add_argument("--keep-models", action="store_true", default=False,
                        help="leave loaded models resident at the end of the run "
                             "(default: release the models this run loaded)")
    parser.add_argument("--release-owned", action="store_true", default=True,
                        help="release only models this run loaded when switching")
    parser.add_argument("--status", action="store_true", default=False,
                        help="print pending corpus work for this output root "
                             "and exit without inference")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the plan and exit without inference")
    args = parser.parse_args(argv)
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
