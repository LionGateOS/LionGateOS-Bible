#!/usr/bin/env python3
"""Milestone 1: corpus-wide CPU extraction and research triage.

This stage **never contacts a model**.  It walks the archive inventory,
extracts text with the Milestone 0 extractors, ranks every chunk against
the research goals, and writes a searchable candidate index plus a
resumable state file.  Milestone 2 will consume the index; nothing here
spends GPU time.

Reuse
-----
Extraction, chunking and triage come from the verified Milestone 0
components (``gd_research_extract``, ``gd_research_chunk``,
``gd_research_triage``), and atomic-write / hashing helpers are imported
from ``gd_research_run`` rather than reimplemented.

Resumability
------------
``research/index/triage_state.json`` records, per document, its SHA-256
plus the extractor / chunker / triage versions that produced its results.
A document is skipped only when all of those still match, so newly
downloaded files and edited files are picked up incrementally on the next
run while everything already done is left alone.

Resource discipline
-------------------
Documents are handled one at a time; candidate records stream straight to
a JSONL file; the final ranking pass keeps only a small index of offsets
in memory rather than the records themselves; snippets per chunk are
capped.  Peak memory does not scale with corpus size.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gd_research_chunk as chunker            # noqa: E402
import gd_research_extract as extractor        # noqa: E402
import gd_research_run as runner               # noqa: E402
import gd_research_triage as triage            # noqa: E402

ARCHIVE_ROOT = os.environ.get("GD_ARCHIVE_ROOT", "/home/liongateos/PCOG-Research-Archive")
DOCUMENTS_DIR = os.path.join(ARCHIVE_ROOT, "documents")
RESEARCH_DIR = os.path.join(ARCHIVE_ROOT, "research")
INDEX_DIR = os.path.join(RESEARCH_DIR, "index")
INVENTORY_PATH = os.path.join(ARCHIVE_ROOT, "metadata", "corpus_inventory.json")

CHUNK_INDEX_PATH = os.path.join(INDEX_DIR, "chunk_index.jsonl")
DOCUMENT_INDEX_PATH = os.path.join(INDEX_DIR, "document_index.json")
FAILURES_PATH = os.path.join(INDEX_DIR, "extraction_failures.json")
STATE_PATH = os.path.join(INDEX_DIR, "triage_state.json")
SUMMARY_PATH = os.path.join(INDEX_DIR, "triage_summary.json")
TOP_PATH = os.path.join(INDEX_DIR, "top_candidates.json")
README_PATH = os.path.join(INDEX_DIR, "README.txt")


def configure_index_dir(index_dir):
    """Redirect every Milestone 1 output into one explicit directory."""
    global INDEX_DIR, CHUNK_INDEX_PATH, DOCUMENT_INDEX_PATH, FAILURES_PATH
    global STATE_PATH, SUMMARY_PATH, TOP_PATH, README_PATH

    INDEX_DIR = os.path.abspath(index_dir)
    CHUNK_INDEX_PATH = os.path.join(INDEX_DIR, "chunk_index.jsonl")
    DOCUMENT_INDEX_PATH = os.path.join(INDEX_DIR, "document_index.json")
    FAILURES_PATH = os.path.join(INDEX_DIR, "extraction_failures.json")
    STATE_PATH = os.path.join(INDEX_DIR, "triage_state.json")
    SUMMARY_PATH = os.path.join(INDEX_DIR, "triage_summary.json")
    TOP_PATH = os.path.join(INDEX_DIR, "top_candidates.json")
    README_PATH = os.path.join(INDEX_DIR, "README.txt")

STATE_SCHEMA = "gd-triage-state/1"
INDEX_SCHEMA = "gd-candidate-index/1"

#: Write the state file every N documents so an interrupted run keeps its work.
STATE_FLUSH_EVERY = 200

#: Calibration measured on this host during the verified Milestone 0 run
#: (document: Bulletin 1973 07 12, chunk c0002, 2,231 chars):
#:   803 prompt tokens evaluated in 0.756 s  -> 1062 tok/s
#:    99 tokens generated in 2.738 s         ->   36.2 tok/s
#:    load 5.82 s (once per run), wall 9.55 s
#: Chars-per-token 4.4 is the implied ratio for English prose here, and
#: the fixed template contributes ~296 tokens before the excerpt.
MODEL_CALIBRATION = {
    "model": "qwen3.6:27b",
    "prompt_tokens_per_second": 1062.0,
    "generation_tokens_per_second": 36.2,
    "chars_per_token": 4.4,
    "fixed_prompt_tokens": 296.0,
    "generation_tokens_observed": 99,
    "generation_tokens_cap": 700,
    "load_seconds_per_run": 5.82,
    "http_overhead_seconds_per_chunk": 0.05,
}


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------
# model-time estimation
# --------------------------------------------------------------------------

def estimate_seconds(chunk_count, mean_chunk_chars, generation_tokens):
    """Estimated wall-clock seconds to analyse *chunk_count* chunks.

    Uses the measured throughput of ``qwen3.6:27b`` on this host.  The
    model is loaded once per run, not once per chunk.
    """
    if chunk_count <= 0:
        return 0.0
    calibration = MODEL_CALIBRATION
    prompt_tokens = calibration["fixed_prompt_tokens"] + (
        mean_chunk_chars / calibration["chars_per_token"]
    )
    per_chunk = (
        prompt_tokens / calibration["prompt_tokens_per_second"]
        + generation_tokens / calibration["generation_tokens_per_second"]
        + calibration["http_overhead_seconds_per_chunk"]
    )
    return (
        calibration["load_seconds_per_run"]
        + chunk_count * per_chunk
    )


def estimate_block(chunk_count, mean_chunk_chars):
    calibration = MODEL_CALIBRATION
    prompt_tokens = calibration["fixed_prompt_tokens"] + (
        mean_chunk_chars / calibration["chars_per_token"]
    )
    typical = estimate_seconds(
        chunk_count, mean_chunk_chars, calibration["generation_tokens_observed"]
    )
    worst = estimate_seconds(
        chunk_count, mean_chunk_chars, calibration["generation_tokens_cap"]
    )
    return {
        "chunks": chunk_count,
        "prompt_tokens_per_chunk": round(prompt_tokens, 1),
        "estimated_prompt_tokens_total": int(prompt_tokens * chunk_count),
        "estimated_seconds_typical": round(typical, 1),
        "estimated_hours_typical": round(typical / 3600.0, 2),
        "estimated_seconds_worst_case": round(worst, 1),
        "estimated_hours_worst_case": round(worst / 3600.0, 2),
    }


# --------------------------------------------------------------------------
# index compaction (memory-bounded)
# --------------------------------------------------------------------------

def compact_index(path, allowed_documents, top_n):
    """Deduplicate, rank and atomically rewrite the JSONL candidate index.

    Keeps only an offset index in memory -- never the records themselves --
    so peak memory is independent of how many candidates there are.  The
    newest record for a ``(path, chunk_id)`` wins, which is what makes
    re-processing a document replace its earlier entries.
    """
    if not os.path.isfile(path):
        return {"records": 0, "documents": 0, "top": []}

    offsets = {}
    with open(path, "r", encoding="utf-8") as handle:
        while True:
            offset = handle.tell()
            line = handle.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue  # tolerate a torn final line from an interrupted run
            doc_path = record.get("path")
            if allowed_documents is not None and doc_path not in allowed_documents:
                continue
            offsets[(doc_path, record.get("chunk_id"))] = {
                "offset": offset,
                "score": record.get("score", 0),
                "path": doc_path,
                "char_start": record.get("char_start", 0),
            }

    ordered = sorted(
        offsets.values(),
        key=lambda item: (-item["score"], item["path"] or "", item["char_start"]),
    )

    temporary = "%s.tmp.%d" % (path, os.getpid())
    kept = 0
    top_records = []
    with open(path, "r", encoding="utf-8") as source, \
            open(temporary, "w", encoding="utf-8") as target:
        for position, item in enumerate(ordered):
            source.seek(item["offset"])
            line = source.readline().strip()
            if not line:
                continue
            target.write(line + "\n")
            kept += 1
            if position < top_n:
                try:
                    top_records.append(json.loads(line))
                except ValueError:
                    pass
        target.flush()
        os.fsync(target.fileno())
    os.replace(temporary, path)

    documents = len({item["path"] for item in ordered})
    return {"records": kept, "documents": documents, "top": top_records}


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def load_inventory(path):
    inventory = runner.load_json(path, None)
    if not isinstance(inventory, list):
        raise SystemExit("cannot read inventory: %s" % path)
    return inventory


def run(args):
    started_at = utcnow()
    wall_start = time.time()

    inventory = load_inventory(args.inventory)
    if args.limit:
        inventory = inventory[: args.limit]

    os.makedirs(INDEX_DIR, exist_ok=True)

    state = runner.load_json(STATE_PATH, None)
    if not isinstance(state, dict) or state.get("schema_version") != STATE_SCHEMA:
        state = {"schema_version": STATE_SCHEMA, "documents": {}, "runs": []}
    state.setdefault("documents", {})
    state.setdefault("runs", [])
    state["triage_version"] = triage.TRIAGE_VERSION
    state["chunker_version"] = chunker.CHUNKER_VERSION
    state["extractor_version"] = extractor.EXTRACTOR_VERSION
    state["chunk_chars"] = args.chunk_chars

    if args.rebuild and os.path.isfile(CHUNK_INDEX_PATH):
        os.replace(CHUNK_INDEX_PATH, CHUNK_INDEX_PATH + ".superseded")

    index_handle = open(CHUNK_INDEX_PATH, "a", encoding="utf-8")

    stats = {
        "inventory_records": len(inventory),
        "processed_this_run": 0,
        "skipped_unchanged": 0,
        "extracted_ok": 0,
        "failed": 0,
        "total_chars": 0,
        "total_chunks": 0,
        "candidate_chunks": 0,
    }
    priority_counts = {name: 0 for name in triage.PRIORITY_ORDER}
    topic_counts = {name: 0 for name in triage.TOPICS}
    signal_counts = {}
    failures = []
    documents = {}
    sha_mismatches = []

    try:
        for position, record in enumerate(inventory, start=1):
            relative = record.get("path")
            absolute = os.path.join(DOCUMENTS_DIR, relative)
            expected_sha = record.get("sha256")

            entry = state["documents"].get(relative) or {}
            unchanged = (
                entry.get("sha256") == expected_sha
                and entry.get("extractor_version") == extractor.EXTRACTOR_VERSION
                and entry.get("chunker_version") == chunker.CHUNKER_VERSION
                and entry.get("triage_version") == triage.TRIAGE_VERSION
                and entry.get("chunk_chars") == args.chunk_chars
            )
            if unchanged and not args.force:
                stats["skipped_unchanged"] += 1
                documents[relative] = entry
                if entry.get("status") == "ok":
                    stats["extracted_ok"] += 1
                    stats["total_chars"] += entry.get("char_count", 0)
                    stats["total_chunks"] += entry.get("chunk_count", 0)
                    stats["candidate_chunks"] += entry.get("candidate_count", 0)
                    for name, value in (entry.get("priority_counts") or {}).items():
                        priority_counts[name] = priority_counts.get(name, 0) + value
                    for name, value in (entry.get("topic_counts") or {}).items():
                        topic_counts[name] = topic_counts.get(name, 0) + value
                    for name, value in (entry.get("signal_counts") or {}).items():
                        signal_counts[name] = signal_counts.get(name, 0) + value
                else:
                    stats["failed"] += 1
                    failures.append({
                        "path": relative,
                        "sha256": entry.get("sha256"),
                        "bytes": entry.get("bytes"),
                        "container": entry.get("container"),
                        "status": entry.get("status"),
                        "reason": entry.get("reason"),
                    })
                continue

            if not os.path.isfile(absolute):
                stats["failed"] += 1
                failures.append({"path": relative, "status": "missing",
                                 "reason": "file not present on disk"})
                state["documents"][relative] = {
                    "sha256": expected_sha, "status": "missing",
                    "reason": "file not present on disk", "triaged_at": utcnow(),
                    "extractor_version": extractor.EXTRACTOR_VERSION,
                    "chunker_version": chunker.CHUNKER_VERSION,
                    "triage_version": triage.TRIAGE_VERSION,
                    "chunk_chars": args.chunk_chars,
                }
                documents[relative] = state["documents"][relative]
                continue

            stats["processed_this_run"] += 1

            actual_sha = runner.sha256_file(absolute)
            if expected_sha and actual_sha != expected_sha:
                sha_mismatches.append({"path": relative, "inventory": expected_sha,
                                       "actual": actual_sha})

            try:
                extracted = extractor.extract(absolute)
            except Exception as exc:  # noqa: BLE001 - every failure is recorded
                status = ("unsupported" if isinstance(exc, extractor.UnsupportedFormat)
                          else "extract_failed")
                stats["failed"] += 1
                failures.append({
                    "path": relative,
                    "sha256": actual_sha,
                    "bytes": record.get("bytes"),
                    "status": status,
                    "container": extractor.sniff(absolute),
                    "reason": "%s: %s" % (type(exc).__name__, exc),
                })
                state["documents"][relative] = {
                    "sha256": actual_sha, "status": status,
                    "reason": str(exc), "triaged_at": utcnow(),
                    "extractor_version": extractor.EXTRACTOR_VERSION,
                    "chunker_version": chunker.CHUNKER_VERSION,
                    "triage_version": triage.TRIAGE_VERSION,
                    "chunk_chars": args.chunk_chars,
                    "bytes": record.get("bytes"),
                    "container": extractor.sniff(absolute),
                }
                documents[relative] = state["documents"][relative]
                continue

            text = extracted["text"]
            chunks = chunker.chunk_text(text, chunk_chars=args.chunk_chars)
            records, truncated = triage.analyze_document(text, chunks)

            doc_priority = {name: 0 for name in triage.PRIORITY_ORDER}
            doc_topics = {name: 0 for name in triage.TOPICS}
            doc_signals = {}
            max_score = 0
            for candidate in records:
                candidate["path"] = relative
                candidate["sha256"] = actual_sha
                candidate["collection"] = os.path.dirname(relative)
                index_handle.write(json.dumps(candidate, ensure_ascii=False) + "\n")
                doc_priority[candidate["priority"]] += 1
                priority_counts[candidate["priority"]] += 1
                for name in candidate["topics"]:
                    doc_topics[name] += 1
                    topic_counts[name] += 1
                for signal in candidate["signals"]:
                    name = signal["signal"]
                    doc_signals[name] = doc_signals.get(name, 0) + signal["hits"]
                    signal_counts[name] = signal_counts.get(name, 0) + signal["hits"]
                max_score = max(max_score, candidate["score"])

            index_handle.flush()

            stats["extracted_ok"] += 1
            stats["total_chars"] += len(text)
            stats["total_chunks"] += len(chunks)
            stats["candidate_chunks"] += len(records)

            entry = {
                "sha256": actual_sha,
                "status": "ok",
                "bytes": record.get("bytes"),
                "container": extracted["container"],
                "extractor": extracted["extractor"],
                "extractor_version": extracted["extractor_version"],
                "chunker_version": chunker.CHUNKER_VERSION,
                "triage_version": triage.TRIAGE_VERSION,
                "chunk_chars": args.chunk_chars,
                "char_count": len(text),
                "chunk_count": len(chunks),
                "candidate_count": len(records),
                "high_count": doc_priority[triage.PRIORITY_HIGH],
                "medium_count": doc_priority[triage.PRIORITY_MEDIUM],
                "low_count": doc_priority[triage.PRIORITY_LOW],
                "max_score": max_score,
                "priority_counts": doc_priority,
                "topic_counts": doc_topics,
                "signal_counts": doc_signals,
                "match_limit_hit": truncated,
                "triaged_at": utcnow(),
            }
            state["documents"][relative] = entry
            documents[relative] = entry

            if position % STATE_FLUSH_EVERY == 0:
                index_handle.flush()
                os.fsync(index_handle.fileno())
                runner.atomic_write_json(STATE_PATH, state)
                print("  ... %d/%d documents (%.0fs)" % (position, len(inventory),
                                                         time.time() - wall_start),
                      flush=True)
    finally:
        index_handle.flush()
        os.fsync(index_handle.fileno())
        index_handle.close()

    # ---- compaction, ranking, atomic outputs ----------------------------
    ok_documents = {
        path for path, entry in state["documents"].items()
        if entry.get("status") == "ok"
    }
    compacted = compact_index(CHUNK_INDEX_PATH, ok_documents, args.top)

    mean_chunk_chars = (
        stats["total_chars"] / stats["total_chunks"] if stats["total_chunks"] else 0
    )

    high = priority_counts[triage.PRIORITY_HIGH]
    medium = priority_counts[triage.PRIORITY_MEDIUM]
    low = priority_counts[triage.PRIORITY_LOW]

    summary = {
        "schema_version": INDEX_SCHEMA,
        "generated_at": utcnow(),
        "run": {
            "started_at": started_at,
            "wall_seconds": round(time.time() - wall_start, 1),
            "inventory": os.path.relpath(args.inventory, ARCHIVE_ROOT),
            "chunk_chars": args.chunk_chars,
            "extractor_version": extractor.EXTRACTOR_VERSION,
            "chunker_version": chunker.CHUNKER_VERSION,
            "triage_version": triage.TRIAGE_VERSION,
            "model_calls": 0,
        },
        "documents": {
            "inventory_records": stats["inventory_records"],
            "processed_this_run": stats["processed_this_run"],
            "skipped_unchanged": stats["skipped_unchanged"],
            "extracted_ok": stats["extracted_ok"],
            "failed": stats["failed"],
            "sha256_mismatches": len(sha_mismatches),
            "total_characters": stats["total_chars"],
            "total_chunks": stats["total_chunks"],
            "mean_chunk_chars": round(mean_chunk_chars, 1),
        },
        "candidates": {
            "total": stats["candidate_chunks"],
            "high": high,
            "medium": medium,
            "low": low,
            "candidate_share_of_chunks": (
                round(stats["candidate_chunks"] / stats["total_chunks"], 4)
                if stats["total_chunks"] else 0
            ),
            "by_topic": dict(sorted(topic_counts.items(), key=lambda kv: -kv[1])),
            "by_signal": dict(sorted(signal_counts.items(), key=lambda kv: -kv[1])),
        },
        "index": {
            "records_kept": compacted["records"],
            "documents_indexed": compacted["documents"],
            "chunk_index_bytes": (os.path.getsize(CHUNK_INDEX_PATH)
                                  if os.path.isfile(CHUNK_INDEX_PATH) else 0),
        },
        "model_estimate": {
            "calibration": MODEL_CALIBRATION,
            "note": ("Estimates use the throughput measured on this host in "
                     "Milestone 0. No model was called to produce them."),
            "high_only": estimate_block(high, mean_chunk_chars),
            "high_and_medium": estimate_block(high + medium, mean_chunk_chars),
            "all_candidates": estimate_block(stats["candidate_chunks"], mean_chunk_chars),
        },
        "failures": failures,
    }

    runner.atomic_write_json(SUMMARY_PATH, summary)
    runner.atomic_write_json(FAILURES_PATH, {
        "schema_version": INDEX_SCHEMA,
        "generated_at": utcnow(),
        "failure_count": len(failures),
        "failures": failures,
    })
    runner.atomic_write_json(DOCUMENT_INDEX_PATH, {
        "schema_version": INDEX_SCHEMA,
        "generated_at": utcnow(),
        "document_count": len(documents),
        "documents": documents,
    })
    runner.atomic_write_json(TOP_PATH, {
        "schema_version": INDEX_SCHEMA,
        "generated_at": utcnow(),
        "requested": args.top,
        "returned": len(compacted["top"]),
        "candidates": compacted["top"],
    })

    state["runs"].append({
        "at": utcnow(),
        "inventory_records": stats["inventory_records"],
        "processed": stats["processed_this_run"],
        "skipped": stats["skipped_unchanged"],
        "ok": stats["extracted_ok"],
        "failed": stats["failed"],
        "candidates": stats["candidate_chunks"],
        "high": high,
        "wall_seconds": round(time.time() - wall_start, 1),
    })
    state["updated_at"] = utcnow()
    runner.atomic_write_json(STATE_PATH, state)

    _write_readme(summary)

    return summary


def _write_readme(summary):
    text = """GD Bible Research - candidate index (Milestone 1)
Generated: {generated}

This directory was produced by CPU-only extraction and triage.
No AI model was called, and no original document was modified.

Files
-----
chunk_index.jsonl   One JSON object per candidate passage, ranked by score
                    (highest first). Each record carries:
                      path, sha256, collection
                      chunk_id, char_start, char_end
                      score, priority, topics, tiers, signals
                      matches[] -> snippet, snippet_char_start/end,
                                   match_char_start/end, matched_text
top_candidates.json The highest-scoring {top} passages.
document_index.json Every document in the inventory (status ok or failed)
                    with its extractor, character/chunk counts and how many
                    candidate passages it contributed.
extraction_failures.json  The subset of documents that could not be extracted,
                    each with its container type and failure reason.
triage_state.json   Resumable state: sha256 + versions per document.
triage_summary.json Aggregate counts and model-time estimates.

Searching
---------
    grep -i 'translat' chunk_index.jsonl | head
    python3 -c "import json;[print(json.loads(l)['path']) for l in open('chunk_index.jsonl')]"

Reading a passage
-----------------
char_start/char_end are offsets into the extracted text of the source
document; match_char_start/match_char_end locate the exact matched words.
Re-extract with gd_research_extract + gd_research_chunk to recover the
full chunk text, or open the original document.

Regenerating incrementally
--------------------------
    python3 gd_research_corpus.py
Documents whose SHA-256 and extractor/chunker/triage versions are
unchanged are skipped, so new downloads are picked up without redoing
existing work.

Counts
------
inventory records : {inventory}
extracted ok      : {ok}
failed            : {failed}
chunks            : {chunks}
candidate passages: {candidates}  (high {high}, medium {medium}, low {low})
""".format(
        generated=summary["generated_at"],
        top=TOP_N_DISPLAY,
        inventory=summary["documents"]["inventory_records"],
        ok=summary["documents"]["extracted_ok"],
        failed=summary["documents"]["failed"],
        chunks=summary["documents"]["total_chunks"],
        candidates=summary["candidates"]["total"],
        high=summary["candidates"]["high"],
        medium=summary["candidates"]["medium"],
        low=summary["candidates"]["low"],
    )
    temporary = "%s.tmp.%d" % (README_PATH, os.getpid())
    with open(temporary, "w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, README_PATH)


TOP_N_DISPLAY = 2000


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Milestone 1: corpus-wide CPU extraction and triage (no model calls)."
    )
    parser.add_argument("--inventory", default=INVENTORY_PATH)
    parser.add_argument(
        "--index-dir", default=INDEX_DIR,
        help="directory for all candidate-index/state outputs "
             "(default: historical research/index)",
    )
    parser.add_argument("--chunk-chars", type=int, default=chunker.DEFAULT_CHUNK_CHARS)
    parser.add_argument("--top", type=int, default=TOP_N_DISPLAY)
    parser.add_argument("--limit", type=int, default=0,
                        help="process only the first N inventory records (testing)")
    parser.add_argument("--force", action="store_true",
                        help="reprocess documents even when unchanged")
    parser.add_argument("--rebuild", action="store_true",
                        help="discard the existing candidate index and rebuild it")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    configure_index_dir(args.index_dir)

    summary = run(args)
    if not args.quiet:
        print(json.dumps({
            "generated_at": summary["generated_at"],
            "wall_seconds": summary["run"]["wall_seconds"],
            "documents": summary["documents"],
            "candidates": summary["candidates"]["total"],
            "priority": {k: summary["candidates"][k] for k in ("high", "medium", "low")},
            "index": summary["index"],
            "model_estimate": {
                k: summary["model_estimate"][k]
                for k in ("high_only", "high_and_medium", "all_candidates")
            },
            "failure_count": len(summary["failures"]),
        }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
