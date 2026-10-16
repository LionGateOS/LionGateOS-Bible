#!/usr/bin/env python3
"""
gd_anchor_verifier.py
=====================

P1 -- Anchor Validity Gate for the Church Archive Search Engine.

Purpose
-------
Provide a *normalization-aware* deterministic classifier that decides whether a
stored research finding's evidence anchor (``char_start``/``char_end`` +
``quote``) still resolves against the *current* canonical ``document_text``.

Why this module exists
----------------------
``gd_string_assertion.verify_evidence_span()`` performs literal substring
equality only.  Running it verbatim over the live research sidecar flags
1,353 findings across 200 documents.  The correct figure -- established by the
read-only P1 audit -- is 714 findings across 56 documents.  The 639-finding /
144-document difference is entirely the 5,931 ``whitespace_normalized`` plus 35
``punct_normalized`` rows, which only validate when compared using the same
normalization the extraction pipeline used when it assigned
``source_match_type``.

This module therefore:

  * preserves ``gd_string_assertion.py`` untouched (read-only import only),
  * reproduces those exact semantics for ``source_match_type == "exact"``,
  * adds the missing normalization layer for the two normalized match types,
  * bounds every comparison on ``len(document_text.content)`` and NEVER on the
    stale ``documents.char_count`` column (stale for 547 documents; a
    ``char_end > char_count`` check detects 0 of the 714 real failures).

Read-only guarantees
---------------------
* ``archive_search.db``            opened ``mode=ro``
* ``archive_research_sidecar.db``  opened ``immutable=1``
* baseline sidecar                 opened ``immutable=1``

No journal, WAL, or shared-memory artifact can be produced by these open modes.

Usage
-----
    python3 gd_anchor_verifier.py                 # summary + audited-total gate
    python3 gd_anchor_verifier.py --manifest out.json
    python3 gd_anchor_verifier.py --json          # machine-readable summary

Exit status
-----------
0  counts reproduced and match the audited expectation
1  counts reproduced but differ from the audited expectation (milestone FAIL)
2  unrecoverable error
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

# --------------------------------------------------------------------------
# Identity
# --------------------------------------------------------------------------

VERIFIER_NAME = "gd_anchor_verifier"
VERIFIER_VERSION = "1.0.0"
SCHEMA_VERSION = 1

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MAIN_DB = os.path.join(BASE_DIR, "archive_search.db")
SIDECAR_DB = os.path.join(BASE_DIR, "archive_research_sidecar.db")
BASELINE_DB = os.environ.get(
    "GD_BASELINE_DB",
    "/mnt/SanDisk-Backup/MASTER_BACKUPS/"
    "archive_research_sidecar_20261011_002538.db"
)

# --- Audited expectations (P1 read-only audit, 2026-10-11) -----------------
# These are *expectations for a pass/fail gate*, never inputs to the
# computation.  The classifier derives its own verdicts independently; the
# numbers below are only compared afterwards.
EXPECTED = {
    "total": 19340,
    "valid": 18626,
    "out_of_bounds": 112,
    "mismatch": 602,
    "invalid_total": 714,
    "affected_documents": 56,
    "verdict_stream_sha256": (
        "7a335e805cb8bb4a24c70c35f8e419259a583680f5181eb0cdc5f6df50d76256"
    ),
    "baseline_count": 30730,
    "removed_total": 11390,
}

#: Match types understood by the classifier.
EXACT = "exact"
WHITESPACE_NORMALIZED = "whitespace_normalized"
PUNCT_NORMALIZED = "punct_normalized"
KNOWN_MATCH_TYPES = (EXACT, WHITESPACE_NORMALIZED, PUNCT_NORMALIZED)

#: Verdict vocabulary -- exactly one of these is produced per finding.
VALID = "valid"
OUT_OF_BOUNDS = "out_of_bounds"
MISMATCH = "mismatch"
UNRESOLVED_DOCUMENT = "unresolved_document"
INVALID_VERDICTS = (OUT_OF_BOUNDS, MISMATCH)

# --- M12 extractor provenance (recorded, not re-derived) ------------------
M12_REFERENCE = {
    "commit": "016115ebb0107db6e421d604d8f95fc3fec29c28",
    "commit_subject": (
        "M12: Patch RTF extraction skip logic to suppress metadata leaks"
    ),
    "commit_authored": "2026-10-11T16:26:21-04:00",
    "file": "gd_research_extract.py",
    "extractor_version_before": "1.0.0",
    "extractor_version_after": "1.1.0",
    "re_extracted_documents": 547,
    "rtf_container_documents_total": 795,
}

# --------------------------------------------------------------------------
# Normalization layer  (the piece gd_string_assertion.py does not provide)
# --------------------------------------------------------------------------


def normalize_whitespace(text: str) -> str:
    """Collapse all whitespace runs to a single space (matches the pipeline)."""
    return " ".join(text.split())


def normalize_punctuation(text: str) -> str:
    """Reduce to alphanumerics and whitespace, then trim (pipeline semantics)."""
    return "".join(ch for ch in text if ch.isalnum() or ch.isspace()).strip()


def normalize(text: str, source_match_type: str) -> str:
    """Apply the normalization implied by ``source_match_type``."""
    if source_match_type == WHITESPACE_NORMALIZED:
        return normalize_whitespace(text)
    if source_match_type == PUNCT_NORMALIZED:
        return normalize_punctuation(text)
    return text


# --------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------


def classify(
    canonical_text,
    quote,
    char_start,
    char_end,
    source_match_type,
) -> str:
    """Return exactly one verdict for a single finding.

    Verdicts: ``valid`` | ``out_of_bounds`` | ``mismatch`` |
    ``unresolved_document``.

    Bounds are taken from ``len(canonical_text)``.  ``documents.char_count``
    is deliberately never consulted.
    """
    if canonical_text is None:
        return UNRESOLVED_DOCUMENT

    if quote is None:
        quote = ""

    if char_start is None or char_end is None:
        return OUT_OF_BOUNDS
    if not isinstance(char_start, int) or not isinstance(char_end, int):
        return OUT_OF_BOUNDS

    # Bounds authority: the length of the canonical text actually stored.
    if char_start < 0 or char_end > len(canonical_text) or char_start >= char_end:
        return OUT_OF_BOUNDS

    actual = canonical_text[char_start:char_end]

    if source_match_type == WHITESPACE_NORMALIZED:
        matches = _normalize_whitespace(actual) == _normalize_whitespace(quote)
    elif source_match_type == PUNCT_NORMALIZED:
        matches = _normalize_punctuation(actual) == _normalize_punctuation(quote)
    else:
        # "exact" and any unknown match type fall back to literal equality,
        # preserving gd_string_assertion.py semantics.
        matches = actual == quote

    return VALID if matches else MISMATCH


# Local aliases so the hot loop avoids module-attribute lookups.
_normalize_whitespace = normalize_whitespace
_normalize_punctuation = normalize_punctuation


def verify(
    canonical_text,
    quote,
    char_start,
    char_end,
    source_match_type,
):
    """Compatibility wrapper that raises the original guardrail exceptions.

    Raises:
        OffsetMismatchError:         literal/normalized text does not match.
        HallucinatedQuoteError:      offsets fall outside the canonical text.
    """
    verdict = classify(
        canonical_text, quote, char_start, char_end, source_match_type
    )
    if verdict == VALID:
        return True
    if verdict == OUT_OF_BOUNDS:
        raise HallucinatedQuoteError(
            "Offsets [{0}:{1}] are out of bounds for text length {2}.".format(
                char_start, char_end,
                len(canonical_text) if canonical_text is not None else None,
            )
        )
    raise OffsetMismatchError(
        "Assertion Failed.\n"
        "Expected AI Quote: '{0}'\n"
        "Actual Text at Offsets: '{1}'".format(
            quote,
            "" if canonical_text is None
            else canonical_text[char_start:char_end],
        )
    )


# --- Read-only import of the existing guardrail (never modified) ----------
try:
    from gd_string_assertion import (  # noqa: F401
        OffsetMismatchError,
        HallucinatedQuoteError,
        verify_evidence_span,
    )
except ImportError:  # pragma: no cover - defensive
    sys.path.insert(0, BASE_DIR)
    from gd_string_assertion import (  # noqa: F401
        OffsetMismatchError,
        HallucinatedQuoteError,
        verify_evidence_span,
    )


# --------------------------------------------------------------------------
# Utilities
# --------------------------------------------------------------------------


def sha256_file(path: str, chunk_size: int = 1 << 20) -> str:
    """Streaming SHA-256 of a file."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(chunk_size), b""):
            digest.update(block)
    return digest.hexdigest()


def file_facts(path: str, with_hash: bool = True) -> dict:
    """Path/size/mtime (+ optional hash) for a database artifact."""
    facts = {"path": path, "exists": os.path.exists(path)}
    if not facts["exists"]:
        return facts
    stat = os.stat(path)
    facts["size_bytes"] = stat.st_size
    facts["mtime"] = datetime.fromtimestamp(
        stat.st_mtime, tz=timezone.utc
    ).isoformat()
    if with_hash:
        facts["sha256"] = sha256_file(path)
    return facts


def _connect(path: str, immutable: bool):
    """Open a database read-only.  Never read-write, never locking-creating."""
    if immutable:
        return sqlite3.connect(f"file:{path}?immutable=1", uri=True)
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


# --------------------------------------------------------------------------
# Audit
# --------------------------------------------------------------------------

_FINDING_SQL = """
    SELECT finding_uid, doc_path, source_sha256, quote,
           char_start, char_end, source_match_type
    FROM research_findings
    ORDER BY finding_uid
"""

_TEXT_SQL = """
    SELECT t.content
    FROM documents d JOIN document_text t ON d.id = t.id
    WHERE d.doc_path = ?
"""


def audit_sidecar(sidecar_path: str, immutable: bool = True) -> dict:
    """Classify every finding in a research sidecar.

    Returns a dict with per-finding verdicts (in ``finding_uid`` order), counts,
    affected documents and the deterministic verdict-stream fingerprint.
    """
    main = _connect(MAIN_DB, immutable=False)
    side = _connect(sidecar_path, immutable=immutable)

    text_cache: dict = {}

    def canonical(doc_path: str):
        if doc_path not in text_cache:
            row = main.execute(_TEXT_SQL, (doc_path,)).fetchone()
            text_cache[doc_path] = row[0] if row else None
        return text_cache[doc_path]

    findings = []
    counts = {VALID: 0, OUT_OF_BOUNDS: 0, MISMATCH: 0, UNRESOLVED_DOCUMENT: 0}
    strict_counts = {VALID: 0, OUT_OF_BOUNDS: 0, MISMATCH: 0, "other": 0}
    affected = set()
    quarantined = []
    stream = hashlib.sha256()

    for (
        finding_uid,
        doc_path,
        source_sha256,
        quote,
        char_start,
        char_end,
        match_type,
    ) in side.execute(_FINDING_SQL):
        text = canonical(doc_path)

        verdict = classify(text, quote, char_start, char_end, match_type)
        counts[verdict] += 1
        if verdict in INVALID_VERDICTS:
            affected.add(doc_path)

        # Independent cross-check with the *existing* strict guardrail, so the
        # known mis-calibration (1,353/200) stays visible rather than implied.
        strict_verdict = _strict_verdict(text, quote, char_start, char_end)
        strict_counts[strict_verdict] += 1

        # Canonical deterministic fingerprint serialization:
        #   "<finding_uid>|<normalized_verdict>\n"  in finding_uid order.
        stream.update(f"{finding_uid}|{verdict}\n".encode("utf-8"))

        findings.append(
            {
                "finding_uid": finding_uid,
                "doc_path": doc_path,
                "source_sha256": source_sha256,
                "char_start": char_start,
                "char_end": char_end,
                "source_match_type": match_type,
                "canonical_text_len": None if text is None else len(text),
                "verdict": verdict,
            }
        )

        if verdict in INVALID_VERDICTS:
            actual = (
                ""
                if text is None or char_start is None or char_end is None
                or char_start < 0 or char_end > len(text) or char_start >= char_end
                else text[char_start:char_end]
            )
            quarantined.append(
                {
                    "finding_uid": finding_uid,
                    "doc_path": doc_path,
                    "source_sha256": source_sha256,
                    "verdict": verdict,
                    "source_match_type": match_type,
                    "char_start": char_start,
                    "char_end": char_end,
                    "canonical_text_len": None if text is None else len(text),
                    "expected_quote": quote,
                    "actual_at_offsets": actual,
                }
            )

    rowid_min, rowid_max = side.execute(
        "SELECT MIN(rowid), MAX(rowid) FROM research_findings"
    ).fetchone()

    side.close()
    main.close()

    return {
        "findings": findings,
        "counts": counts,
        "strict_counts": strict_counts,
        "affected_documents": sorted(affected),
        "quarantine": quarantined,
        "verdict_stream_sha256": stream.hexdigest(),
        "row_count": len(findings),
        "rowid_min": rowid_min,
        "rowid_max": rowid_max,
    }


def _strict_verdict(text, quote, char_start, char_end) -> str:
    """Verdict under literal ``gd_string_assertion.verify_evidence_span``."""
    if text is None:
        return "other"
    try:
        verify_evidence_span(text, quote, char_start, char_end)
        return VALID
    except HallucinatedQuoteError:
        return OUT_OF_BOUNDS
    except OffsetMismatchError:
        return MISMATCH
    except Exception:
        return "other"


# --------------------------------------------------------------------------
# Manifest
# --------------------------------------------------------------------------


def build_manifest() -> dict:
    """Run the audit and assemble the deterministic manifest document."""
    live = audit_sidecar(SIDECAR_DB, immutable=True)
    baseline = _baseline_identity()

    counts = live["counts"]
    invalid_total = counts[OUT_OF_BOUNDS] + counts[MISMATCH]

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "verifier": {
            "name": VERIFIER_NAME,
            "version": VERIFIER_VERSION,
            "path": os.path.join(BASE_DIR, "gd_anchor_verifier.py"),
        },
        "normalization_semantics": {
            "authority_for_bounds": (
                "len(document_text.content) -- documents.char_count is "
                "STALE for 547 documents and must never bound an anchor"
            ),
            "exact": "byte-for-byte equality of canonical_text[start:end] and quote",
            "whitespace_normalized": (
                "' '.join(actual.split()) == ' '.join(quote.split())"
            ),
            "punct_normalized": (
                "alphanumeric+whitespace reduction, trimmed, compared equal"
            ),
            "unknown_match_type": "falls back to exact literal equality",
            "inherits": "gd_string_assertion.verify_evidence_span (exact path)",
        },
        "sources": {
            "archive_search_db": file_facts(MAIN_DB),
            "archive_research_sidecar_db": file_facts(SIDECAR_DB),
            "open_modes": {
                "archive_search_db": "mode=ro",
                "archive_research_sidecar_db": "immutable=1",
                "baseline_sidecar": "immutable=1",
            },
        },
        "row_count": live["row_count"],
        "rowid_range": [live["rowid_min"], live["rowid_max"]],
        "counts": {
            "total": live["row_count"],
            "valid": counts[VALID],
            "out_of_bounds": counts[OUT_OF_BOUNDS],
            "mismatch": counts[MISMATCH],
            "invalid_total": invalid_total,
            "unresolved_document": counts[UNRESOLVED_DOCUMENT],
        },
        "affected_document_count": len(live["affected_documents"]),
        "affected_documents": live["affected_documents"],
        "verdict_stream_sha256": live["verdict_stream_sha256"],
        "verdict_stream_serialization": (
            'sha256 over "f{finding_uid}|{verdict}\\n" for every finding in '
            "ORDER BY finding_uid (normalized verdict only)"
        ),
        "strict_semantics_cross_check": {
            "note": (
                "gd_string_assertion.verify_evidence_span applied verbatim; "
                "over-quarantines because it has no normalization layer"
            ),
            "valid": live["strict_counts"][VALID],
            "out_of_bounds": live["strict_counts"][OUT_OF_BOUNDS],
            "mismatch": live["strict_counts"][MISMATCH],
            "invalid_total": (
                live["strict_counts"][OUT_OF_BOUNDS]
                + live["strict_counts"][MISMATCH]
            ),
        },
        "baseline": baseline,
        "removed_count": baseline["research_findings_count"] - live["row_count"],
        "m12_extractor_change": M12_REFERENCE,
        "findings": live["findings"],
        "quarantine": live["quarantine"],
    }

    manifest["manifest_content_sha256"] = _manifest_content_hash(manifest)
    return manifest


def _baseline_identity() -> dict:
    facts = file_facts(BASELINE_DB)
    facts["open_mode"] = "immutable=1"
    if facts.get("exists"):
        con = _connect(BASELINE_DB, immutable=True)
        facts["research_findings_count"] = con.execute(
            "SELECT COUNT(*) FROM research_findings"
        ).fetchone()[0]
        rowid_min, rowid_max = con.execute(
            "SELECT MIN(rowid), MAX(rowid) FROM research_findings"
        ).fetchone()
        facts["rowid_range"] = [rowid_min, rowid_max]
        con.close()
    else:
        facts["research_findings_count"] = None
    return facts


_CONTENT_HASH_EXCLUDED = ("generated_at", "manifest_content_sha256")


def _manifest_content_hash(manifest: dict) -> str:
    """Deterministic hash of the manifest minus its non-deterministic fields."""
    payload = {
        key: value
        for key, value in manifest.items()
        if key not in _CONTENT_HASH_EXCLUDED
    }
    blob = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------


def evaluate(manifest: dict) -> list:
    """Compare computed counts against the audited expectation."""
    counts = manifest["counts"]
    checks = [
        ("total findings", counts["total"], EXPECTED["total"]),
        ("valid", counts["valid"], EXPECTED["valid"]),
        ("out_of_bounds", counts["out_of_bounds"], EXPECTED["out_of_bounds"]),
        ("mismatch", counts["mismatch"], EXPECTED["mismatch"]),
        ("invalid_total", counts["invalid_total"], EXPECTED["invalid_total"]),
        (
            "affected_documents",
            manifest["affected_document_count"],
            EXPECTED["affected_documents"],
        ),
        (
            "verdict_stream_sha256",
            manifest["verdict_stream_sha256"],
            EXPECTED["verdict_stream_sha256"],
        ),
        (
            "baseline_count",
            manifest["baseline"].get("research_findings_count"),
            EXPECTED["baseline_count"],
        ),
        ("removed_count", manifest["removed_count"], EXPECTED["removed_total"]),
    ]
    return checks


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--manifest", metavar="PATH",
                        help="write the full manifest JSON to PATH")
    parser.add_argument("--json", action="store_true",
                        help="print a machine-readable summary to stdout")
    args = parser.parse_args(argv)

    manifest = build_manifest()
    counts = manifest["counts"]

    summary = {
        "verifier": f"{VERIFIER_NAME}/{VERIFIER_VERSION}",
        "total": counts["total"],
        "valid": counts["valid"],
        "out_of_bounds": counts["out_of_bounds"],
        "mismatch": counts["mismatch"],
        "invalid_total": counts["invalid_total"],
        "affected_documents": manifest["affected_document_count"],
        "verdict_stream_sha256": manifest["verdict_stream_sha256"],
        "manifest_content_sha256": manifest["manifest_content_sha256"],
        "strict_cross_check": manifest["strict_semantics_cross_check"],
        "arithmetic_ok": counts["valid"] + counts["out_of_bounds"]
        + counts["mismatch"] == counts["total"],
    }

    checks = evaluate(manifest)
    summary["gate"] = [
        {"check": name, "computed": got, "expected": want,
         "pass": got == want}
        for name, got, want in checks
    ]
    summary["gate_passed"] = all(item["pass"] for item in summary["gate"])

    if args.manifest:
        with open(args.manifest, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        summary["manifest_written"] = os.path.abspath(args.manifest)

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(f"{VERIFIER_NAME} {VERIFIER_VERSION}")
        print(f"  total           : {summary['total']}")
        print(f"  valid           : {summary['valid']}")
        print(f"  out_of_bounds   : {summary['out_of_bounds']}")
        print(f"  mismatch        : {summary['mismatch']}")
        print(f"  invalid_total   : {summary['invalid_total']}")
        print(f"  affected docs   : {summary['affected_documents']}")
        print(f"  arithmetic      : "
              f"{summary['valid']} + {summary['out_of_bounds']} + "
              f"{summary['mismatch']} = {summary['total']} "
              f"-> {'OK' if summary['arithmetic_ok'] else 'FAIL'}")
        print(f"  verdict stream  : {summary['verdict_stream_sha256']}")
        print(f"  content sha256  : {summary['manifest_content_sha256']}")
        print(f"  strict x-check  : "
              f"valid={summary['strict_cross_check']['valid']} "
              f"oob={summary['strict_cross_check']['out_of_bounds']} "
              f"mismatch={summary['strict_cross_check']['mismatch']} "
              f"invalid={summary['strict_cross_check']['invalid_total']}")
        print()
        for item in summary["gate"]:
            flag = "PASS" if item["pass"] else "FAIL"
            print(f"  [{flag}] {item['check']:<22} computed={item['computed']}")
            if not item["pass"]:
                print(f"          {'':<22} expected={item['expected']}")
        print()
        print("  GATE:", "PASSED" if summary["gate_passed"] else "FAILED")
        if summary.get("manifest_written"):
            print(f"  manifest: {summary['manifest_written']}")

    return 0 if summary["gate_passed"] else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # pragma: no cover - defensive
        print(f"FATAL: {exc}")
        sys.exit(2)
