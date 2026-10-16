#!/usr/bin/env python3
"""Milestone 0 orchestrator for the GD Bible Research pipeline.

One document, one chunk, one model call, one atomically-written findings
file, and a resume path that proves completed work is not repeated.

Design notes
------------
* **Nothing in the archive is modified.**  The pipeline only ever *reads*
  ``documents/``; all output lands in a new sibling tree,
  ``PCOG-Research-Archive/research/``.
* **Resume is content-addressed.**  A document is considered done only
  when its SHA-256 *and* the extractor, chunker, prompt and model
  identities all still match, and the findings file still exists.  This
  fixes a weakness in the existing collector, where resumption trusts any
  non-empty file and never re-checks the hash.
* **Atomic writes** reuse the collector's established pattern
  (``run_gd_bible_priority_download_v2.py:62``): write a temporary file,
  fsync it, then ``os.replace`` it into position.
* Milestone 0 analyses exactly one chunk.  Bulk processing is out of
  scope and is refused by the ``--max-model-calls`` ceiling.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gd_research_chunk as chunker          # noqa: E402
import gd_research_extract as extractor      # noqa: E402
import gd_research_model as model_client     # noqa: E402
import gd_research_verify as verifier        # noqa: E402

ARCHIVE_ROOT = os.environ.get("GD_ARCHIVE_ROOT", "/home/liongateos/PCOG-Research-Archive")
DOCUMENTS_DIR = os.path.join(ARCHIVE_ROOT, "documents")
RESEARCH_DIR = os.path.join(ARCHIVE_ROOT, "research")
FINDINGS_DIR = os.path.join(RESEARCH_DIR, "findings")
EXTRACTED_DIR = os.path.join(RESEARCH_DIR, "extracted")
STATE_DIR = os.path.join(RESEARCH_DIR, "state")
STATE_PATH = os.path.join(STATE_DIR, "research_state.json")
INVENTORY_PATH = os.path.join(ARCHIVE_ROOT, "metadata", "corpus_inventory.json")

DEFAULT_DOCUMENT = (
    "documents/WCG/HWA Letters/Bulletin/"
    "Bulletin 1973 07 12 (HWA) - Letter to the Ministry (A NEW DAY for the WORK.doc"
)

PROMPT_VERSION = "analyse-v1"
STATE_SCHEMA = "gd-research-state/1"

#: Milestone 0 analyses a single chunk.  The ceiling makes that a property
#: of the program rather than a promise in a document.
MAX_MODEL_CALLS = 1

MODEL_OPTIONS = {
    "num_predict": 700,
    "num_ctx": 8192,
    "temperature": 0,
    "top_p": 0.9,
}

PROMPT_TEMPLATE = """You analyse documents for a Bible-translation research archive. \
Report statements about Bible translation, wording, capitalization, corrections, or \
preferred terminology, and note any scripture references that appear.

Return ONLY JSON exactly matching this shape:
{{"findings":[{{"topic":"translation|wording|capitalization|terminology|scripture",\
"quote":"exact text copied from the excerpt","scripture_refs":["Book Chapter:Verse"],\
"speaker":"HWA|GF|other|unknown","note":"short explanation",\
"confidence":"high|medium|low"}}],"no_findings":false}}

Rules:
1. "quote" MUST be copied verbatim from the excerpt, character for character, \
including capitalization and punctuation. Never paraphrase, translate, repair or \
shorten a quotation.
2. Report a finding only when the excerpt genuinely discusses one of the topics.
3. Use an empty "scripture_refs" array when no reference is given.
4. If nothing is relevant, return {{"findings":[],"no_findings":true}}.

DOCUMENT: {document}
EXCERPT (characters {char_start}-{char_end}):
{excerpt}
"""


# --------------------------------------------------------------------------
# small utilities (patterns reused from the existing collector)
# --------------------------------------------------------------------------

def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path, chunk_bytes=1024 * 1024):
    """SHA-256 of a file's raw bytes, 1 MiB at a time.

    Mirrors the collector's existing hashing loop
    (``build_corpus_inventory.py:17-21``) so hashes stay comparable with
    ``metadata/corpus_inventory.json``.
    """
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(chunk_bytes), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path, default):
    """Load JSON, returning *default* when the file is absent or corrupt."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return default


def atomic_write_json(path, payload):
    """Write JSON atomically: temp file in the same directory, then replace."""
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    temporary = "%s.tmp.%d" % (path, os.getpid())
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    try:
        descriptor = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError:
        pass
    return path


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# chunk selection
# --------------------------------------------------------------------------

#: Highest-precision signals first: explicit translation / wording /
#: terminology discussion, then divine-name and scripture usage.  This is
#: the seed of the triage stage that a later milestone has to scale up.
SIGNAL_TIERS = (
    ("translation-or-wording",
     re.compile(r"translat|capitali[sz]|terminolog|\bwording\b|King James|\bKJV\b|"
                r"Revised Standard|Moffatt|Ferrar", re.IGNORECASE)),
    ("scripture-or-divine-name",
     re.compile(r"\b(?:I|II|III)?\s?(?:Chronicles|Kings|Samuel|Genesis|Exodus|Psalm|"
                r"Matthew|Mark|Luke|John|Romans|Hebrews|Revelation)\s+\d+|"
                r"\bthe Eternal\b|\bLORD\b", re.IGNORECASE)),
)


def select_chunk(chunks, requested_index=None):
    """Choose which chunk to analyse.

    An explicit index wins.  Otherwise the highest-precision signal tier
    that matches decides; if nothing matches, chunk 0 is used.  Returns
    ``(chunk, reason)``.
    """
    if requested_index is not None:
        if not 0 <= requested_index < len(chunks):
            raise ValueError(
                "chunk index %d out of range (document has %d chunks)"
                % (requested_index, len(chunks))
            )
        return chunks[requested_index], "explicit index %d" % requested_index

    for tier_name, pattern in SIGNAL_TIERS:
        for chunk in chunks:
            if pattern.search(chunk["text"]):
                return chunk, "signal tier %r" % tier_name

    return chunks[0], "fallback: no signal matched, defaulting to chunk 0"


# --------------------------------------------------------------------------
# paths
# --------------------------------------------------------------------------

def slugify(name):
    stem = os.path.splitext(name)[0]
    slug = re.sub(r"[^A-Za-z0-9]+", "-", stem).strip("-").lower()
    return slug[:80] or "document"


def relative_document_path(document):
    """Return the document path relative to the archive root."""
    absolute = document if os.path.isabs(document) else os.path.join(ARCHIVE_ROOT, document)
    return os.path.relpath(absolute, ARCHIVE_ROOT)


def findings_path(relative_doc, sha256):
    collection = os.path.dirname(relative_doc)
    relative_collection = os.path.relpath(collection, "documents")
    if relative_collection.startswith(".."):
        relative_collection = ""
    target_dir = os.path.join(FINDINGS_DIR, relative_collection)
    filename = "%s.%s.json" % (slugify(os.path.basename(relative_doc)), sha256[:8])
    return os.path.join(target_dir, filename)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def build_prompt(chunk, relative_doc):
    return PROMPT_TEMPLATE.format(
        document=relative_doc,
        char_start=chunk["char_start"],
        char_end=chunk["char_end"],
        excerpt=chunk["text"],
    )


def run(args):
    summary = {
        "milestone": "0",
        "document": None,
        "status": None,
        "skipped": False,
        "skip_reason": None,
        "model_calls": 0,
        "findings_verified": 0,
        "findings_quarantined": 0,
        "errors": [],
        "warnings": [],
    }

    document = args.document
    absolute = document if os.path.isabs(document) else os.path.join(ARCHIVE_ROOT, document)
    absolute = os.path.abspath(absolute)

    if not os.path.isfile(absolute):
        summary["status"] = "error"
        summary["errors"].append("document not found: %s" % absolute)
        return summary

    relative_doc = relative_document_path(absolute)
    summary["document"] = relative_doc

    if not relative_doc.startswith("documents" + os.sep):
        summary["status"] = "error"
        summary["errors"].append(
            "refusing to process a path outside the archive documents tree"
        )
        return summary

    # ---- identity -------------------------------------------------------
    digest = sha256_file(absolute)
    size = os.path.getsize(absolute)
    summary["sha256"] = digest
    summary["bytes"] = size

    inventory = load_json(INVENTORY_PATH, None)
    if isinstance(inventory, list):
        # corpus_inventory.json stores paths relative to documents/, not to
        # the archive root (e.g. "GRF Letters/1999/3 Sept 99.doc").
        inventory_key = os.path.relpath(absolute, DOCUMENTS_DIR)
        recorded = next(
            (row for row in inventory if row.get("path") == inventory_key), None
        )
        if recorded is None:
            summary["warnings"].append("document is absent from corpus_inventory.json")
        elif recorded.get("sha256") != digest:
            summary["warnings"].append(
                "SHA-256 disagrees with corpus_inventory.json "
                "(inventory=%s...) - the archive may have changed"
                % str(recorded.get("sha256"))[:12]
            )
        else:
            summary["inventory_sha256_agrees"] = True

    target_chunk_count = None
    findings_abs = findings_path(relative_doc, digest)

    # ---- state / resume -------------------------------------------------
    state = load_json(STATE_PATH, None)
    if not isinstance(state, dict) or state.get("schema_version") != STATE_SCHEMA:
        state = {"schema_version": STATE_SCHEMA, "documents": {}, "runs": []}
    state.setdefault("documents", {})
    state.setdefault("runs", [])

    entry = state["documents"].get(relative_doc) or {}
    expected = {
        "sha256": digest,
        "extractor_version": extractor.EXTRACTOR_VERSION,
        "chunker_version": chunker.CHUNKER_VERSION,
        "prompt_version": PROMPT_VERSION,
        "model": args.model,
    }
    fingerprint_ok = all(entry.get(key) == value for key, value in expected.items())
    findings_present = os.path.isfile(findings_abs)

    if not args.force and fingerprint_ok and findings_present and entry.get("status") == "complete":
        summary["status"] = "skipped"
        summary["skipped"] = True
        summary["skip_reason"] = (
            "unchanged sha256 + matching extractor/chunker/prompt/model and findings file present"
        )
        summary["model_calls"] = 0
        summary["findings_file"] = os.path.relpath(findings_abs, ARCHIVE_ROOT)
        summary["previous_run"] = {
            "completed_at": entry.get("completed_at"),
            "findings_verified": entry.get("findings_verified"),
        }
        _record_run(state, summary)
        atomic_write_json(STATE_PATH, state)
        return summary

    # ---- extraction -----------------------------------------------------
    try:
        extracted = extractor.extract(absolute)
    except extractor.UnsupportedFormat as exc:
        summary["status"] = "unsupported"
        summary["errors"].append("unsupported: %s" % exc)
        _record_run(state, summary)
        atomic_write_json(STATE_PATH, state)
        return summary
    except Exception as exc:  # noqa: BLE001
        summary["status"] = "extract_failed"
        summary["errors"].append("%s: %s" % (type(exc).__name__, exc))
        _record_run(state, summary)
        atomic_write_json(STATE_PATH, state)
        return summary

    text = extracted["text"]
    summary["container"] = extracted["container"]
    summary["extractor"] = extracted["extractor"]
    summary["extractor_version"] = extracted["extractor_version"]
    summary["char_count"] = extracted["char_count"]

    chunks = chunker.chunk_text(text, chunk_chars=args.chunk_chars)
    summary["chunk_count"] = len(chunks)
    target_chunk_count = len(chunks)

    # persist the extraction so the run is reproducible from disk
    extracted_abs = os.path.join(
        EXTRACTED_DIR, "%s.%s.txt" % (slugify(os.path.basename(relative_doc)), digest[:8])
    )
    os.makedirs(os.path.dirname(extracted_abs), exist_ok=True)
    with open(extracted_abs, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    summary["extracted_file"] = os.path.relpath(extracted_abs, ARCHIVE_ROOT)
    summary["extracted_sha256"] = sha256_text(text)

    requested = None if args.chunk_index is None or args.chunk_index < 0 else args.chunk_index
    chunk, reason = select_chunk(chunks, requested)
    summary["chunk_selected"] = chunk["chunk_id"]
    summary["chunk_selection_reason"] = reason
    summary["chunk_char_start"] = chunk["char_start"]
    summary["chunk_char_end"] = chunk["char_end"]

    prompt = build_prompt(chunk, relative_doc)
    summary["prompt_version"] = PROMPT_VERSION
    summary["prompt_sha256"] = sha256_text(prompt)

    if args.dry_run:
        summary["status"] = "dry_run"
        summary["model_calls"] = 0
        summary["model_response_preview"] = None
        return summary

    # ---- local-model safety gate ---------------------------------------
    try:
        workload = model_client.check_competing_workloads(
            args.model, base_url=args.base_url, allow_evict=args.allow_evict
        )
        summary["workload_check"] = workload
    except model_client.CloudModelRejected as exc:
        summary["status"] = "rejected"
        summary["errors"].append(str(exc))
        return summary
    except model_client.ModelUnavailable as exc:
        summary["status"] = "model_unavailable"
        summary["errors"].append(str(exc))
        return summary

    if MAX_MODEL_CALLS < 1:
        summary["status"] = "refused"
        summary["errors"].append("model-call ceiling is zero")
        return summary

    # ---- the single model call -----------------------------------------
    started = utcnow()
    try:
        result = model_client.generate_json(
            prompt,
            args.model,
            base_url=args.base_url,
            options=MODEL_OPTIONS,
            timeout=args.timeout,
            attempts=args.attempts,
            keep_alive=args.keep_alive,
        )
    except model_client.ModelError as exc:
        summary["status"] = "model_failed"
        summary["errors"].append(str(exc))
        summary["model_calls"] = 1
        _record_run(state, summary)
        atomic_write_json(STATE_PATH, state)
        return summary

    summary["model_calls"] = 1
    summary["model"] = result["model"]
    summary["model_timing"] = {
        "wall_seconds": round(result["wall_seconds"], 2),
        "load_seconds": round(result["load_seconds"], 2),
        "prompt_eval_count": result["prompt_eval_count"],
        "prompt_eval_seconds": round(result["prompt_eval_seconds"], 3),
        "eval_count": result["eval_count"],
        "eval_seconds": round(result["eval_seconds"], 3),
        "attempts": result["attempts"],
    }
    if result["eval_seconds"]:
        summary["model_timing"]["generation_tokens_per_second"] = round(
            (result["eval_count"] or 0) / result["eval_seconds"], 1
        )

    raw = result["response"]

    # ---- validation + verification --------------------------------------
    try:
        payload = json.loads(raw)
        summary["json_valid"] = True
    except ValueError as exc:
        payload = None
        summary["json_valid"] = False
        summary["errors"].append("model response is not valid JSON: %s" % exc)

    accepted, schema_errors = verifier.validate_response(payload) if payload is not None else ([], [])
    summary["schema_errors"] = schema_errors

    verified, quarantined = verifier.verify_findings(accepted, chunk, text)
    summary["findings_verified"] = len(verified)
    summary["findings_quarantined"] = len(quarantined)

    findings_payload = {
        "schema_version": verifier.SCHEMA_VERSION,
        "source": {
            "path": relative_doc,
            "absolute_path": absolute,
            "sha256": digest,
            "bytes": size,
            "collection": os.path.dirname(relative_doc),
            "container": extracted["container"],
            "extractor": extracted["extractor"],
            "extractor_version": extracted["extractor_version"],
            "char_count": extracted["char_count"],
            "extracted_sha256": summary["extracted_sha256"],
            "extracted_cache": summary["extracted_file"],
        },
        "run": {
            "model": result["model"],
            "model_reported": result["model_reported"],
            "options": MODEL_OPTIONS,
            "prompt_version": PROMPT_VERSION,
            "prompt_sha256": summary["prompt_sha256"],
            "chunker_version": chunker.CHUNKER_VERSION,
            "chunk_chars": args.chunk_chars,
            "started_at": started,
            "completed_at": utcnow(),
        },
        "chunk": {
            "chunk_id": chunk["chunk_id"],
            "char_start": chunk["char_start"],
            "char_end": chunk["char_end"],
            "char_count": chunk["char_count"],
            "selection_reason": reason,
            "chunks_total_in_document": len(chunks),
        },
        "chunks_unanalysed": [
            other["chunk_id"] for other in chunks if other["chunk_id"] != chunk["chunk_id"]
        ],
        "model_response_raw": raw,
        "findings": verified,
        "quarantined": quarantined,
        "doc_status": "analysed" if verified else "no_findings",
    }

    atomic_write_json(findings_abs, findings_payload)
    summary["findings_file"] = os.path.relpath(findings_abs, ARCHIVE_ROOT)
    summary["status"] = "complete"
    summary["doc_status"] = findings_payload["doc_status"]

    # ---- checkpoint ------------------------------------------------------
    now = utcnow()
    state["documents"][relative_doc] = {
        **expected,
        "bytes": size,
        "container": extracted["container"],
        "extractor": extracted["extractor"],
        "extracted_sha256": summary["extracted_sha256"],
        "chunk_count": len(chunks),
        "analysed_chunks": [chunk["chunk_id"]],
        "status": "complete",
        "findings_file": summary["findings_file"],
        "findings_verified": len(verified),
        "findings_quarantined": len(quarantined),
        "model_calls": 1,
        "first_run_at": entry.get("first_run_at", now),
        "completed_at": now,
    }
    _record_run(state, summary)
    atomic_write_json(STATE_PATH, state)
    return summary


def _record_run(state, summary):
    record = {
        "at": utcnow(),
        "document": summary.get("document"),
        "status": summary.get("status"),
        "skipped": summary.get("skipped"),
        "model_calls": summary.get("model_calls"),
        "findings_verified": summary.get("findings_verified"),
        "findings_quarantined": summary.get("findings_quarantined"),
    }
    state.setdefault("runs", []).append(record)
    state["updated_at"] = record["at"]


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="GD Bible Research pipeline - Milestone 0 (one document, one chunk)."
    )
    parser.add_argument("--document", default=DEFAULT_DOCUMENT,
                        help="document path, absolute or relative to the archive root")
    parser.add_argument("--model", default=model_client.LOCAL_MODEL_ALLOWLIST[0],
                        help="local model name (cloud-tagged names are rejected)")
    parser.add_argument("--base-url", default=model_client.DEFAULT_BASE_URL)
    parser.add_argument("--chunk-index", type=int, default=-1,
                        help="-1 selects automatically by research signal")
    parser.add_argument("--chunk-chars", type=int, default=chunker.DEFAULT_CHUNK_CHARS)
    parser.add_argument("--timeout", type=int, default=model_client.DEFAULT_TIMEOUT)
    parser.add_argument("--attempts", type=int, default=model_client.DEFAULT_ATTEMPTS)
    parser.add_argument("--keep-alive", default="2m")
    parser.add_argument("--force", action="store_true",
                        help="reprocess even when the fingerprint matches")
    parser.add_argument("--allow-evict", action="store_true",
                        help="accept evicting another resident local model")
    parser.add_argument("--dry-run", action="store_true",
                        help="extract and chunk, but make no model call")
    args = parser.parse_args(argv)

    summary = run(args)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary.get("status") in {"complete", "skipped", "dry_run"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
