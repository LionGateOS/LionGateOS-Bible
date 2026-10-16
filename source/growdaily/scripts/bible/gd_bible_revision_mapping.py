"""gd_bible_revision_mapping.py -- GD Bible Revision Mapping V1.

Deterministic, CPU-only, read-only bridge from the completed GD full-HIGH
archive research corpus to *verse-addressable evidence* for a later GD Bible
revision review:

    22,756 verified passages
      -> final-pass selection (escalate if present, else screen)
      -> 58,498 final verified findings
      -> stable ``finding_uid`` per finding
      -> strict per-raw-reference mapping through ``gd_scripture_engine``
      -> canonical verse expansion against ``gd_canonical_coordinates.json``
      -> verse-addressable evidence rows

This milestone makes NO Bible translation decision and edits NO Bible text.
It only builds and validates the deterministic bridge.

Evidentiary boundary (do not merge classes)
------------------------------------------
``scripture_refs`` attached to a research finding are MODEL-ATTRIBUTED strings.
They are a different evidentiary class from deterministic references extracted
from document text. This mapper preserves every raw string verbatim and labels
every derived coordinate with the raw string and the engine verdict that
produced it. Nothing here promotes a model annotation to authoritative fact.

Final-pass selection rule
-------------------------
The combined artifact stores a ``screen`` pass and sometimes an ``escalate``
pass. The final population rule is::

    final_pass = escalate if present, otherwise screen

Only ``final_pass["verified"]`` entries (with ``verified is True``) form the
58,498-finding population. Screen and escalation findings are never both
counted.

Finding identity
----------------
``finding_uid`` is the SHA-256 of a documented canonical JSON serialization
(UTF-8, ``sort_keys=True``, ``separators=(",", ":")``, ``ensure_ascii=False``)
of an identity payload that includes source-document SHA-256, chunk identity,
research generation, the selected final pass name and pass key, the finding
index inside that pass, and immutable finding fields. File location alone is
never the identity.

Strict consumption rule for raw reference strings
-------------------------------------------------
Each element of a finding's ``scripture_refs`` array is processed
INDEPENDENTLY. No book is inherited across array elements: ``"12:24"`` stays
unresolved even when the preceding element was ``"Heb. 8:8, 13"``.

A raw string is FULLY CONSUMED only when every element the engine did not
recognise is one of:

1. whitespace,
2. an explicitly documented harmless citation punctuation character
   (``HARMLESS_RESIDUAL_CHARS``, actually enforced character by character), or
3. a small citation-connector word from ``HARMLESS_RESIDUAL_WORDS``, which
   defaults to the engine's ``_CITATION_CONNECTORS`` only
   (``and/or/verse/verses/ff/cf/see/also``).

The mapping layer is deliberately STRICTER than the parser. The engine's
generic grammatical words, strong citation cues and cue fillers are used by the
PARSER to detect citation structure and are NOT accepted here as evidence that
leftover content is harmless; including them would silently accept prose such as
``"John 3:16 now"``, ``"John 3:16 written"`` or ``"John 3:16 about"``. No
exception is currently required.

If any other word, digit or symbol remains unexplained, the raw string is
classified ``partial_parse`` and contributes NO accepted verse mapping; its
engine rows are preserved for review instead.

Classification (deterministic precedence)
----------------------------------------
1. empty / whitespace only                     -> ``unstructured``
2. no recognised engine rows                  -> ``unstructured``
3. accepted rows AND unclean residual         -> ``partial_parse``
4. accepted rows AND clean residual            -> ``mapped_verse`` /
                                                 ``mapped_range`` /
                                                 ``mapped_mixed`` /
                                                 ``chapter_only`` /
                                                 ``book_only``
5. accepted rows mixing verse-level with chapter/book-level context in ONE raw
   string                                       -> ``mixed_context`` (NON-MAPPED)
6. no accepted rows, any invalid row           -> ``asserted_invalid``
7. no accepted rows, any unresolved row        -> ``unresolved``
8. otherwise                                   -> ``unstructured``

Only ``canonical_status == "asserted_valid"`` rows can produce canonical
mappings. ``asserted_invalid`` coordinates are NEVER mapped; they are recorded
as evidence anomalies, not as automatic archive errors. Chapter-only and
book-only strings are preserved as context and are never promoted to an exact
verse. ``mixed_context`` is a non-mapped defensive state: a raw string mixing
verse-level and chapter/book-level accepted rows cannot be reduced to verse
coordinates, so it emits no verse evidence and one explicit anomaly row, with
all engine rows preserved.

Production input pins (fail closed)
----------------------------------
``validate_production_inputs()`` checks the engine version, the
``gd_scripture_engine.py`` SHA-256, the ``gd_canonical_coordinates.json`` SHA-256
and counts, and the research artifact SHA-256 BEFORE any output file is created,
raising ``ProductionInputError`` on any mismatch. ``write_artifacts(pinned=True)``
is the production default and additionally refuses, before creating any output,
a caller-supplied ``table`` coordinate override and a non-``None`` ``limit``
(a deliberately truncated write). ``pinned=False`` / ``--unpinned-inputs`` exists
only for synthetic test corpora.

Range expansion
---------------
An asserted-valid verse range is preserved *and* expanded to the exact KJV
verse coordinates it contains, using the pinned coordinate table::

    Ephesians 3:14-15 -> Ephesians 3:14, Ephesians 3:15
    Romans 8:18-9:5   -> Romans 8:18..8:39, Romans 9:1..9:5

Expansion never guesses across an invalid coordinate and never clamps: if
either endpoint of a range is missing, outside the pinned table, or ordered
backwards, the row expands to nothing (the still-valid side is never mapped on
its own). Verse mappings are deduplicated within a finding (the same canonical
verse is counted once per finding) while the raw occurrences that produced it
are preserved separately.

Outputs
-------
``--audit-only`` (default) runs the complete corpus in memory/read-only and
prints deterministic summary statistics plus human-review samples. It creates
no artifact. ``--write --out DIR`` writes the versioned JSONL artifacts plus a
manifest (used only with temporary directories in this milestone; the final
production artifact is deliberately not written to the research archive).
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
from collections import Counter

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

import gd_scripture_engine as ENGINE  # noqa: E402

# --------------------------------------------------------------------------
# Versions and pinned inputs
# --------------------------------------------------------------------------

# Mapper behaviour/schema version. Bumped when this module's output changes.
MAPPER_VERSION = "1.0.0"

# Derived-artifact schema version (all three JSONL streams share it).
SCHEMA_VERSION = "gd-bible-revision-reference-map/1"

# finding_uid identity payload version.
IDENTITY_VERSION = "1.0.0"

# Engine version this mapper is validated against.
EXPECTED_ENGINE_VERSION = "1.5.0"

DEFAULT_RESEARCH_ARTIFACT = os.path.join(
    os.environ.get("GD_ARCHIVE_ROOT",
                   "/home/liongateos/PCOG-Research-Archive"),
    "research", "full-high-research-combined-v1",
    "combined_high_research.jsonl"
)

EXPECTED_RESEARCH_SHA256 = (
    "a9cc75dcc664e77811f646053b5c0748ad6a14907c7d84e2c2323abc93bda92a"
)

# Pinned production inputs. The production writer validates every one of these
# and FAILS CLOSED before creating any output file. Only an explicit
# test-only/unpinned call may bypass them.
EXPECTED_ENGINE_FILE_SHA256 = (
    "7e336688d359693b046034a7bf49b827e1edc06da510f3bbb8a9310833b670fa"
)
EXPECTED_COORDINATES_SHA256 = (
    "a0d2c672f6c06f3307c22027216ae53f98bdf910903ef86c049fbbdeb4e9753f"
)

ENGINE_FILE_PATH = os.path.abspath(ENGINE.__file__)

COORDINATES_PATH = ENGINE.COORDINATES_PATH

EXPECTED_CANONICAL_COUNTS = {"book_count": 66, "chapter_count": 1189,
                             "verse_count": 31102}

# Documented expectation for the milestone input; the audit proves it.
EXPECTED_PASSAGES = 22756
EXPECTED_FINAL_FINDINGS = 58498

FINAL_PASS_RULE = "escalate_if_present_else_screen"

# --------------------------------------------------------------------------
# Classification vocabulary
# --------------------------------------------------------------------------

STATUS_MAPPED_VERSE = "mapped_verse"
STATUS_MAPPED_RANGE = "mapped_range"
STATUS_MAPPED_MIXED = "mapped_mixed"
STATUS_CHAPTER_ONLY = "chapter_only"
STATUS_BOOK_ONLY = "book_only"
STATUS_ASSERTED_INVALID = "asserted_invalid"
STATUS_UNRESOLVED = "unresolved"
STATUS_PARTIAL_PARSE = "partial_parse"
STATUS_UNSTRUCTURED = "unstructured"
# NON-MAPPED defensive bucket: accepted rows mixing verse-level and
# chapter/book-level granularity inside ONE raw string. Such a mixture cannot be
# safely reduced to verse coordinates, so it produces NO verse mapping and is
# preserved as an explicit anomaly. Expected to be empty on the current corpus;
# it exists so no mixture falls between the verse and anomaly outputs.
STATUS_MIXED_CONTEXT = "mixed_context"

MAPPED_STATUSES = (STATUS_MAPPED_VERSE, STATUS_MAPPED_RANGE,
                   STATUS_MAPPED_MIXED)

VERSE_MAPPED_STATUSES = (STATUS_MAPPED_VERSE, STATUS_MAPPED_RANGE,
                         STATUS_MAPPED_MIXED)

NON_MAPPED_STATUSES = (STATUS_MIXED_CONTEXT, STATUS_CHAPTER_ONLY,
                       STATUS_BOOK_ONLY, STATUS_ASSERTED_INVALID,
                       STATUS_UNRESOLVED, STATUS_PARTIAL_PARSE,
                       STATUS_UNSTRUCTURED)

ALL_STATUSES = MAPPED_STATUSES + NON_MAPPED_STATUSES

# Harmless residual characters: whitespace and citation punctuation ONLY.
# Anything else that the engine did not consume makes the reference
# partial_parse. This set is deliberately narrow and is ACTUALLY enforced by
# _residual_analysis(); it excludes arithmetic/glyph symbols such as
# "+ * = ~ ^ % $ # @ \u00b0" that are not citation punctuation.
HARMLESS_RESIDUAL_CHARS = frozenset(
    " \t\n\r\f\v"                      # whitespace
    ".,;:!?"                          # citation punctuation
    "()[]{}<>"                        # grouping
    "\"'`\u00b4\u2019\u2018\u201c\u201d"  # quote/apostrophe variants
    "\u2026"                          # ellipsis
    "|/\\&_"                          # citation joins and separators
    "-\u2013\u2014"                   # hyphen / en dash / em dash
)

# Harmless residual words: the engine's citation CONNECTOR vocabulary only
# ("and", "or", "verse", "verses", "ff", "cf", "see", "also"). These are the
# words the engine itself uses to join one reference to the next, so they carry
# no independent prose meaning here.
#
# The mapping layer is deliberately STRICTER than the parser. The engine's
# generic grammatical words (_GENERIC_PRECEDING_WORDS: to/and/of/with/for/as/
# now/then/...), its strong cue words (_STRONG_CITATION_CUES: see/read/notice/
# in/written/found/...) and its filler words (_CUE_FILLERS: the/a/an/...) are
# used by the PARSER to detect citation structure; they are NOT evidence that
# the leftovers of a model-attributed string are harmless. Including them would
# silently accept prose such as "John 3:16 now/written/about". They are excluded
# on purpose; no exception is currently required.
HARMLESS_RESIDUAL_WORDS = frozenset(ENGINE._CITATION_CONNECTORS)


# Tokenizer for unexplained residual content: Unicode words and digit runs.
RESIDUAL_TOKEN_RE = re.compile(r"[^\W\d_]+|\d+", re.UNICODE)

# --------------------------------------------------------------------------
# Hashing / canonical serialization
# --------------------------------------------------------------------------


def sha256_bytes(payload):
    return hashlib.sha256(payload).hexdigest()


def sha256_text(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def sha256_file(path, chunk_size=1 << 20):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(chunk_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def canonical_json(obj):
    """Documented canonical serialization for identity hashing."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def canonical_verse_key(book_id, chapter, verse):
    """Stable coordinate key, display-independent (mirrors engine keys)."""
    return "b{}:c{}:v{}".format(book_id, chapter, verse)


# --------------------------------------------------------------------------
# Coordinate table
# --------------------------------------------------------------------------


def load_coordinate_table(path=None):
    """Return ``{book: (verses_per_chapter, ...)}`` from the pinned artifact."""
    if path is None:
        return ENGINE.CANONICAL_COORDINATES
    artifact = ENGINE._load_coordinates_artifact(path)
    return ENGINE._table_from_artifact(artifact)


def _coordinates_counts_match():
    """True when the loaded table matches the pinned 66/1189/31102 counts."""
    table = ENGINE.CANONICAL_COORDINATES
    if table is None:
        return False
    return {
        "book_count": len(table),
        "chapter_count": sum(len(chapters) for chapters in table.values()),
        "verse_count": sum(sum(chapters) for chapters in table.values()),
    } == EXPECTED_CANONICAL_COUNTS


class ProductionInputError(RuntimeError):
    """Raised when a pinned production input does not match its pinned value."""


def validate_production_inputs(
        research_path=DEFAULT_RESEARCH_ARTIFACT,
        expected_engine_version=EXPECTED_ENGINE_VERSION,
        expected_engine_sha256=EXPECTED_ENGINE_FILE_SHA256,
        expected_coordinates_sha256=EXPECTED_COORDINATES_SHA256,
        expected_research_sha256=EXPECTED_RESEARCH_SHA256):
    """Validate every pinned production input; raise on any mismatch.

    Checked before any output file is created: engine version, engine file
    SHA-256, canonical-coordinate artifact SHA-256, canonical coordinate counts,
    and the research artifact SHA-256. Nothing is repaired or warned past: a
    mismatch raises ``ProductionInputError``.
    """
    problems = []

    if ENGINE.VERSION != expected_engine_version:
        problems.append(
            "engine version {!r} != expected {!r}".format(
                ENGINE.VERSION, expected_engine_version))

    engine_sha256 = sha256_file(ENGINE_FILE_PATH)
    if engine_sha256 != expected_engine_sha256:
        problems.append(
            "engine file sha256 {} != expected {}".format(
                engine_sha256, expected_engine_sha256))

    coordinates_sha256 = sha256_file(COORDINATES_PATH)
    if coordinates_sha256 != expected_coordinates_sha256:
        problems.append(
            "canonical coordinates sha256 {} != expected {}".format(
                coordinates_sha256, expected_coordinates_sha256))

    if not _coordinates_counts_match():
        table = ENGINE.CANONICAL_COORDINATES or {}
        actual = {
            "book_count": len(table),
            "chapter_count": sum(len(c) for c in table.values()),
            "verse_count": sum(sum(c) for c in table.values()),
        }
        problems.append(
            "canonical coordinate counts {} != expected {}".format(
                actual, EXPECTED_CANONICAL_COUNTS))

    research_sha256 = sha256_file(research_path)
    if research_sha256 != expected_research_sha256:
        problems.append(
            "research artifact sha256 {} != expected {}".format(
                research_sha256, expected_research_sha256))

    if problems:
        raise ProductionInputError(
            "production input pin mismatch (refusing to write): "
            + "; ".join(problems))

    return {
        "engine_version": ENGINE.VERSION,
        "engine_file_sha256": engine_sha256,
        "canonical_coordinates_sha256": coordinates_sha256,
        "research_artifact_sha256": research_sha256,
        "canonical_coordinate_counts": dict(EXPECTED_CANONICAL_COUNTS),
    }


# --------------------------------------------------------------------------
# Final-pass selection
# --------------------------------------------------------------------------


def select_final_pass(passage):
    """Return ``(final_pass_name, pass_object)`` per the milestone rule."""
    passes = (passage.get("chunk") or {}).get("passes") or {}
    escalate = passes.get("escalate")
    if escalate is not None:
        return "escalate", escalate
    return "screen", passes.get("screen")


def iter_final_findings(passage):
    """Yield ``(final_pass_name, pass_key, finding_index, finding)`` rows.

    Only the selected final pass is ever read; screen findings of an escalated
    passage are never also counted. Only entries flagged ``verified is True``
    belong to the 58,498 population.
    """
    name, pass_obj = select_final_pass(passage)
    if pass_obj is None:
        return
    key = pass_obj.get("key")
    for index, finding in enumerate(pass_obj.get("verified") or []):
        if not isinstance(finding, dict) or finding.get("verified") is not True:
            continue
        yield {"final_pass": name, "final_pass_key": key,
               "finding_index": index, "finding": finding}


def count_quarantined_in_final_pass(passage):
    """Quarantined findings retained in the selected final pass (context only)."""
    _name, pass_obj = select_final_pass(passage)
    if pass_obj is None:
        return 0
    return len(pass_obj.get("quarantined") or [])


# --------------------------------------------------------------------------
# Finding identity
# --------------------------------------------------------------------------


def build_identity(passage, finding_ref):
    """Build the documented identity payload for one final finding."""
    finding = finding_ref["finding"]
    return {
        "identity_version": IDENTITY_VERSION,
        "source_document_sha256": passage.get("sha256"),
        "source_document": passage.get("source_document"),
        "chunk_id": passage.get("chunk_id"),
        "research_generation": passage.get("research_generation"),
        "final_pass": finding_ref["final_pass"],
        "final_pass_key": finding_ref["final_pass_key"],
        "finding_index": finding_ref["finding_index"],
        "finding_topic": finding.get("topic"),
        "finding_char_start": finding.get("char_start"),
        "finding_char_end": finding.get("char_end"),
        "finding_quote_sha256": sha256_text(finding.get("quote") or ""),
    }


def finding_uid(identity):
    """SHA-256 of the canonical identity serialization."""
    return sha256_bytes(canonical_json(identity).encode("utf-8"))


class FindingUidGuard:
    """Detects duplicate/colliding finding_uid values over a run."""

    def __init__(self):
        self._seen = set()
        self.collisions = 0
        self.duplicate_uids = []

    def add(self, uid):
        if uid in self._seen:
            self.collisions += 1
            if len(self.duplicate_uids) < 20:
                self.duplicate_uids.append(uid)
            return False
        self._seen.add(uid)
        return True

    def __len__(self):
        return len(self._seen)


# --------------------------------------------------------------------------
# Strict per-raw-reference mapping
# --------------------------------------------------------------------------


def _residual_analysis(raw, rows):
    """Return ``(uncovered_text, unexplained_tokens, unexplained_symbols)``.

    The harmless character allowlist is ENFORCED here: every uncovered
    character must be whitespace or a documented harmless citation punctuation
    character, and every uncovered word/digit token must be a documented
    harmless citation connector. Anything else is unexplained and forces
    ``partial_parse``.
    """
    mask = [False] * len(raw)
    for row in rows:
        start = row.get("start_offset") or 0
        end = row.get("end_offset") or 0
        for position in range(max(0, start), min(end, len(mask))):
            mask[position] = True
    uncovered = "".join(ch for i, ch in enumerate(raw) if not mask[i])

    unexplained_tokens = [
        token for token in RESIDUAL_TOKEN_RE.findall(uncovered)
        if not (token.isalpha() and token.lower() in HARMLESS_RESIDUAL_WORDS)
    ]
    unexplained_symbols = sorted({
        char for char in uncovered
        if not char.isspace()
        and not char.isalpha()
        and not char.isdigit()
        and char not in HARMLESS_RESIDUAL_CHARS
    })
    return uncovered, unexplained_tokens, unexplained_symbols


def _compact_row(row):
    return {
        "canonical": row.get("canonical"),
        "reference_key": row.get("reference_key"),
        "granularity": row.get("granularity"),
        "canonical_status": row.get("canonical_status"),
        "canonical_issues": list(row.get("canonical_issues") or []),
        "resolution_status": row.get("resolution_status"),
        "citation_context": row.get("citation_context"),
        "raw_match": row.get("raw_match"),
    }


def classify_raw_reference(raw, table=None):
    """Classify one raw model-attributed reference string, deterministically.

    Returns a copy-safe "core" result dict (no per-finding fields).
    """
    if not isinstance(raw, str):
        return {
            "raw_kind": "non_string",
            "status": STATUS_UNSTRUCTURED,
            "reason": "non_string_reference",
            "unexplained_residual": "",
            "unexplained_tokens": [],
            "unexplained_symbols": [],
            "engine_rows": [],
            "accepted_rows": [],
            "verse_keys": [],
            "origins": [],
            "context": None,
        }

    rows = ENGINE.extract_references(
        raw,
        include_unresolved=True,
        include_bare_books=True,
        canonical=True,
        include_unstructured_chapters=True,
    )

    accepted = [r for r in rows if r.get("canonical_status") == "asserted_valid"]
    invalid = [r for r in rows if r.get("canonical_status") == "asserted_invalid"]
    unresolved = [r for r in rows
                  if r.get("resolution_status") == "unresolved"]

    if not raw.strip():
        status, reason = STATUS_UNSTRUCTURED, "empty_reference"
        uncovered, unexplained, unexplained_symbols = "", [], []
    elif not rows:
        status, reason = STATUS_UNSTRUCTURED, "no_recognized_citation"
        uncovered = raw
        unexplained = RESIDUAL_TOKEN_RE.findall(raw)
        unexplained_symbols = sorted({
            char for char in raw
            if not char.isspace() and not char.isalpha() and not char.isdigit()
            and char not in HARMLESS_RESIDUAL_CHARS
        })
    else:
        uncovered, unexplained, unexplained_symbols = _residual_analysis(raw, rows)
        granularities = {r.get("granularity") for r in accepted}
        if accepted and (unexplained or unexplained_symbols):
            status, reason = STATUS_PARTIAL_PARSE, "unexplained_residual_content"
        elif accepted:
            if granularities == {"verse"}:
                status, reason = STATUS_MAPPED_VERSE, ""
            elif granularities == {"range"}:
                status, reason = STATUS_MAPPED_RANGE, ""
            elif granularities <= {"verse", "range"}:
                status, reason = STATUS_MAPPED_MIXED, ""
            elif granularities == {"chapter"}:
                status, reason = STATUS_CHAPTER_ONLY, ""
            elif granularities == {"book"}:
                status, reason = STATUS_BOOK_ONLY, ""
            else:
                # NON-MAPPED: a verse-level + chapter/book-level mixture in one
                # raw string has no safe verse reduction. Preserve the rows and
                # emit an explicit anomaly instead of a mapping.
                status, reason = (STATUS_MIXED_CONTEXT,
                                  "mixed_context_granularity")
        elif invalid:
            status, reason = STATUS_ASSERTED_INVALID, "asserted_invalid_coordinate"
        elif unresolved:
            status, reason = STATUS_UNRESOLVED, "no_determinable_book"
        else:
            status, reason = STATUS_UNSTRUCTURED, "no_canonical_assertion"

    verse_keys = []
    origins = []
    if status in VERSE_MAPPED_STATUSES:
        for row in accepted:
            expanded = expand_verse_keys(row, table)
            verse_keys.extend(expanded)
            if expanded:
                origins.append(row.get("granularity"))

    context = None
    if status in (STATUS_CHAPTER_ONLY, STATUS_BOOK_ONLY) and accepted:
        context = accepted[0].get("canonical")

    return {
        "raw_kind": "string",
        "status": status,
        "reason": reason,
        "unexplained_residual": uncovered,
        "unexplained_tokens": unexplained,
        "unexplained_symbols": unexplained_symbols,
        "engine_rows": [_compact_row(r) for r in rows],
        "accepted_rows": [_compact_row(r) for r in accepted],
        "verse_keys": sorted(set(verse_keys)),
        "origins": sorted(set(origins)),
        "context": context,
    }


def expand_verse_keys(row, table=None):
    """Expand one asserted-valid engine row to canonical verse keys.

    Fail-safe contract: an endpoint that is missing, out of range or out of
    order makes the WHOLE row expand to ``[]``. Nothing is clamped, nothing is
    guessed, and the still-valid side of a broken range is never mapped on its
    own. For a valid cross-chapter span the intermediate chapters expand
    completely.
    """
    coordinate_table = table if table is not None else ENGINE.CANONICAL_COORDINATES
    if not coordinate_table:
        return []
    if row.get("canonical_status") != "asserted_valid":
        return []
    book = row.get("book")
    book_id = row.get("book_id")
    counts = coordinate_table.get(book)
    if not counts:
        return []

    granularity = row.get("granularity")
    if granularity == "verse":
        chapter, verse = row.get("chapter"), row.get("verse_start")
        if chapter is None or verse is None:
            return []
        if 1 <= chapter <= len(counts) and 1 <= verse <= counts[chapter - 1]:
            return [canonical_verse_key(book_id, chapter, verse)]
        return []

    if granularity != "range" or row.get("verse_start") is None:
        return []

    chapter_start = row.get("chapter")
    chapter_end = row.get("chapter_end")
    if chapter_end is None:
        chapter_end = chapter_start
    verse_start = row.get("verse_start")
    verse_end = row.get("verse_end")
    if verse_end is None:
        verse_end = verse_start

    # Explicit endpoint validation. No clamping, no partial mapping.
    if chapter_start is None or chapter_end is None:
        return []
    if verse_start is None or verse_end is None:
        return []
    if not 1 <= chapter_start <= len(counts):
        return []
    if not 1 <= chapter_end <= len(counts):
        return []
    if not 1 <= verse_start <= counts[chapter_start - 1]:
        return []
    if not 1 <= verse_end <= counts[chapter_end - 1]:
        return []
    if (chapter_start, verse_start) > (chapter_end, verse_end):
        return []

    keys = []
    for chapter in range(chapter_start, chapter_end + 1):
        limit = counts[chapter - 1]
        start = verse_start if chapter == chapter_start else 1
        end = verse_end if chapter == chapter_end else limit
        for verse in range(start, end + 1):
            keys.append(canonical_verse_key(book_id, chapter, verse))
    return keys


def map_raw_reference(raw, table=None, universe=None):
    """Map one raw string, optionally memoised by exact raw string."""
    if universe is not None:
        cached = universe.get(raw)
        if cached is not None:
            return cached
    core = classify_raw_reference(raw, table=table)
    if universe is not None:
        universe[raw] = core
    return core


# --------------------------------------------------------------------------
# Finding-level mapping
# --------------------------------------------------------------------------


def map_finding(passage, finding_ref, table=None, universe=None, uid_guard=None):
    """Build the ``finding_reference_map`` row for one final verified finding."""
    finding = finding_ref["finding"]
    identity = build_identity(passage, finding_ref)
    uid = finding_uid(identity)
    if uid_guard is not None:
        uid_guard.add(uid)

    raw_refs = finding.get("scripture_refs")
    if raw_refs is None:
        raw_refs = []
    if not isinstance(raw_refs, list):
        raw_refs = [raw_refs]

    outcomes = []
    verse_keys = []
    verse_sources = {}
    expanded_total = 0
    status_counts = Counter()

    for raw_index, raw in enumerate(raw_refs):
        core = map_raw_reference(raw, table=table, universe=universe)
        status_counts[core["status"]] += 1
        keys = list(core["verse_keys"])
        expanded_total += len(keys)
        for key in keys:
            if key not in verse_sources:
                verse_sources[key] = []
            if raw not in verse_sources[key]:
                verse_sources[key].append(raw)
        verse_keys.extend(keys)
        outcomes.append({
            "raw_index": raw_index,
            "raw": raw,
            "raw_sha256": sha256_text(raw) if isinstance(raw, str) else None,
            "status": core["status"],
            "reason": core["reason"],
            "unexplained_residual": core["unexplained_residual"],
            "unexplained_tokens": list(core["unexplained_tokens"]),
            "unexplained_symbols": list(core["unexplained_symbols"]),
            "normalized_references": list(core["accepted_rows"]),
            "context": core["context"],
            "canonical_verse_keys": keys,
            "canonical_verse_count": len(keys),
            "engine_rows": list(core["engine_rows"]),
        })

    unique_keys = sorted(set(verse_keys))

    return {
        "schema_version": SCHEMA_VERSION,
        "mapper_version": MAPPER_VERSION,
        "engine_version": ENGINE.VERSION,
        "finding_uid": uid,
        "identity": identity,
        "passage": {
            "chunk_id": passage.get("chunk_id"),
            "source_document": passage.get("source_document"),
            "source_document_sha256": passage.get("sha256"),
            "source_collection": passage.get("source_collection"),
            "current_path": passage.get("current_path"),
            "research_generation": passage.get("research_generation"),
            "final_pass": finding_ref["final_pass"],
            "final_pass_key": finding_ref["final_pass_key"],
        },
        "finding": {
            "finding_index": finding_ref["finding_index"],
            "topic": finding.get("topic"),
            "quote": finding.get("quote"),
            "note": finding.get("note"),
            "confidence": finding.get("confidence"),
            "provenance": finding.get("provenance"),
            "speaker": finding.get("speaker"),
            "char_start": finding.get("char_start"),
            "char_end": finding.get("char_end"),
            "occurrences": finding.get("occurrences"),
        },
        "raw_scripture_refs": list(raw_refs),
        "raw_reference_count": len(raw_refs),
        "outcomes": outcomes,
        "status_counts": dict(sorted(status_counts.items())),
        "mapped_verse_keys": unique_keys,
        "mapped_verse_count": len(unique_keys),
        "has_verse_mapping": bool(unique_keys),
        # provenance of each deduplicated verse coordinate (raw_occurrences kept
        # separately so dedup never loses where a coordinate came from)
        "verse_key_sources": [{"verse_key": k, "raw_refs": verse_sources[k]}
                              for k in unique_keys],
        "expanded_mapping_count": expanded_total,
        "duplicate_mappings_removed": expanded_total - len(unique_keys),
    }


def verse_evidence_rows(map_row, table=None):
    """Yield ``verse_evidence_index`` rows for one finding_reference_map row."""
    coordinate_table = table if table is not None else ENGINE.CANONICAL_COORDINATES
    book_by_id = {index + 1: name for index, name in enumerate(ENGINE.CANON)}
    sources = {entry["verse_key"]: entry["raw_refs"]
               for entry in map_row["verse_key_sources"]}
    passage = map_row["passage"]
    for key in map_row["mapped_verse_keys"]:
        try:
            book_part, chapter_part, verse_part = key.split(":")
            book_id = int(book_part[1:])
            chapter = int(chapter_part[1:])
            verse = int(verse_part[1:])
        except (ValueError, IndexError):
            continue
        book = book_by_id.get(book_id)
        yield {
            "schema_version": SCHEMA_VERSION,
            "mapper_version": MAPPER_VERSION,
            "engine_version": ENGINE.VERSION,
            "finding_uid": map_row["finding_uid"],
            "verse_key": key,
            "canonical": "{} {}:{}".format(book, chapter, verse),
            "book": book,
            "book_id": book_id,
            "chapter": chapter,
            "verse": verse,
            "raw_refs": list(sources.get(key, [])),
            "source_document_sha256": passage["source_document_sha256"],
            "chunk_id": passage["chunk_id"],
            "research_generation": passage["research_generation"],
            "final_pass": passage["final_pass"],
            "finding_topic": map_row["finding"]["topic"],
        }


def anomaly_rows(map_row):
    """Yield anomaly/unmapped rows for one finding_reference_map row.

    Non-mapped raw strings produce one row each. Accepted strings that also
    contain invalid or unresolved coordinate rows keep those rows as anomalies
    so no evidence is lost and no invalid coordinate is ever mapped.
    """
    passage = map_row["passage"]
    common = {
        "schema_version": SCHEMA_VERSION,
        "mapper_version": MAPPER_VERSION,
        "engine_version": ENGINE.VERSION,
        "finding_uid": map_row["finding_uid"],
        "source_document_sha256": passage["source_document_sha256"],
        "chunk_id": passage["chunk_id"],
        "research_generation": passage["research_generation"],
        "final_pass": passage["final_pass"],
        "finding_topic": map_row["finding"]["topic"],
        "finding_index": map_row["finding"]["finding_index"],
    }
    for outcome in map_row["outcomes"]:
        status = outcome["status"]
        if status in NON_MAPPED_STATUSES:
            row = dict(common)
            row.update({
                "anomaly_kind": "raw_reference",
                "status": status,
                "reason": outcome["reason"],
                "raw_index": outcome["raw_index"],
                "raw_ref": outcome["raw"],
                "unexplained_residual": outcome["unexplained_residual"],
                "unexplained_tokens": outcome["unexplained_tokens"],
                "unexplained_symbols": outcome["unexplained_symbols"],
                "engine_rows": outcome["engine_rows"],
                "context": outcome["context"],
            })
            yield row
        else:
            for engine_row in outcome["engine_rows"]:
                if engine_row["canonical_status"] == "asserted_invalid" or \
                        engine_row["resolution_status"] == "unresolved":
                    row = dict(common)
                    row.update({
                        "anomaly_kind": "embedded_coordinate",
                        "status": ("asserted_invalid"
                                   if engine_row["canonical_status"] == "asserted_invalid"
                                   else "unresolved"),
                        "reason": ("asserted_invalid_coordinate"
                                   if engine_row["canonical_status"] == "asserted_invalid"
                                   else "no_determinable_book"),
                        "raw_index": outcome["raw_index"],
                        "raw_ref": outcome["raw"],
                        "unexplained_residual": "",
                        "unexplained_tokens": [],
                        "unexplained_symbols": [],
                        "engine_rows": [engine_row],
                        "context": None,
                    })
                    yield row


# --------------------------------------------------------------------------
# Corpus audit (read-only, streaming)
# --------------------------------------------------------------------------


def audit_corpus(research_path=DEFAULT_RESEARCH_ARTIFACT, samples=5,
                 limit=None, table=None, verify_hashes=False):
    """Run the complete mapping pipeline read-only and return summary stats."""
    coordinate_table = table if table is not None else ENGINE.CANONICAL_COORDINATES
    sample_limit = max(0, int(samples))

    stats = Counter()
    finding_topics = Counter()
    finding_generations = Counter()
    mapped_topics = Counter()
    mapped_generations = Counter()
    raw_status_occurrences = Counter()
    raw_status_unique = Counter()
    raw_status_by_finding = Counter()
    engine_row_status = Counter()
    seen_raw = {}
    seen_verses = set()
    raw_examples = {}
    status_samples = {status: [] for status in ALL_STATUSES}
    uid_guard = FindingUidGuard()
    universe = {}
    first_finding_uid = None
    first_passage_uid = None

    def note_sample(status, record):
        bucket = status_samples[status]
        if len(bucket) < sample_limit:
            bucket.append(record)

    with open(research_path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if limit is not None and stats["passage_records"] >= limit:
                break
            passage = json.loads(line)
            stats["passage_records"] += 1
            stats["quarantined_findings_in_selected_final_passes"] += \
                count_quarantined_in_final_pass(passage)
            if (passage.get("chunk") or {}).get("passes", {}).get("escalate"):
                stats["passages_with_escalation_pass"] += 1

            for finding_ref in iter_final_findings(passage):
                row = map_finding(passage, finding_ref, table=coordinate_table,
                                  universe=universe, uid_guard=uid_guard)
                if first_finding_uid is None:
                    first_finding_uid = row["finding_uid"]
                    first_passage_uid = row["passage"]
                stats["final_verified_findings"] += 1
                stats["unique_finding_uids"] = len(uid_guard)
                finding_topics[row["finding"]["topic"]] += 1
                finding_generations[row["passage"]["research_generation"]] += 1

                if row["raw_reference_count"] == 0:
                    stats["findings_with_no_scripture_refs"] += 1
                else:
                    stats["findings_with_one_or_more_scripture_refs"] += 1

                if row["has_verse_mapping"]:
                    stats["findings_with_verse_mapping"] += 1
                    mapped_topics[row["finding"]["topic"]] += 1
                    mapped_generations[row["passage"]["research_generation"]] += 1
                elif row["raw_reference_count"]:
                    stats["findings_with_refs_but_no_verse_mapping"] += 1

                stats["total_raw_reference_strings"] += row["raw_reference_count"]
                stats["expanded_mappings_pre_dedup"] += row["expanded_mapping_count"]
                stats["unique_finding_verse_mappings"] += row["mapped_verse_count"]
                stats["duplicate_per_finding_verse_mappings_removed"] += \
                    row["duplicate_mappings_removed"]
                seen_verses.update(row["mapped_verse_keys"])

                statuses_seen = set()
                for outcome in row["outcomes"]:
                    raw = outcome["raw"]
                    status = outcome["status"]
                    raw_status_occurrences[status] += 1
                    if raw not in seen_raw:
                        seen_raw[raw] = status
                        raw_status_unique[status] += 1
                    statuses_seen.add(status)
                    if outcome["canonical_verse_count"] > 1:
                        stats["raw_refs_producing_multiple_normalized_mappings"] += 1
                    for engine_row in outcome["engine_rows"]:
                        engine_row_status[engine_row["canonical_status"]] += 1
                    if status in NON_MAPPED_STATUSES:
                        note_sample(status, {
                            "finding_uid": row["finding_uid"],
                            "chunk_id": row["passage"]["chunk_id"],
                            "source_document_sha256": row["passage"]["source_document_sha256"],
                            "research_generation": row["passage"]["research_generation"],
                            "final_pass": row["passage"]["final_pass"],
                            "finding_topic": row["finding"]["topic"],
                            "finding_index": row["finding"]["finding_index"],
                            "raw_index": outcome["raw_index"],
                            "raw_ref": raw,
                            "status": status,
                            "reason": outcome["reason"],
                            "unexplained_residual": outcome["unexplained_residual"],
                            "normalized": [r["canonical"] for r in outcome["normalized_references"]],
                            "context": outcome["context"],
                        })
                for status in statuses_seen:
                    raw_status_by_finding[status] += 1

    summary = {
        "mapper_version": MAPPER_VERSION,
        "schema_version": SCHEMA_VERSION,
        "identity_version": IDENTITY_VERSION,
        "engine_version": ENGINE.VERSION,
        "engine_expected_version": EXPECTED_ENGINE_VERSION,
        "engine_file_sha256": sha256_file(ENGINE_FILE_PATH),
        "engine_file_sha256_matches_expected": (
            sha256_file(ENGINE_FILE_PATH) == EXPECTED_ENGINE_FILE_SHA256),
        "coordinates_artifact_sha256": sha256_file(COORDINATES_PATH),
        "coordinates_artifact_sha256_matches_expected": (
            sha256_file(COORDINATES_PATH) == EXPECTED_COORDINATES_SHA256),
        "coordinates_counts_match_expected": _coordinates_counts_match(),
        "harmless_residual_words": sorted(HARMLESS_RESIDUAL_WORDS),
        "harmless_residual_chars": "".join(sorted(HARMLESS_RESIDUAL_CHARS)),
        "final_pass_rule": FINAL_PASS_RULE,
        "research_artifact": research_path,
        "coordinates_path": COORDINATES_PATH,
        "passage_records": stats["passage_records"],
        "passages_with_escalation_pass": stats["passages_with_escalation_pass"],
        "final_verified_findings": stats["final_verified_findings"],
        "quarantined_findings_in_selected_final_passes":
            stats["quarantined_findings_in_selected_final_passes"],
        "unique_finding_uids": stats["unique_finding_uids"],
        "finding_uid_collisions": uid_guard.collisions,
        "duplicate_finding_uid_samples": uid_guard.duplicate_uids,
        "findings_with_no_scripture_refs": stats["findings_with_no_scripture_refs"],
        "findings_with_one_or_more_scripture_refs":
            stats["findings_with_one_or_more_scripture_refs"],
        "findings_with_verse_mapping": stats["findings_with_verse_mapping"],
        "findings_with_refs_but_no_verse_mapping":
            stats["findings_with_refs_but_no_verse_mapping"],
        "total_raw_reference_strings": stats["total_raw_reference_strings"],
        "unique_raw_reference_strings": len(seen_raw),
        "raw_status_occurrences": dict(sorted(raw_status_occurrences.items())),
        "raw_status_unique_strings": dict(sorted(raw_status_unique.items())),
        "raw_status_findings_touched": dict(sorted(raw_status_by_finding.items())),
        "engine_row_canonical_status": dict(sorted(engine_row_status.items())),
        "mapped_verse_raw_refs":
            raw_status_occurrences[STATUS_MAPPED_VERSE],
        "mapped_range_raw_refs":
            raw_status_occurrences[STATUS_MAPPED_RANGE],
        "mapped_mixed_raw_refs":
            raw_status_occurrences[STATUS_MAPPED_MIXED],
        "mixed_context_raw_refs":
            raw_status_occurrences[STATUS_MIXED_CONTEXT],
        "chapter_only_raw_refs":
            raw_status_occurrences[STATUS_CHAPTER_ONLY],
        "book_only_raw_refs":
            raw_status_occurrences[STATUS_BOOK_ONLY],
        "asserted_invalid_raw_refs":
            raw_status_occurrences[STATUS_ASSERTED_INVALID],
        "unresolved_raw_refs":
            raw_status_occurrences[STATUS_UNRESOLVED],
        "partial_parse_raw_refs":
            raw_status_occurrences[STATUS_PARTIAL_PARSE],
        "unstructured_raw_refs":
            raw_status_occurrences[STATUS_UNSTRUCTURED],
        "unique_finding_verse_mappings": stats["unique_finding_verse_mappings"],
        "expanded_mappings_pre_dedup": stats["expanded_mappings_pre_dedup"],
        "duplicate_per_finding_verse_mappings_removed":
            stats["duplicate_per_finding_verse_mappings_removed"],
        "unique_canonical_verses_represented": len(seen_verses),
        "raw_refs_producing_multiple_normalized_mappings":
            stats["raw_refs_producing_multiple_normalized_mappings"],
        "counts_by_research_finding_type": dict(sorted(finding_topics.items())),
        "counts_by_research_generation": dict(sorted(finding_generations.items())),
        "mapped_findings_by_research_finding_type":
            dict(sorted(mapped_topics.items())),
        "mapped_findings_by_research_generation":
            dict(sorted(mapped_generations.items())),
        "first_finding_uid": first_finding_uid,
        "first_finding_passage": first_passage_uid,
    }

    if verify_hashes:
        research_sha = sha256_file(research_path)
        summary["research_artifact_sha256"] = research_sha
        summary["research_artifact_sha256_matches_expected"] = (
            research_sha == EXPECTED_RESEARCH_SHA256)
        summary["coordinates_source"] = ENGINE.COORDINATES_SOURCE

    summary["samples"] = {
        status: status_samples[status] for status in NON_MAPPED_STATUSES
        if status_samples[status]
    }
    return summary


# --------------------------------------------------------------------------
# Artifact writer (used with temporary directories in this milestone)
# --------------------------------------------------------------------------


def _artifact_metadata(research_path, coordinates_path):
    return {
        "schema_version": SCHEMA_VERSION,
        "mapper_version": MAPPER_VERSION,
        "mapper_file": os.path.abspath(__file__),
        "identity_version": IDENTITY_VERSION,
        "engine_version": ENGINE.VERSION,
        "engine_expected_version": EXPECTED_ENGINE_VERSION,
        "engine_file_sha256": sha256_file(os.path.abspath(ENGINE.__file__)),
        "mapper_file_sha256": sha256_file(os.path.abspath(__file__)),
        "input_research_artifact": research_path,
        "input_research_artifact_sha256": sha256_file(research_path),
        "canonical_coordinates_artifact": coordinates_path,
        "canonical_coordinates_sha256": sha256_file(coordinates_path),
    }


def write_artifacts(research_path=DEFAULT_RESEARCH_ARTIFACT, out_dir=None,
                    generated_at=None, limit=None, table=None, pinned=True):
    """Write the versioned JSONL artifacts + manifest to ``out_dir``.

    ``pinned=True`` (the default, used for production) validates every pinned
    production input BEFORE any output file is created and fails closed with
    ``ProductionInputError`` on any mismatch. It additionally refuses a
    caller-supplied ``table`` coordinate override and a non-``None`` ``limit``
    (partial write), both before creating the output directory. ``pinned=False``
    is a test-only/unpinned escape hatch for synthetic corpora; it must never be
    used to produce the production artifact.
    """
    if out_dir is None:
        raise ValueError("out_dir is required")
    # Pinned production guards. These run BEFORE validate_production_inputs()
    # and before any output directory or file is created, so a caller-supplied
    # coordinate table or a deliberately truncated write can never slip past a
    # successfully validated production pin.
    if pinned and table is not None:
        raise ProductionInputError(
            "pinned production write refuses a caller-supplied coordinate table "
            "(table must be None when pinned=True); the pinned "
            "gd_canonical_coordinates.json is the only production coordinate "
            "source")
    if pinned and limit is not None:
        raise ProductionInputError(
            "pinned production write refuses a partial/truncated write "
            "(limit must be None when pinned=True); got limit={!r}".format(limit))
    if pinned:
        validate_production_inputs(research_path)
    coordinate_table = table if table is not None else ENGINE.CANONICAL_COORDINATES
    os.makedirs(out_dir, exist_ok=True)
    metadata = _artifact_metadata(research_path, COORDINATES_PATH)
    metadata["inputs_pinned"] = bool(pinned)
    generated_at = generated_at or datetime.datetime.now(
        datetime.timezone.utc).isoformat()

    counts = Counter()
    uid_guard = FindingUidGuard()
    universe = {}
    seen_verses = set()
    anomaly_total = 0

    map_path = os.path.join(out_dir, "finding_reference_map.jsonl")
    verse_path = os.path.join(out_dir, "verse_evidence_index.jsonl")
    anomaly_path = os.path.join(out_dir, "reference_anomalies.jsonl")

    with open(map_path, "w", encoding="utf-8") as map_handle, \
            open(verse_path, "w", encoding="utf-8") as verse_handle, \
            open(anomaly_path, "w", encoding="utf-8") as anomaly_handle:
        with open(research_path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                if limit is not None and counts["passage_records"] >= limit:
                    break
                passage = json.loads(line)
                counts["passage_records"] += 1
                for finding_ref in iter_final_findings(passage):
                    row = map_finding(passage, finding_ref,
                                      table=coordinate_table, universe=universe,
                                      uid_guard=uid_guard)
                    counts["findings"] += 1
                    counts["findings_with_verse_mapping"] += int(
                        row["has_verse_mapping"])
                    counts["verse_mappings"] += row["mapped_verse_count"]
                    counts["duplicate_mappings_removed"] += \
                        row["duplicate_mappings_removed"]
                    seen_verses.update(row["mapped_verse_keys"])
                    map_handle.write(canonical_json(row) + "\n")
                    for verse_row in verse_evidence_rows(row, table=coordinate_table):
                        verse_handle.write(canonical_json(verse_row) + "\n")
                    for anomaly in anomaly_rows(row):
                        anomaly_handle.write(canonical_json(anomaly) + "\n")
                        anomaly_total += 1

    manifest = {
        "artifact": "gd_bible_revision_reference_map",
        "description": (
            "Deterministic verse-addressable evidence bridge from the GD "
            "full-HIGH combined research corpus. Derived, non-authoritative, "
            "model-attributed references preserved verbatim."
        ),
        "generated_at": generated_at,
        **metadata,
        "final_pass_rule": FINAL_PASS_RULE,
        "finding_uid_spec": {
            "algorithm": "sha256",
            "serialization": ("json.dumps(sort_keys=True,separators=(',',':'),"
                              "ensure_ascii=False) encoded utf-8"),
            "identity_version": IDENTITY_VERSION,
            "payload_fields": [
                "identity_version", "source_document_sha256",
                "source_document", "chunk_id", "research_generation",
                "final_pass", "final_pass_key", "finding_index",
                "finding_topic", "finding_char_start", "finding_char_end",
                "finding_quote_sha256",
            ],
        },
        "strict_consumption_rule": {
            "per_array_element": True,
            "book_inheritance_across_elements": False,
            "harmless_residual_chars": "".join(sorted(HARMLESS_RESIDUAL_CHARS)),
            "harmless_residual_words": sorted(HARMLESS_RESIDUAL_WORDS),
            "harmless_word_source": "gd_scripture_engine._CITATION_CONNECTORS only",
            "excluded_engine_vocabularies": [
                "_GENERIC_PRECEDING_WORDS", "_STRONG_CITATION_CUES",
                "_CUE_FILLERS",
            ],
            "character_allowlist_enforced": True,
            "unexplained_residual_policy": "classified partial_parse; no mapping",
        },
        "range_expansion": {
            "rule": ("asserted-valid verse ranges expand to exact KJV verse "
                     "coordinates from gd_canonical_coordinates.json; never "
                     "guess across an invalid coordinate"),
            "dedup": "per finding_uid + canonical verse key",
        },
        "status_taxonomy": list(ALL_STATUSES),
        "mapped_statuses": list(MAPPED_STATUSES),
        "non_mapped_statuses": list(NON_MAPPED_STATUSES),
        "mixed_context_semantics": (
            "non-mapped defensive state: verse-level + chapter/book-level "
            "accepted rows in one raw string yield no verse evidence and one "
            "anomaly row with all engine rows preserved"),
        "production_pins": {
            "expected_engine_version": EXPECTED_ENGINE_VERSION,
            "expected_engine_file_sha256": EXPECTED_ENGINE_FILE_SHA256,
            "expected_canonical_coordinates_sha256": EXPECTED_COORDINATES_SHA256,
            "expected_research_artifact_sha256": EXPECTED_RESEARCH_SHA256,
            "expected_canonical_coordinate_counts": dict(EXPECTED_CANONICAL_COUNTS),
            "pins_enforced": bool(pinned),
            "rejects_coordinate_table_override": bool(pinned),
            "rejects_non_none_limit": bool(pinned),
        },
        "counts": {
            "passages": counts["passage_records"],
            "findings": counts["findings"],
            "unique_finding_uids": len(uid_guard),
            "finding_uid_collisions": uid_guard.collisions,
            "findings_with_verse_mapping": counts["findings_with_verse_mapping"],
            "verse_evidence_rows": counts["verse_mappings"],
            "unique_canonical_verses": len(seen_verses),
            "duplicate_mappings_removed": counts["duplicate_mappings_removed"],
            "anomaly_rows": anomaly_total,
        },
        "provenance": {
            "input_research_artifact": research_path,
            "generation": "derived from the GD full-HIGH combined artifact",
            "archive_originals_modified": False,
            "bible_text_modified": False,
        },
    }
    manifest_path = os.path.join(out_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")
    return manifest


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="GD Bible Revision Mapping V1 -- deterministic reference bridge.")
    parser.add_argument("--research", default=DEFAULT_RESEARCH_ARTIFACT,
                        help="combined research JSONL (read-only)")
    parser.add_argument("--audit-only", action="store_true",
                        help="run the full corpus read-only and print statistics")
    parser.add_argument("--write", action="store_true",
                        help="write derived artifacts (requires --out)")
    parser.add_argument("--out", default=None, help="output directory for --write")
    parser.add_argument("--samples", type=int, default=5,
                        help="human-review samples per non-mapped category")
    parser.add_argument("--limit", type=int, default=None,
                        help="debug: only the first N passages")
    parser.add_argument("--verify-hashes", action="store_true",
                        help="recompute input artifact SHA-256 values")
    parser.add_argument("--unpinned-inputs", action="store_true",
                        help="TEST ONLY: skip production pin validation on --write "
                             "(synthetic corpora); never use for production output")
    parser.add_argument("--generated-at", default=None,
                        help="override manifest timestamp (tests)")
    return parser


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    if args.write:
        if not args.out:
            raise SystemExit("--write requires --out")
        if args.unpinned_inputs:
            print("WARNING: --unpinned-inputs is test-only; production pins are NOT "
                  "enforced for this run", file=sys.stderr)
        try:
            manifest = write_artifacts(args.research, args.out,
                                       generated_at=args.generated_at,
                                       limit=args.limit,
                                       pinned=not args.unpinned_inputs)
        except ProductionInputError as exc:
            print("ERROR: {}".format(exc), file=sys.stderr)
            raise
        print(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False))
        return 0

    summary = audit_corpus(args.research, samples=args.samples, limit=args.limit,
                           verify_hashes=args.verify_hashes)
    print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
