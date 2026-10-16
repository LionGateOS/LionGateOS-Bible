"""gd_bible_revision_review_packets.py -- GD Bible Revision Review Packets V1.

Deterministic, CPU-only, read-only builder of per-verse *review packets* for the
GD Bible revision program. The packets are the evidence payload that a later
Bible-revision judgment stage (RTX 3090 Ti / local Qwen) will consume.

This milestone makes NO editorial decision and NO model call. It does not edit
the canonical GD Bible, the standard KJV asset, the archive originals or the
production evidence bridge. It only assembles complete, traceable, per-verse
evidence packets and audits them.

Track A -- Existing Change Audit
    Every verse currently changed by the GD ``TRANSFORMATION_MANIFEST.json``
    (335 verses). Packets are emitted even when no mapped archive evidence
    exists, with an explicit ``direct_archive_verse_evidence = false``.

Track B -- New Change Discovery Tier 1
    Every *not-currently-changed* verse carrying at least 20 archive findings
    whose topic is one of ``translation``, ``terminology``, ``wording``,
    ``capitalization`` (316 verses). "scripture" alone never qualifies a
    candidate.

Join rules (authoritative, no re-derivation)
--------------------------------------------
``verse_evidence_index.jsonl`` is the ONLY authoritative source of
(``verse_key``, ``finding_uid``) association. Findings are never re-mapped from
their raw reference strings here, and no additional verse association is ever
inferred. ``finding_reference_map.jsonl`` supplies the full finding record for
each ``finding_uid``.

Bible text is joined verbatim by ``book_id``/``chapter``/``verse`` from both the
standard KJV asset and the current GD asset; the join fails closed and never
normalizes, rewrites or repairs text.

Evidentiary boundary (preserved from the mapping layer)
-------------------------------------------------------
Archive ``scripture_refs`` remain MODEL-ATTRIBUTED evidence. A packet records
attributions; it does not promote them to fact. Absence of mapped archive
evidence for a changed verse is NOT evidence that the current wording is wrong.

Determinism
-----------
Packets are emitted in canonical verse order, findings are deduplicated by
``finding_uid`` and ordered by a documented stable sort key, and every count
dictionary is key-sorted. Two runs over identical inputs produce byte-identical
JSONL streams. Only ``generated_at`` in the stream manifest varies, and it can
be pinned with ``--generated-at`` or ``SOURCE_DATE_EPOCH``.

Usage
-----
    # deterministic audit only (default; writes nothing)
    python3 gd_bible_revision_review_packets.py --audit-only

    # explicit test/unpinned mode (still writes nothing without --write)
    python3 gd_bible_revision_review_packets.py --audit-only --allow-unpinned

    # production write (NOT part of this milestone; fails closed on pin drift)
    python3 gd_bible_revision_review_packets.py --write --out-dir review_packets_v1

Output design (production artifact, not written by this milestone)
------------------------------------------------------------------
    existing_change_review_packets.jsonl   (Track A)
    new_change_tier1_review_packets.jsonl  (Track B)
    owner_candidate_review_overlay.jsonl   (Track C overlay)
    review_universe_index.jsonl            (Track C index)
    manifest.json                          (pins, counts, provenance)

Track C uses an owner overlay plus unique review-universe index rather than duplicating
complete Track A/B packets. No AI judgment is written to any of those files.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)
_GD_DIR = os.path.dirname(os.path.dirname(WORKSPACE_DIR))

import gd_bible_revision_mapping as MAPPING  # noqa: E402
import gd_scripture_engine as ENGINE  # noqa: E402


BUILDER_SOURCE_PATH = os.path.abspath(__file__)

PACKET_BUILDER_VERSION = "1.0.0"
PACKET_SCHEMA_VERSION = "gd-bible-revision-review-packet/1"
SOURCE_MAPPING_SCHEMA_VERSION = "gd-bible-revision-reference-map/1"
SOURCE_MAPPING_ARTIFACT = "gd_bible_revision_reference_map"

TRACK_A = "A"
TRACK_B = "B"
TRACK_A_NAME = "existing_change_audit"
TRACK_B_NAME = "new_change_discovery_tier_1"
PRIORITY_TIER_A = "existing_change_audit"
PRIORITY_TIER_B = "new_change_tier_1"

TRACK_A_STREAM = "existing_change_review_packets.jsonl"
TRACK_B_STREAM = "new_change_tier1_review_packets.jsonl"
MANIFEST_NAME = "manifest.json"

REVISION_RELEVANT_TOPICS = (
    "capitalization",
    "terminology",
    "translation",
    "wording",
)
REVISION_RELEVANT_TOPIC_SET = frozenset(REVISION_RELEVANT_TOPICS)
TRACK_B_MIN_REVISION_RELEVANT_FINDINGS = 20

BOOK_ID_MIN = 1
BOOK_ID_MAX = 66
EXPECTED_BOOK_COUNT = 66
EXPECTED_CHAPTER_COUNT = 1189
EXPECTED_VERSE_COUNT = 31102

TRACK_A_STATEMENT = (
    "Selected for review because this verse is currently changed by the GD "
    "TRANSFORMATION_MANIFEST (existing GD transformation review)."
)
TRACK_A_NO_EVIDENCE_NOTE = (
    "No mapped archive verse evidence exists for this verse. Absence of mapped "
    "archive evidence is NOT evidence that the current wording is wrong."
)
TRACK_B_STATEMENT = (
    "Selected as a new-change candidate because this not-currently-changed "
    "verse has at least {} archive findings whose topic is one of {}".format(
        TRACK_B_MIN_REVISION_RELEVANT_FINDINGS,
        ", ".join(REVISION_RELEVANT_TOPICS),
    )
)
TRACK_B_CANDIDATE_NOTE = (
    "Candidate only. This packet makes no editorial decision and does not "
    "assert that the current wording is wrong."
)

PROVENANCE_STATEMENT = (
    "Review packets are a deterministic, read-only projection of the frozen "
    "production evidence bridge ({} / {}) joined to the standard KJV asset, the "
    "current GD asset and the GD transformation manifest. Verse association is "
    "taken verbatim from verse_evidence_index.jsonl; no reference is re-mapped "
    "and no association is inferred. Bible text is preserved verbatim.".format(
        SOURCE_MAPPING_ARTIFACT, SOURCE_MAPPING_SCHEMA_VERSION)
)
EVIDENCE_CLASS_STATEMENT = (
    "Archive scripture references and their verse associations remain "
    "MODEL-ATTRIBUTED evidence from the GD archive research corpus. A packet "
    "records attributions; it does not promote them to authoritative fact, and "
    "it makes no Bible translation decision."
)
EDITORIAL_BOUNDARY_STATEMENT = (
    "No model judgment, no editorial decision and no Bible text change is "
    "produced by the packet builder. The canonical GD Bible is not modified."
)

# --------------------------------------------------------------------------
# Frozen inputs (paths + pins)
# --------------------------------------------------------------------------

DEFAULT_EVIDENCE_BRIDGE_DIR = os.path.join(
    os.environ.get("GD_ARCHIVE_ROOT",
                   "/home/liongateos/PCOG-Research-Archive"),
    "research", "gd-bible-revision-mapping-v1"
)
DEFAULT_STANDARD_KJV_ASSET = os.path.join(
    _GD_DIR, "assets", "bible", "en_kjv.json"
)
DEFAULT_CURRENT_GD_ASSET = os.path.join(
    _GD_DIR, "assets", "bible", "kjv_modified.json"
)
DEFAULT_TRANSFORMATION_MANIFEST = os.path.join(
    _GD_DIR, "docs", "bible", "TRANSFORMATION_MANIFEST.json"
)

# Role -> (filename inside the evidence bridge dir, sha256, expected row count)
EVIDENCE_BRIDGE_FILES = {
    "finding_reference_map": (
        "finding_reference_map.jsonl",
        "7b98d8a9a7ce1748dfd65fbada34e95e0a53cd8d8454dcdf4ff5c5410f0bda8f",
        58498,
    ),
    "verse_evidence_index": (
        "verse_evidence_index.jsonl",
        "f6cc556ed145848079827ec8f134e38ec8e39e7302f6b2fa0107d77e0631a52a",
        67109,
    ),
    "reference_anomalies": (
        "reference_anomalies.jsonl",
        "e66309b7e39b793b3260803096dba71fbac0b23ea7dae7f126ef50b2e2bc001b",
        4061,
    ),
    "evidence_bridge_manifest": (
        "manifest.json",
        "9329dbf1d451ad7711785cc3935168814d1e5dd9a4b92a36328ac0c07a84eab2",
        None,
    ),
}

# Non-bridge frozen pins (hashes measured and recorded by this milestone).
STANDARD_KJV_ASSET_SHA256 = (
    "4109ee74d422614995325b5d2f43da9ec35d9be547d6a11bc68fb0978179585f"
)
CURRENT_GD_ASSET_SHA256 = (
    "f2e29b70e61fb1345d80721905caf9f59049f5265ad1c28bd2f9e2d82fedbb4c"
)
TRANSFORMATION_MANIFEST_SHA256 = (
    "c3451fb48212c0c8081a57b3b1db131fa969da0d554a71e7b2923994a1cb333f"
)

# Frozen coordinate + code dependencies. A pinned run must use exactly these
# files, must never load an alternate coordinate artifact, and must record the
# hashes and versions it actually used.
CANONICAL_COORDINATES_PATH = os.path.abspath(MAPPING.COORDINATES_PATH)
CANONICAL_COORDINATES_SHA256 = (
    "a0d2c672f6c06f3307c22027216ae53f98bdf910903ef86c049fbbdeb4e9753f"
)
COORDINATE_COUNT_PINS = {"book_count": EXPECTED_BOOK_COUNT,
                         "chapter_count": EXPECTED_CHAPTER_COUNT,
                         "verse_count": EXPECTED_VERSE_COUNT}
MAPPING_MODULE_PATH = os.path.abspath(MAPPING.__file__)
MAPPING_MODULE_SHA256 = (
    "9ef2aaa8bd174fb028d177014fc4592a6e7a05681ad135466f9a04249012fb24"
)
MAPPING_MODULE_VERSION_EXPECTED = "1.0.0"
ENGINE_MODULE_PATH = os.path.abspath(ENGINE.__file__)
ENGINE_MODULE_SHA256 = (
    "7e336688d359693b046034a7bf49b827e1edc06da510f3bbb8a9310833b670fa"
)
ENGINE_MODULE_VERSION_EXPECTED = "1.5.0"

# Durable owner-specified review inputs (Track C candidates + style policies).
# This is a living owner document: editing it changes the pinned hash below, so
# the edit is an explicit, reviewable event. Re-pin OWNER_INPUTS_SHA256 with
#   sha256sum docs/bible/editorial/gd_bible_owner_review_inputs.json
# after reviewing an owner edit; a pinned build otherwise fails closed.
OWNER_INPUTS_PATH = os.path.join(_GD_DIR, "docs", "bible", "editorial",
                                  "gd_bible_owner_review_inputs.json")
OWNER_INPUTS_SHA256 = (
    "d6eb6552e46626dc4ef234d8f18f230a1c7b34461b8eb5f2109a1b1ae477e824"
)
OWNER_INPUTS_ARTIFACT = "gd-bible-owner-review-inputs"
OWNER_INPUTS_SCHEMA_VERSION = "gd-bible-owner-review-inputs/1"
OWNER_PROVENANCE_CLASS = "owner_specified_editorial_candidate"
OWNER_CANDIDATE_STATUS = "review_candidate"

# Track C = owner-specified review candidates. They force later review even
# with no archive evidence, and are never archive evidence themselves.
TRACK_C = "C"
TRACK_C_NAME = "owner_specified_review_candidates"
PRIORITY_TIER_C = "owner_specified"
OWNER_OVERLAY_SCHEMA_VERSION = "gd-bible-owner-review-overlay/1"
REVIEW_UNIVERSE_SCHEMA_VERSION = "gd-bible-review-universe-index/1"
OWNER_OVERLAY_RECORD_TYPE = "owner_candidate_overlay"
REVIEW_UNIVERSE_RECORD_TYPE = "review_universe_entry"
OWNER_OVERLAY_STREAM = "owner_candidate_review_overlay.jsonl"
REVIEW_UNIVERSE_STREAM = "review_universe_index.jsonl"
TRACK_C_STATEMENT = (
    "Owner-specified review candidate. It is sufficient reason to force the "
    "verse into later review even when archive evidence is below the Track B "
    "threshold. It is not archive evidence, not automatically correct, not an "
    "approved change, and not permission to edit the Bible."
)
TRACK_C_CANDIDATE_NOTE = (
    "Absence of archive evidence is not negative evidence; the owner reason "
    "alone makes this verse review eligible."
)

# Published artifact set (order is the deterministic publication order).
ARTIFACT_FILES = (TRACK_A_STREAM, TRACK_B_STREAM, OWNER_OVERLAY_STREAM,
                  REVIEW_UNIVERSE_STREAM, MANIFEST_NAME)
ARTIFACT_STREAM_TRACKS = {TRACK_A_STREAM: TRACK_A, TRACK_B_STREAM: TRACK_B,
                          OWNER_OVERLAY_STREAM: TRACK_C}
ARTIFACT_INDEX_STREAMS = (REVIEW_UNIVERSE_STREAM,)
STAGING_PREFIX = ".gd_review_packets_staging_"

# Expected counts of the verified workload audit. Any drift fails a pinned run.
EXPECTED_COUNTS = {
    "findings": 58498,
    "unique_finding_uids": 58498,
    "finding_uid_collisions": 0,
    "findings_with_verse_mapping": 38802,
    "verse_evidence_rows": 67109,
    "unique_canonical_verses": 12646,
    "anomaly_rows": 4061,
    "transformation_rules": 33,
    "transformation_applications": 383,
    "manifest_reference_entries": 364,
    "unique_changed_verses": 335,
    "track_a_packets": 335,
    "track_a_with_direct_archive_evidence": 215,
    "track_a_without_direct_archive_evidence": 120,
    "track_a_evidence_rows": 2385,
    "track_a_unique_evidence_findings": 2121,
    "track_b_packets": 316,
    "track_b_min_revision_relevant_findings": 20,
    "track_b_packets_with_unmanifested_text_difference": 0,
    "combined_packets": 651,
    # Owner-specified Track C inputs (owner-declared, not measured overlaps).
    "owner_verse_candidates": 10,
    "owner_note_occurrences": 12,
    "duplicate_owner_note_occurrences": 1,
    "unresolved_owner_references": 0,
    "style_policies": 3,
    "style_policies_applied": 0,
    "style_policies_approved": 0,
    # Track C overlap with A/B and the review universe are MEASURED from the
    # frozen data (335 A + 316 B + 10 owner) and only then pinned as invariants.
    "track_c_overlap_with_track_a": 0,
    "track_c_overlap_with_track_b": 4,
    "owner_only_owner_verses": 6,
    "owner_candidates_with_direct_archive_evidence": 10,
    "owner_candidates_without_direct_archive_evidence": 0,
    "review_universe_total_unique_verses": 657,
}

VERSE_KEY_RE = re.compile(r"^b(?P<book>\d+):c(?P<chapter>\d+):v(?P<verse>\d+)$")


class PacketInputError(RuntimeError):
    """Raised when a frozen production input does not match its pin."""


class PacketBuildError(RuntimeError):
    """Raised when the packet build cannot proceed deterministically."""


class CoordinateError(PacketBuildError):
    """Raised when a Bible coordinate cannot be resolved fail-closed."""


# --------------------------------------------------------------------------
# Small deterministic helpers
# --------------------------------------------------------------------------


def dumps(obj):
    """Documented compact JSON serialization for packets and manifests."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def sha256_file(path):
    return MAPPING.sha256_file(path)


def sha256_text(text):
    return MAPPING.sha256_text(text)


def count_jsonl_rows(path):
    """Count non-empty JSONL rows in a small stream."""
    rows = 0
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows += 1
    return {"rows": rows}


def parse_verse_key(verse_key):
    """Return ``(book_id, chapter, verse)``; fail closed on a malformed key."""
    match = VERSE_KEY_RE.match(verse_key or "")
    if not match:
        raise PacketBuildError(
            "malformed verse key: {!r}".format(verse_key))
    return (int(match.group("book")), int(match.group("chapter")),
            int(match.group("verse")))


def verse_order_key(verse_key):
    """Numeric canonical ordering key (lexicographic order is wrong for keys)."""
    return parse_verse_key(verse_key)


def canonical_reference(book, chapter, verse):
    return "{} {}:{}".format(book, chapter, verse)


def resolve_input_paths(evidence_bridge_dir=None, standard_kjv_asset=None,
                        current_gd_asset=None, transformation_manifest=None,
                        owner_inputs=None):
    bridge_dir = evidence_bridge_dir or DEFAULT_EVIDENCE_BRIDGE_DIR
    paths = {
        "evidence_bridge_dir": bridge_dir,
        "standard_kjv_asset": standard_kjv_asset or DEFAULT_STANDARD_KJV_ASSET,
        "current_gd_asset": current_gd_asset or DEFAULT_CURRENT_GD_ASSET,
        "transformation_manifest": (
            transformation_manifest or DEFAULT_TRANSFORMATION_MANIFEST),
        "owner_inputs": owner_inputs or OWNER_INPUTS_PATH,
    }
    for role, (filename, _sha, _count) in EVIDENCE_BRIDGE_FILES.items():
        paths[role] = os.path.join(bridge_dir, filename)
    return paths


# --------------------------------------------------------------------------
# Coordinate table + Bible text join
# --------------------------------------------------------------------------


def load_coordinate_books(path=None):
    """Return the pinned ``books`` list from ``gd_canonical_coordinates.json``.

    Uses the committed GD coordinate machinery (the same loader the mapping
    layer uses). Fails closed when the artifact is missing or malformed.
    """
    artifact = ENGINE._load_coordinates_artifact(
        path or MAPPING.COORDINATES_PATH)
    if not artifact:
        raise PacketBuildError(
            "canonical coordinate artifact unavailable: {}".format(
                path or MAPPING.COORDINATES_PATH))
    books = artifact.get("books")
    if not isinstance(books, list) or not books:
        raise PacketBuildError("canonical coordinate artifact has no books")
    seen_ids = set()
    for expected_id, entry in enumerate(books, start=1):
        if not isinstance(entry, dict):
            raise PacketBuildError("coordinate book entry is not an object")
        book_id = entry.get("book_id")
        counts = entry.get("chapter_verse_counts")
        if book_id != expected_id:
            raise PacketBuildError(
                "coordinate book_id {} is not positional {}".format(
                    book_id, expected_id))
        if book_id in seen_ids:
            raise PacketBuildError("duplicate coordinate book_id {}".format(book_id))
        seen_ids.add(book_id)
        if not isinstance(entry.get("book"), str) or not entry["book"]:
            raise PacketBuildError("coordinate book name missing")
        if not isinstance(counts, list) or not counts:
            raise PacketBuildError(
                "coordinate chapter_verse_counts missing for {}".format(
                    entry.get("book")))
        for count in counts:
            if isinstance(count, bool) or not isinstance(count, int) or count < 1:
                raise PacketBuildError(
                    "invalid chapter verse count for {}".format(entry.get("book")))
    return books


def coordinate_counts(books):
    return {
        "book_count": len(books),
        "chapter_count": sum(len(b["chapter_verse_counts"]) for b in books),
        "verse_count": sum(sum(b["chapter_verse_counts"]) for b in books),
    }


def load_bible_asset(path):
    """Load a Bible asset as ``[{name, abbrev, chapters: [[verse, ...]]}]``."""
    try:
        with open(path, encoding="utf-8") as handle:
            asset = json.load(handle)
    except (OSError, ValueError) as exc:
        raise PacketBuildError(
            "Bible asset unreadable: {} ({})".format(path, exc))
    validate_bible_asset(asset, path)
    return asset


def validate_bible_asset(asset, label="<asset>"):
    if not isinstance(asset, list) or not asset:
        raise PacketBuildError("{}: Bible asset must be a non-empty list".format(label))
    for index, book in enumerate(asset):
        if not isinstance(book, dict):
            raise PacketBuildError("{}: book {} is not an object".format(label, index))
        if not isinstance(book.get("name"), str) or not book["name"]:
            raise PacketBuildError("{}: book {} has no name".format(label, index))
        chapters = book.get("chapters")
        if not isinstance(chapters, list) or not chapters:
            raise PacketBuildError(
                "{}: {} has no chapters".format(label, book["name"]))
        for chapter_index, verses in enumerate(chapters):
            if not isinstance(verses, list) or not verses:
                raise PacketBuildError(
                    "{}: {} chapter {} is empty".format(
                        label, book["name"], chapter_index + 1))
            for verse_index, text in enumerate(verses):
                if not isinstance(text, str):
                    raise PacketBuildError(
                        "{}: {} {}:{} is not text".format(
                            label, book["name"], chapter_index + 1,
                            verse_index + 1))
    return True


def assert_assets_and_coordinates_agree(standard_asset, current_asset, books):
    """Fail closed when the two assets or the coordinate table disagree.

    Checks book count, per-book name, per-book chapter count and per-chapter
    verse count. This is the ``the two Bible assets must share the required
    coordinate`` guarantee, established before any packet lookup.
    """
    problems = []
    if len(standard_asset) != len(current_asset):
        problems.append("book_count_standard_{}_current_{}".format(
            len(standard_asset), len(current_asset)))
    if len(books) != len(standard_asset):
        problems.append("book_count_coordinates_{}_standard_{}".format(
            len(books), len(standard_asset)))
    limit = min(len(standard_asset), len(current_asset), len(books))
    for index in range(limit):
        std_book = standard_asset[index]
        cur_book = current_asset[index]
        coord_book = books[index]
        if std_book.get("name") != cur_book.get("name"):
            problems.append("book_name_mismatch_at_{}".format(index + 1))
            continue
        if std_book.get("name") != coord_book.get("book"):
            problems.append("coordinate_book_name_mismatch_{}".format(
                std_book.get("name")))
            continue
        std_chapters = std_book["chapters"]
        cur_chapters = cur_book["chapters"]
        expected = coord_book["chapter_verse_counts"]
        if len(std_chapters) != len(cur_chapters):
            problems.append("chapter_count_mismatch_{}".format(std_book["name"]))
            continue
        if len(std_chapters) != len(expected):
            problems.append("coordinate_chapter_count_mismatch_{}".format(
                std_book["name"]))
            continue
        for chapter_index, expected_verses in enumerate(expected):
            if len(std_chapters[chapter_index]) != len(cur_chapters[chapter_index]):
                problems.append("chapter_verse_count_mismatch_{}_{}".format(
                    std_book["name"], chapter_index + 1))
            elif len(std_chapters[chapter_index]) != expected_verses:
                problems.append("coordinate_chapter_verse_count_mismatch_{}_{}".format(
                    std_book["name"], chapter_index + 1))
    if problems:
        raise CoordinateError(
            "Bible assets/coordinates disagree: " + "; ".join(problems[:10]))
    return True


class BibleTextIndex:
    """Fail-closed verbatim join of standard + current Bible text by coordinate."""

    def __init__(self, standard_asset, current_asset, books):
        validate_bible_asset(standard_asset, "standard_kjv_asset")
        validate_bible_asset(current_asset, "current_gd_asset")
        assert_assets_and_coordinates_agree(standard_asset, current_asset, books)
        self.standard_asset = standard_asset
        self.current_asset = current_asset
        self.books = books
        self._by_id = {entry["book_id"]: entry for entry in books}

    def book_entry(self, book_id):
        if isinstance(book_id, bool) or not isinstance(book_id, int):
            raise CoordinateError("book_id is not an integer: {!r}".format(book_id))
        if not BOOK_ID_MIN <= book_id <= BOOK_ID_MAX:
            raise CoordinateError(
                "book_id {} outside {}..{}".format(
                    book_id, BOOK_ID_MIN, BOOK_ID_MAX))
        entry = self._by_id.get(book_id)
        if entry is None:
            raise CoordinateError(
                "book_id {} absent from the canonical coordinate table".format(
                    book_id))
        return entry

    def book_name(self, book_id):
        return self.book_entry(book_id)["book"]

    def verse_counts(self, book_id):
        return self.book_entry(book_id)["chapter_verse_counts"]

    def lookup(self, book_id, chapter, verse, verse_key=None):
        """Return ``(standard_text, current_text)`` verbatim, or raise."""
        entry = self.book_entry(book_id)
        label = verse_key or canonical_reference(entry["book"], chapter, verse)
        counts = entry["chapter_verse_counts"]
        if isinstance(chapter, bool) or not isinstance(chapter, int):
            raise CoordinateError("{}: chapter is not an integer".format(label))
        if isinstance(verse, bool) or not isinstance(verse, int):
            raise CoordinateError("{}: verse is not an integer".format(label))
        if not 1 <= chapter <= len(counts):
            raise CoordinateError(
                "{}: chapter {} outside 1..{}".format(
                    label, chapter, len(counts)))
        if not 1 <= verse <= counts[chapter - 1]:
            raise CoordinateError(
                "{}: verse {} outside 1..{}".format(
                    label, verse, counts[chapter - 1]))
        if book_id > len(self.standard_asset) or book_id > len(self.current_asset):
            raise CoordinateError("{}: book absent from Bible asset".format(label))
        try:
            standard_text = self.standard_asset[book_id - 1]["chapters"][chapter - 1][verse - 1]
            current_text = self.current_asset[book_id - 1]["chapters"][chapter - 1][verse - 1]
        except (IndexError, KeyError, TypeError) as exc:
            raise CoordinateError(
                "{}: coordinate missing in Bible asset ({})".format(label, exc))
        if not isinstance(standard_text, str) or not isinstance(current_text, str):
            raise CoordinateError(
                "{}: Bible text is not a string in both assets".format(label))
        if self.standard_asset[book_id - 1]["name"] != entry["book"]:
            raise CoordinateError(
                "{}: standard asset book name mismatch".format(label))
        if self.current_asset[book_id - 1]["name"] != entry["book"]:
            raise CoordinateError(
                "{}: current asset book name mismatch".format(label))
        return standard_text, current_text

    def lookup_verse_key(self, verse_key):
        book_id, chapter, verse = parse_verse_key(verse_key)
        return self.lookup(book_id, chapter, verse, verse_key=verse_key)


# --------------------------------------------------------------------------
# Transformation manifest join
# --------------------------------------------------------------------------

RULE_OPTIONAL_FIELDS = (
    "standardToken",
    "standardPhrase",
    "customToken",
    "customPhrase",
    "contextCondition",
)


def load_transformation_manifest(path):
    try:
        with open(path, encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, ValueError) as exc:
        raise PacketBuildError(
            "transformation manifest unreadable: {} ({})".format(path, exc))
    if not isinstance(manifest, dict):
        raise PacketBuildError("transformation manifest must be an object")
    rules = manifest.get("rules")
    if not isinstance(rules, list) or not rules:
        raise PacketBuildError("transformation manifest has no rules")
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise PacketBuildError("manifest rule {} is not an object".format(index))
        if not isinstance(rule.get("ruleId"), str) or not rule["ruleId"]:
            raise PacketBuildError("manifest rule {} has no ruleId".format(index))
        if not isinstance(rule.get("references"), list):
            raise PacketBuildError(
                "manifest rule {} has no references list".format(rule["ruleId"]))
    return manifest


def parse_transformation_manifest(manifest, table=None, coordinates=None):
    """Resolve every manifest reference to exactly one canonical verse key.

    Reuses the committed GD mapping parser (``classify_raw_reference`` ->
    ``expand_verse_keys``). Fail closed when a reference does not resolve to
    exactly one verse, when a rule is malformed, or when ``applicationCount``
    disagrees with the number of reference entries.

    Returns ``(summary, verse_rules)`` where ``verse_rules`` maps a verse key to
    the list of applicable rule entries in manifest order.
    """
    rules_out = []
    verse_rules = {}
    reference_entries = 0
    applications = 0
    problems = []

    for rule in manifest["rules"]:
        rule_id = rule["ruleId"]
        references = rule["references"]
        application_count = rule.get("applicationCount")
        if isinstance(application_count, bool) or not isinstance(application_count, int):
            problems.append("{}: applicationCount is not an integer".format(rule_id))
            application_count = 0
        if application_count < 1:
            problems.append("{}: applicationCount is not positive".format(rule_id))
        # ``applicationCount`` is the number of applied transformations, NOT the
        # number of reference entries: a rule may be applied more than once per
        # referenced verse (R024/R025/R026) and a rule may also repeat a
        # reference entry verbatim (R001/R011). Both facts are preserved and
        # neither may be collapsed into the other.
        distinct_references = len(set(references))
        if application_count < distinct_references:
            problems.append(
                "{}: applicationCount {} < {} distinct reference entries".format(
                    rule_id, application_count, distinct_references))
        reference_entries += len(references)
        applications += application_count

        normalized = {
            "ruleId": rule_id,
            "description": rule.get("description", ""),
            "caseSensitive": bool(rule.get("caseSensitive", False)),
            "tokenCountBefore": rule.get("tokenCountBefore"),
            "tokenCountAfter": rule.get("tokenCountAfter"),
            "applicationCount": application_count,
            "rule_reference_entry_count": len(references),
            "duplicate_reference_entry_count": len(references) - len(set(references)),
        }
        for field in RULE_OPTIONAL_FIELDS:
            if field in rule:
                normalized[field] = rule[field]

        per_verse_strings = {}
        for raw_index, raw in enumerate(references):
            core = MAPPING.classify_raw_reference(raw, table=table)
            verse_keys = core.get("verse_keys") or []
            if core.get("status") not in MAPPING.VERSE_MAPPED_STATUSES:
                problems.append(
                    "{}[{}]: {!r} classified {} (not a verse mapping)".format(
                        rule_id, raw_index, raw, core.get("status")))
                continue
            if len(verse_keys) != 1:
                problems.append(
                    "{}[{}]: {!r} resolved to {} verses".format(
                        rule_id, raw_index, raw, len(verse_keys)))
                continue
            verse_key = verse_keys[0]
            per_verse_strings.setdefault(verse_key, []).append(raw)

        normalized["unique_verse_count"] = len(per_verse_strings)
        rules_out.append(normalized)

        for verse_key, strings in per_verse_strings.items():
            entry = dict(normalized)
            # Original manifest reference strings that resolved to THIS verse,
            # duplicates preserved (some rules contain duplicate entries).
            entry["manifest_reference_strings"] = list(strings)
            verse_rules.setdefault(verse_key, []).append(entry)

    if problems:
        raise PacketBuildError(
            "transformation manifest references did not resolve cleanly "
            "({} problem(s)): {}".format(len(problems), "; ".join(problems[:10])))

    summary = {
        "transformation_rules": len(manifest["rules"]),
        "transformation_applications": applications,
        "manifest_reference_entries": reference_entries,
        "unique_changed_verses": len(verse_rules),
        "rules": rules_out,
    }
    return summary, verse_rules


# --------------------------------------------------------------------------
# Evidence bridge loading
# --------------------------------------------------------------------------


def load_verse_evidence_index(path):
    """Load the authoritative (verse_key, finding_uid) association.

    Returns a dict with per-verse association metadata. Duplicate
    ``finding_uid`` entries per verse are deduplicated defensively, but the raw
    reference strings of every occurrence are preserved.
    """
    by_verse = {}
    rows = 0
    unique_findings = set()
    pairs = set()
    duplicates = 0
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            rows += 1
            verse_key = row.get("verse_key")
            finding_uid = row.get("finding_uid")
            if not verse_key or not finding_uid:
                raise PacketBuildError(
                    "verse_evidence_index row {} lacks verse_key/finding_uid".format(rows))
            parse_verse_key(verse_key)
            key = (verse_key, finding_uid)
            if key in pairs:
                duplicates += 1
            pairs.add(key)
            unique_findings.add(finding_uid)
            bucket = by_verse.setdefault(verse_key, {})
            existing = bucket.get(finding_uid)
            if existing is None:
                bucket[finding_uid] = {
                    "finding_topic": row.get("finding_topic"),
                    "research_generation": row.get("research_generation"),
                    "final_pass": row.get("final_pass"),
                    "chunk_id": row.get("chunk_id"),
                    "source_document_sha256": row.get("source_document_sha256"),
                    "book": row.get("book"),
                    "book_id": row.get("book_id"),
                    "chapter": row.get("chapter"),
                    "verse": row.get("verse"),
                    "canonical": row.get("canonical"),
                    "raw_refs": list(row.get("raw_refs") or []),
                }
            else:
                for raw in row.get("raw_refs") or []:
                    if raw not in existing["raw_refs"]:
                        existing["raw_refs"].append(raw)
    return {
        "by_verse": by_verse,
        "rows": rows,
        "unique_verses": len(by_verse),
        "unique_findings": len(unique_findings),
        "pairs": len(pairs),
        "duplicate_pairs": duplicates,
        "finding_uids": unique_findings,
    }


def load_finding_records(path, needed_uids):
    """Stream ``finding_reference_map.jsonl``; return records for needed uids.

    Also independently verifies total row count, unique finding_uid count and
    duplicate finding_uid rows.
    """
    needed = set(needed_uids)
    records = {}
    rows = 0
    seen = set()
    collisions = 0
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            rows += 1
            uid = row.get("finding_uid")
            if not uid:
                raise PacketBuildError(
                    "finding_reference_map row {} lacks finding_uid".format(rows))
            if uid in seen:
                # A repeated finding_uid row is an identity collision: the
                # bridge promises exactly one row per finding_uid.
                collisions += 1
            seen.add(uid)
            if uid in needed and uid not in records:
                records[uid] = row
    return {
        "records": records,
        "rows": rows,
        "unique_finding_uids": len(seen),
        "finding_uid_collisions": collisions,
        "missing_needed_uids": sorted(needed - set(records)),
    }


# --------------------------------------------------------------------------
# Selection
# --------------------------------------------------------------------------


def select_track_a(changed_verse_keys):
    """Track A: every currently changed verse, canonical order."""
    return sorted(set(changed_verse_keys), key=verse_order_key)


def select_track_b(verse_evidence_index, changed_verse_keys,
                   threshold=TRACK_B_MIN_REVISION_RELEVANT_FINDINGS):
    """Track B: not-currently-changed verses with >= threshold relevant findings."""
    changed = set(changed_verse_keys)
    selected = []
    for verse_key, bucket in verse_evidence_index["by_verse"].items():
        if verse_key in changed:
            continue
        relevant = 0
        for association in bucket.values():
            if association.get("finding_topic") in REVISION_RELEVANT_TOPIC_SET:
                relevant += 1
        if relevant >= threshold:
            selected.append(verse_key)
    return sorted(selected, key=verse_order_key)


def revision_relevant_count(bucket):
    return sum(
        1 for association in bucket.values()
        if association.get("finding_topic") in REVISION_RELEVANT_TOPIC_SET
    )


def revision_relevant_uids(bucket):
    return sorted(
        uid for uid, association in bucket.items()
        if association.get("finding_topic") in REVISION_RELEVANT_TOPIC_SET
    )


# --------------------------------------------------------------------------
# Packet construction
# --------------------------------------------------------------------------


def _evidence_sort_key(item):
    return (
        item.get("source_document_sha256") or "",
        item.get("chunk_id") or "",
        item.get("final_pass") or "",
        item.get("finding_char_start")
        if isinstance(item.get("finding_char_start"), int) else -1,
        item.get("finding_index")
        if isinstance(item.get("finding_index"), int) else -1,
        item.get("finding_uid") or "",
    )


def build_evidence_item(finding_uid, record, association, problems):
    """Build one traceable evidence item for one (verse, finding) association."""
    identity = record.get("identity") or {}
    finding = record.get("finding") or {}
    passage = record.get("passage") or {}

    if identity.get("finding_topic") != association.get("finding_topic"):
        problems.append("topic_mismatch:{}".format(finding_uid))
    if identity.get("final_pass") != association.get("final_pass"):
        problems.append("final_pass_mismatch:{}".format(finding_uid))
    if identity.get("research_generation") != association.get("research_generation"):
        problems.append("generation_mismatch:{}".format(finding_uid))
    if identity.get("chunk_id") != association.get("chunk_id"):
        problems.append("chunk_mismatch:{}".format(finding_uid))
    if identity.get("source_document_sha256") != association.get("source_document_sha256"):
        problems.append("document_sha_mismatch:{}".format(finding_uid))

    source_document = passage.get("source_document") or identity.get("source_document")

    return {
        "finding_uid": finding_uid,
        "finding_index": finding.get("finding_index"),
        "finding_topic": finding.get("topic"),
        "finding_quote": finding.get("quote"),
        "finding_note": finding.get("note"),
        "finding_confidence": finding.get("confidence"),
        "finding_provenance": finding.get("provenance"),
        "finding_speaker": finding.get("speaker"),
        "finding_occurrences": finding.get("occurrences"),
        "finding_char_start": finding.get("char_start"),
        "finding_char_end": finding.get("char_end"),
        "source_document": source_document,
        "source_document_sha256": identity.get("source_document_sha256"),
        "source_collection": passage.get("source_collection"),
        "current_path": passage.get("current_path"),
        "chunk_id": identity.get("chunk_id"),
        "research_generation": identity.get("research_generation"),
        "final_pass": identity.get("final_pass"),
        "final_pass_key": identity.get("final_pass_key"),
        "finding_quote_sha256": identity.get("finding_quote_sha256"),
        "raw_scripture_refs": list(record.get("raw_scripture_refs") or []),
        "verse_raw_refs": list(association.get("raw_refs") or []),
        "mapped_verse_keys": list(record.get("mapped_verse_keys") or []),
        "provenance": {
            "association": "verse_evidence_index:verse_key+finding_uid",
            "bridge_schema_version": record.get("schema_version",
                                                SOURCE_MAPPING_SCHEMA_VERSION),
            "mapper_version": record.get("mapper_version"),
            "engine_version": record.get("engine_version"),
            "identity_version": identity.get("identity_version"),
            "evidence_class": "model_attributed_archive_evidence",
            "reference_origin": "archive_research_finding_scripture_refs",
        },
    }


def build_packet(track, verse_key, text_index, current_transformation_rules,
                 bucket, records, problems):
    """Build one deterministic per-verse packet."""
    book_id, chapter, verse = parse_verse_key(verse_key)
    book = text_index.book_name(book_id)
    standard_text, current_text = text_index.lookup(
        book_id, chapter, verse, verse_key=verse_key)
    text_differs = standard_text != current_text

    associations = bucket or {}
    evidence = []
    for finding_uid in sorted(associations):
        record = records.get(finding_uid)
        if record is None:
            problems.append("missing_finding_record:{}".format(finding_uid))
            continue
        if verse_key not in set(record.get("mapped_verse_keys") or []):
            problems.append("record_lacks_verse:{}:{}".format(finding_uid, verse_key))
            continue
        evidence.append(build_evidence_item(
            finding_uid, record, associations[finding_uid], problems))
    evidence.sort(key=_evidence_sort_key)

    topics = {}
    generations = {}
    passes = {}
    documents = set()
    for item in evidence:
        topics[item["finding_topic"]] = topics.get(item["finding_topic"], 0) + 1
        generations[item["research_generation"]] = (
            generations.get(item["research_generation"], 0) + 1)
        passes[item["final_pass"]] = passes.get(item["final_pass"], 0) + 1
        documents.add(item["source_document_sha256"])

    relevant = sum(
        1 for item in evidence
        if item["finding_topic"] in REVISION_RELEVANT_TOPIC_SET)

    direct_evidence = bool(evidence)
    if track == TRACK_A:
        rule_ids = [rule["ruleId"] for rule in current_transformation_rules]
        selection_basis = {
            "track": TRACK_A,
            "track_name": TRACK_A_NAME,
            "rule": "existing_gd_transformation_review",
            "statement": TRACK_A_STATEMENT,
            "currently_changed": True,
            "direct_archive_verse_evidence": direct_evidence,
            "revision_relevant_topics": list(REVISION_RELEVANT_TOPICS),
            "revision_relevant_finding_count": relevant,
            "revision_relevant_threshold": None,
            "applicable_rule_ids": rule_ids,
        }
        if not direct_evidence:
            selection_basis["archive_evidence_note"] = TRACK_A_NO_EVIDENCE_NOTE
        else:
            selection_basis["archive_evidence_note"] = (
                "Mapped archive verse evidence exists for this changed verse.")
    elif track == TRACK_B:
        selection_basis = {
            "track": TRACK_B,
            "track_name": TRACK_B_NAME,
            "rule": "new_change_discovery_tier_1_ge_{}_revision_relevant_findings".format(
                TRACK_B_MIN_REVISION_RELEVANT_FINDINGS),
            "statement": TRACK_B_STATEMENT,
            "currently_changed": False,
            "direct_archive_verse_evidence": direct_evidence,
            "revision_relevant_topics": list(REVISION_RELEVANT_TOPICS),
            "revision_relevant_finding_count": relevant,
            "revision_relevant_threshold": TRACK_B_MIN_REVISION_RELEVANT_FINDINGS,
            "unmanifested_text_difference": text_differs,
            "candidate_note": TRACK_B_CANDIDATE_NOTE,
        }
    elif track == TRACK_C:
        selection_basis = {
            "track": TRACK_C,
            "track_name": TRACK_C_NAME,
            "rule": "owner_specified_review_candidate",
            "statement": TRACK_C_STATEMENT,
            "currently_changed": bool(current_transformation_rules),
            "direct_archive_verse_evidence": direct_evidence,
            "revision_relevant_topics": list(REVISION_RELEVANT_TOPICS),
            "revision_relevant_finding_count": relevant,
            "revision_relevant_threshold": None,
            "archive_evidence_threshold_required": False,
            "owner_specified": True,
            "owner_evidence_is_archive_evidence": False,
            "absence_of_archive_evidence_is_negative_evidence": False,
            "candidate_note": TRACK_C_CANDIDATE_NOTE,
        }
    else:
        raise PacketBuildError("unknown packet track {!r}".format(track))

    return {
        "schema_version": PACKET_SCHEMA_VERSION,
        "packet_builder_version": PACKET_BUILDER_VERSION,
        "track": track,
        "track_name": {TRACK_A: TRACK_A_NAME, TRACK_B: TRACK_B_NAME,
                       TRACK_C: TRACK_C_NAME}[track],
        "priority_tier": {TRACK_A: PRIORITY_TIER_A, TRACK_B: PRIORITY_TIER_B,
                          TRACK_C: PRIORITY_TIER_C}[track],
        "verse_key": verse_key,
        "canonical_reference": canonical_reference(book, chapter, verse),
        "book_id": book_id,
        "book": book,
        "chapter": chapter,
        "verse": verse,
        "standard_kjv_text": standard_text,
        "current_gd_text": current_text,
        "text_differs": text_differs,
        "currently_changed": (track == TRACK_A) or bool(current_transformation_rules),
        "direct_archive_verse_evidence": direct_evidence,
        "current_transformation_rules": current_transformation_rules,
        "evidence_summary": {
            "total_unique_findings": len(evidence),
            "total_unique_source_documents": len(documents),
            "total_evidence_rows": len(evidence),
            "revision_relevant_finding_count": relevant,
            "revision_relevant_topics": list(REVISION_RELEVANT_TOPICS),
            "counts_by_topic": {key: topics[key] for key in sorted(topics)},
            "counts_by_generation": {
                key: generations[key] for key in sorted(generations)},
            "counts_by_final_pass": {key: passes[key] for key in sorted(passes)},
        },
        "evidence": evidence,
        "selection_basis": selection_basis,
    }


def build_all_packets(text_index, verse_rules, verse_evidence_index,
                      records, track_a_keys, track_b_keys):
    """Build both streams. Returns ``(track_a, track_b, problems)``."""
    by_verse = verse_evidence_index["by_verse"]
    problems = []
    track_a = [
        build_packet(TRACK_A, verse_key, text_index,
                     verse_rules.get(verse_key, []),
                     by_verse.get(verse_key, {}), records, problems)
        for verse_key in track_a_keys
    ]
    track_b = [
        build_packet(TRACK_B, verse_key, text_index, [],
                     by_verse.get(verse_key, {}), records, problems)
        for verse_key in track_b_keys
    ]
    return track_a, track_b, problems


def serialize_stream(packets):
    """Serialize a packet list to compact JSONL text (deterministic)."""
    if not packets:
        return ""
    return "\n".join(dumps(packet) for packet in packets) + "\n"


# --------------------------------------------------------------------------
# Audit
# --------------------------------------------------------------------------


def _percentile(sorted_values, fraction):
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = fraction * (len(sorted_values) - 1)
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] + weight * (sorted_values[upper] - sorted_values[lower])


def _median(sorted_values):
    return _percentile(sorted_values, 0.5)


def _check(checks, name, expected, observed):
    ok = expected == observed
    checks.append({"name": name, "expected": expected, "observed": observed,
                   "ok": ok})
    return ok


def _owner_direct_evidence(record):
    """Whether the authoritative packet for an owner verse has archive evidence."""
    if record.get("owner_only"):
        return bool(record.get("direct_archive_verse_evidence"))
    return bool(record.get("existing_packet_direct_archive_evidence"))


def build_audit(packets_a, packets_b, measured, manifest_summary,
                verse_evidence_index, finding_load, text_index=None,
                pinned=True, owner_candidates=None, owner_overlay=None,
                review_universe=None, owner_summary=None, style_policies=None):
    """Full deterministic audit of both streams against the verified workload."""
    checks = []
    owner_candidates = owner_candidates or []
    owner_overlay = owner_overlay or []
    review_universe = review_universe or []
    owner_summary = owner_summary or {}
    style_policies = style_policies or []

    # ---- stream serialization (exact in-memory size) -------------------
    text_a = serialize_stream(packets_a)
    text_b = serialize_stream(packets_b)
    bytes_a = len(text_a.encode("utf-8"))
    bytes_b = len(text_b.encode("utf-8"))

    # ---- Track A -------------------------------------------------------
    a_total = len(packets_a)
    a_with = sum(1 for p in packets_a if p["direct_archive_verse_evidence"])
    a_without = a_total - a_with
    a_evidence_rows = sum(len(p["evidence"]) for p in packets_a)
    a_unique_findings = len({item["finding_uid"]
                             for p in packets_a for item in p["evidence"]})
    a_keys = [p["verse_key"] for p in packets_a]
    _check(checks, "track_a_packets", EXPECTED_COUNTS["track_a_packets"], a_total)
    _check(checks, "track_a_packets_with_direct_archive_evidence",
           EXPECTED_COUNTS["track_a_with_direct_archive_evidence"], a_with)
    _check(checks, "track_a_packets_without_direct_archive_evidence",
           EXPECTED_COUNTS["track_a_without_direct_archive_evidence"], a_without)
    _check(checks, "track_a_evidence_rows",
           EXPECTED_COUNTS["track_a_evidence_rows"], a_evidence_rows)
    _check(checks, "track_a_unique_evidence_findings",
           EXPECTED_COUNTS["track_a_unique_evidence_findings"], a_unique_findings)
    _check(checks, "track_a_unique_verse_keys", a_total, len(set(a_keys)))
    _check(checks, "track_a_all_currently_changed", a_total,
           sum(1 for p in packets_a if p["currently_changed"]))
    _check(checks, "track_a_all_text_differs", a_total,
           sum(1 for p in packets_a if p["text_differs"]))
    _check(checks, "track_a_no_evidence_packets_have_empty_evidence", a_without,
           sum(1 for p in packets_a
               if not p["direct_archive_verse_evidence"]
               and not p["evidence"]))
    _check(checks, "track_a_no_evidence_packets_have_zero_counts", a_without,
           sum(1 for p in packets_a
               if not p["direct_archive_verse_evidence"]
               and p["evidence_summary"]["total_unique_findings"] == 0
               and p["evidence_summary"]["total_unique_source_documents"] == 0))
    _check(checks, "track_a_no_evidence_selection_basis_says_existing_transformation",
           a_without,
           sum(1 for p in packets_a
               if not p["direct_archive_verse_evidence"]
               and p["selection_basis"]["rule"] == "existing_gd_transformation_review"))

    # ---- Track B -------------------------------------------------------
    b_total = len(packets_b)
    b_keys = [p["verse_key"] for p in packets_b]
    _check(checks, "track_b_packets", EXPECTED_COUNTS["track_b_packets"], b_total)
    _check(checks, "track_b_unique_verse_keys", b_total, len(set(b_keys)))
    _check(checks, "track_b_overlap_with_track_a", 0, len(set(a_keys) & set(b_keys)))
    _check(checks, "track_b_all_not_currently_changed", b_total,
           sum(1 for p in packets_b if not p["currently_changed"]))
    _check(checks, "track_b_all_current_transformation_rules_empty", b_total,
           sum(1 for p in packets_b if p["current_transformation_rules"] == []))
    relevant_counts = sorted(
        p["evidence_summary"]["revision_relevant_finding_count"] for p in packets_b)
    _check(checks, "track_b_revision_relevant_at_or_above_threshold", b_total,
           sum(1 for value in relevant_counts
               if value >= TRACK_B_MIN_REVISION_RELEVANT_FINDINGS))
    _check(checks, "track_b_selection_basis_records_threshold", b_total,
           sum(1 for p in packets_b
               if p["selection_basis"]["revision_relevant_threshold"]
               == TRACK_B_MIN_REVISION_RELEVANT_FINDINGS))
    _check(checks, "track_b_revision_relevant_count_matches_selection_basis", b_total,
           sum(1 for p in packets_b
               if p["selection_basis"]["revision_relevant_finding_count"]
               == p["evidence_summary"]["revision_relevant_finding_count"]))
    # A Track B verse is defined as NOT currently changed (absent from the
    # transformation manifest). Standard/current text must therefore agree; a
    # difference is an integrity discrepancy, not a normal new-change
    # candidate, and fails a pinned build.
    b_unmanifested_text_diff = sum(
        1 for p in packets_b
        if (not p["currently_changed"]) and p["text_differs"])
    _check(checks, "track_b_packets_with_unmanifested_text_difference",
           EXPECTED_COUNTS["track_b_packets_with_unmanifested_text_difference"],
           b_unmanifested_text_diff)
    b_evidence_rows = sum(len(p["evidence"]) for p in packets_b)
    b_unique_findings = len({item["finding_uid"]
                             for p in packets_b for item in p["evidence"]})
    b_source_document_associations = sum(
        p["evidence_summary"]["total_unique_source_documents"] for p in packets_b)

    # ---- Track C: owner-specified review candidates ---------------------
    c_keys = [r["verse_key"] for r in owner_overlay]
    c_pointer = [r for r in owner_overlay if not r["owner_only"]]
    c_standalone = [r for r in owner_overlay if r["owner_only"]]
    c_overlap_a = sorted(set(c_keys) & set(a_keys), key=verse_order_key)
    c_overlap_b = sorted(set(c_keys) & set(b_keys), key=verse_order_key)
    c_raw_occurrences = sum(
        c["owner_note_occurrence_count"] for c in owner_candidates)
    c_duplicate_occurrences = sum(
        c["duplicate_occurrence_count"] for c in owner_candidates)
    _check(checks, "track_c_packets",
           EXPECTED_COUNTS["owner_verse_candidates"], len(owner_overlay))
    _check(checks, "track_c_unique_verse_keys", len(owner_overlay),
           len(set(c_keys)))
    _check(checks, "track_c_raw_owner_note_occurrences",
           EXPECTED_COUNTS["owner_note_occurrences"], c_raw_occurrences)
    _check(checks, "track_c_duplicate_owner_note_occurrences",
           EXPECTED_COUNTS["duplicate_owner_note_occurrences"],
           c_duplicate_occurrences)
    _check(checks, "track_c_unresolved_owner_references",
           EXPECTED_COUNTS["unresolved_owner_references"], 0)
    _check(checks, "track_c_overlap_with_track_a",
           EXPECTED_COUNTS["track_c_overlap_with_track_a"], len(c_overlap_a))
    _check(checks, "track_c_overlap_with_track_b",
           EXPECTED_COUNTS["track_c_overlap_with_track_b"], len(c_overlap_b))
    _check(checks, "owner_only_owner_verses",
           EXPECTED_COUNTS["owner_only_owner_verses"], len(c_standalone))
    _check(checks, "track_c_pointer_records", len(c_overlap_a) + len(c_overlap_b),
           len(c_pointer))
    _check(checks, "track_c_owner_candidates_with_direct_archive_evidence",
           EXPECTED_COUNTS["owner_candidates_with_direct_archive_evidence"],
           sum(1 for r in owner_overlay if _owner_direct_evidence(r) is True))
    _check(checks, "track_c_owner_candidates_without_direct_archive_evidence",
           EXPECTED_COUNTS["owner_candidates_without_direct_archive_evidence"],
           sum(1 for r in owner_overlay if _owner_direct_evidence(r) is False))
    # Owner reason alone must be sufficient: no archive-evidence threshold.
    _check(checks, "track_c_no_archive_evidence_threshold_applied",
           len(c_standalone),
           sum(1 for r in c_standalone
               if r["selection_basis"]["revision_relevant_threshold"] is None
               and r["selection_basis"]["archive_evidence_threshold_required"]
               is False))
    # The owner block never contains, and never counts as, archive evidence.
    _check(checks, "track_c_owner_block_contains_no_archive_evidence",
           len(owner_overlay),
           sum(1 for r in owner_overlay
               if r["owner_input"]["owner_rationale_is_archive_evidence"] is False
               and "evidence" not in r["owner_input"]))
    # Overlapping verses carry a pointer, never a duplicated payload.
    _check(checks, "track_c_pointer_records_embed_no_payload", len(c_pointer),
           sum(1 for r in c_pointer
               if r["payload_embedded"] is False
               and "standard_kjv_text" not in r
               and "evidence" not in r))
    # Owner-only verses must carry enough material for a complete packet.
    _check(checks, "track_c_standalone_records_are_complete", len(c_standalone),
           sum(1 for r in c_standalone
               if r["payload_embedded"] is True
               and isinstance(r.get("standard_kjv_text"), str)
               and isinstance(r.get("current_gd_text"), str)
               and isinstance(r.get("evidence_summary"), dict)
               and isinstance(r.get("selection_basis"), dict)))
    _check(checks, "track_c_owner_candidate_status_is_review_candidate",
           len(owner_candidates),
           sum(1 for c in owner_candidates
               if c["candidate_status"] == OWNER_CANDIDATE_STATUS
               and c["accepted_translation"] is False))
    _check(checks, "track_c_owner_candidates_are_not_archive_evidence",
           len(owner_candidates),
           sum(1 for c in owner_candidates
               if c["provenance_class"] == OWNER_PROVENANCE_CLASS))
    candidate_keys = {c["verse_key"] for c in owner_candidates}
    context_keys = {k for c in owner_candidates
                    for k in c["context_only_verse_keys"]}
    _check(checks, "track_c_context_only_verses_are_not_candidates",
           len(context_keys), len(context_keys - candidate_keys))
    policy_examples = [p.get("example_reference_raw") for p in style_policies
                       if p.get("example_reference_raw")]
    policy_example_keys = {
        classify_owner_reference(example)[1] for example in policy_examples}
    _check(checks, "style_policy_examples_are_not_track_c_candidates",
           0, len(policy_example_keys & candidate_keys))

    # ---- review universe (unique A + B + C by verse_key) ---------------
    universe_keys = set(a_keys) | set(b_keys) | set(c_keys)
    identities = [row["review_identity"] for row in review_universe]
    _check(checks, "review_universe_total_unique_verses",
           EXPECTED_COUNTS["review_universe_total_unique_verses"],
           len(review_universe))
    _check(checks, "review_universe_matches_a_b_c_union",
           len(universe_keys), len(review_universe))
    _check(checks, "review_universe_duplicate_review_identities", 0,
           len(identities) - len(set(identities)))
    _check(checks, "review_universe_identity_is_the_verse_key",
           len(review_universe),
           sum(1 for row in review_universe
               if row["review_identity"] == row["verse_key"]))
    _check(checks, "review_universe_every_row_names_one_packet_stream",
           len(review_universe),
           sum(1 for row in review_universe
               if row["packet_stream"] in
               (TRACK_A_STREAM, TRACK_B_STREAM, OWNER_OVERLAY_STREAM)))
    _check(checks, "review_universe_track_flags_match_the_streams",
           len(review_universe),
           sum(1 for row in review_universe
               if row["in_track_a"] == (row["verse_key"] in set(a_keys))
               and row["in_track_b"] == (row["verse_key"] in set(b_keys))
               and row["in_track_c"] == (row["verse_key"] in set(c_keys))
               and row["owner_only"] == (row["in_track_c"]
                                         and not row["in_track_a"]
                                         and not row["in_track_b"])))
    _check(checks, "review_universe_owner_overlay_never_duplicates_a_verse",
           len(c_keys),
           sum(1 for verse_key in c_keys
               if sum(1 for row in review_universe
                      if row["verse_key"] == verse_key) == 1))

    # ---- style policies: preserved, not implemented, not verses -------
    _check(checks, "style_policies_count", EXPECTED_COUNTS["style_policies"],
           len(style_policies))
    _check(checks, "style_policies_applied", EXPECTED_COUNTS["style_policies_applied"],
           sum(1 for p in style_policies if p["applied"]))
    _check(checks, "style_policies_approved",
           EXPECTED_COUNTS["style_policies_approved"],
           sum(1 for p in style_policies if p["approved"]))
    _check(checks, "style_policies_require_contextual_classification",
           len(style_policies),
           sum(1 for p in style_policies
               if p["requires_contextual_classification"] is True
               and p["blind_replacement_forbidden"] is True))
    capitalization = [p for p in style_policies
                      if p.get("reversible_boundary_required") is True]
    _check(checks, "reverential_capitalization_policies", 1, len(capitalization))
    _check(checks, "reverential_capitalization_is_final_reversible_pass", 1,
           sum(1 for p in capitalization
               if p["stage"] == "final_reversible_style_pass"
               and p["apply_order"] == "last"))
    _check(checks, "reverential_capitalization_not_applied", 1,
           sum(1 for p in capitalization if p["applied"] is False))
    _check(checks, "style_policies_are_not_verse_packets", 0,
           len(set(p["policy_id"] for p in style_policies) & set(candidate_keys)))

    # ---- combined ------------------------------------------------------
    combined = a_total + b_total
    all_keys = a_keys + b_keys
    _check(checks, "combined_packets", EXPECTED_COUNTS["combined_packets"], combined)
    _check(checks, "combined_unique_verse_keys", combined, len(set(all_keys)))
    _check(checks, "combined_duplicate_verse_keys", 0,
           len(all_keys) - len(set(all_keys)))
    _check(checks, "combined_track_a_track_b_disjoint", True,
           not (set(a_keys) & set(b_keys)))
    _check(checks, "every_evidence_finding_uid_exists_in_finding_reference_map",
           True, not finding_load["missing_needed_uids"])
    _check(checks, "finding_reference_map_rows",
           EXPECTED_COUNTS["findings"], finding_load["rows"])
    _check(checks, "finding_reference_map_unique_finding_uids",
           EXPECTED_COUNTS["unique_finding_uids"],
           finding_load["unique_finding_uids"])
    _check(checks, "finding_uid_collisions",
           EXPECTED_COUNTS["finding_uid_collisions"],
           finding_load["finding_uid_collisions"])
    _check(checks, "verse_evidence_index_rows",
           EXPECTED_COUNTS["verse_evidence_rows"], verse_evidence_index["rows"])
    _check(checks, "verse_evidence_index_unique_verses",
           EXPECTED_COUNTS["unique_canonical_verses"],
           verse_evidence_index["unique_verses"])
    _check(checks, "evidence_association_is_subset_of_verse_evidence_index", True,
           _associations_subset_of_index(packets_a, packets_b, verse_evidence_index))
    # Independently re-resolve every packet coordinate through the same
    # fail-closed text index and confirm the stored text is verbatim correct.
    lookup_failures = 0
    lookups = 0
    if text_index is not None:
        for packet in packets_a + packets_b:
            lookups += 1
            try:
                standard_text, current_text = text_index.lookup(
                    packet["book_id"], packet["chapter"], packet["verse"],
                    verse_key=packet["verse_key"])
            except CoordinateError:
                lookup_failures += 1
                continue
            if standard_text != packet["standard_kjv_text"]:
                lookup_failures += 1
            if current_text != packet["current_gd_text"]:
                lookup_failures += 1
            if (standard_text != current_text) != packet["text_differs"]:
                lookup_failures += 1
    _check(checks, "bible_coordinate_lookups_performed", combined, lookups)
    _check(checks, "bible_coordinate_lookup_failures", 0, lookup_failures)
    _check(checks, "anomaly_rows", EXPECTED_COUNTS["anomaly_rows"],
           measured.get("reference_anomalies", {}).get("row_count"))
    _check(checks, "packet_evidence_never_has_empty_finding_uid", 0,
           sum(1 for p in packets_a + packets_b for item in p["evidence"]
               if not item["finding_uid"]))
    _check(checks, "every_packet_evidence_item_traceable_to_verse", True,
           _evidence_traceable(packets_a, packets_b))

    # ---- transformation reconciliation ---------------------------------
    _check(checks, "transformation_rules", EXPECTED_COUNTS["transformation_rules"],
           manifest_summary["transformation_rules"])
    _check(checks, "transformation_applications",
           EXPECTED_COUNTS["transformation_applications"],
           manifest_summary["transformation_applications"])
    _check(checks, "manifest_reference_entries",
           EXPECTED_COUNTS["manifest_reference_entries"],
           manifest_summary["manifest_reference_entries"])
    _check(checks, "unique_changed_verses",
           EXPECTED_COUNTS["unique_changed_verses"],
           manifest_summary["unique_changed_verses"])
    multi_rule_verses = sum(
        1 for p in packets_a if len(p["current_transformation_rules"]) > 1)
    duplicate_ref_pairs = sum(
        1 for p in packets_a
        for rule in p["current_transformation_rules"]
        if len(rule["manifest_reference_strings"])
        != len(set(rule["manifest_reference_strings"])))
    rules_with_duplicate_entries = sum(
        1 for rule in manifest_summary["rules"]
        if rule["duplicate_reference_entry_count"] > 0)
    duplicate_entries_total = sum(
        rule["duplicate_reference_entry_count"] for rule in manifest_summary["rules"])
    _check(checks, "track_a_verses_with_multiple_rules_present", True,
           multi_rule_verses > 0)
    _check(checks, "rules_with_duplicate_reference_entries_present", True,
           rules_with_duplicate_entries > 0)
    _check(checks, "track_a_verse_rule_pairs_with_duplicates_present", True,
           duplicate_ref_pairs > 0)

    top20 = sorted(
        packets_b,
        key=lambda p: (-p["evidence_summary"]["total_unique_findings"],
                       verse_order_key(p["verse_key"])))[:20]

    audit = {
        "schema_version": PACKET_SCHEMA_VERSION,
        "packet_builder_version": PACKET_BUILDER_VERSION,
        "pins_enforced": pinned,
        "inputs_measured": measured,
        "transformation_manifest_summary": {
            "transformation_rules": manifest_summary["transformation_rules"],
            "transformation_applications": manifest_summary["transformation_applications"],
            "manifest_reference_entries": manifest_summary["manifest_reference_entries"],
            "unique_changed_verses": manifest_summary["unique_changed_verses"],
            "verses_with_multiple_rules": multi_rule_verses,
            "rules_with_duplicate_reference_entries": rules_with_duplicate_entries,
            "duplicate_reference_entries_total": duplicate_entries_total,
            "track_a_verse_rule_pairs_with_duplicate_strings": duplicate_ref_pairs,
            "rule_inventory": [
                {
                    "ruleId": rule["ruleId"],
                    "applicationCount": rule["applicationCount"],
                    "rule_reference_entry_count": rule["rule_reference_entry_count"],
                    "duplicate_reference_entry_count":
                        rule["duplicate_reference_entry_count"],
                    "unique_verse_count": rule["unique_verse_count"],
                }
                for rule in manifest_summary["rules"]
            ],
        },
        "track_a": {
            "packets": a_total,
            "packets_with_direct_archive_evidence": a_with,
            "packets_without_direct_archive_evidence": a_without,
            "evidence_rows": a_evidence_rows,
            "unique_evidence_findings": a_unique_findings,
            "unique_verse_keys": len(set(a_keys)),
            "verses_with_multiple_transformation_rules": multi_rule_verses,
        },
        "track_b": {
            "packets": b_total,
            "unique_verse_keys": len(set(b_keys)),
            "overlap_with_track_a": len(set(a_keys) & set(b_keys)),
            "threshold": TRACK_B_MIN_REVISION_RELEVANT_FINDINGS,
            "min_revision_relevant_findings": min(relevant_counts) if relevant_counts else None,
            "max_revision_relevant_findings": max(relevant_counts) if relevant_counts else None,
            "total_unique_evidence_findings": b_unique_findings,
            "evidence_rows_summed": b_evidence_rows,
            "total_source_document_associations": b_source_document_associations,
            "packets_with_unmanifested_text_difference": b_unmanifested_text_diff,
            "distribution_findings_per_packet": {
                "method": "linear_interpolation_between_order_statistics",
                "min": min(relevant_counts) if relevant_counts else None,
                "median": _median(relevant_counts),
                "p75": _percentile(relevant_counts, 0.75),
                "p90": _percentile(relevant_counts, 0.90),
                "p95": _percentile(relevant_counts, 0.95),
                "max": max(relevant_counts) if relevant_counts else None,
            },
            "distribution_all_evidence_findings_per_packet": {
                "method": "linear_interpolation_between_order_statistics",
                "min": min((p["evidence_summary"]["total_unique_findings"]
                            for p in packets_b), default=None),
                "median": _median(sorted(
                    p["evidence_summary"]["total_unique_findings"] for p in packets_b)),
                "p75": _percentile(sorted(
                    p["evidence_summary"]["total_unique_findings"] for p in packets_b), 0.75),
                "p90": _percentile(sorted(
                    p["evidence_summary"]["total_unique_findings"] for p in packets_b), 0.90),
                "p95": _percentile(sorted(
                    p["evidence_summary"]["total_unique_findings"] for p in packets_b), 0.95),
                "max": max((p["evidence_summary"]["total_unique_findings"]
                            for p in packets_b), default=None),
            },
            "top_20_largest_packets_by_all_evidence": [
                {
                    "verse_key": p["verse_key"],
                    "canonical_reference": p["canonical_reference"],
                    "total_unique_findings": p["evidence_summary"]["total_unique_findings"],
                    "revision_relevant_finding_count":
                        p["evidence_summary"]["revision_relevant_finding_count"],
                    "total_unique_source_documents":
                        p["evidence_summary"]["total_unique_source_documents"],
                }
                for p in top20
            ],
        },
        "combined": {
            "packets": combined,
            "unique_verse_keys": len(set(all_keys)),
            "duplicate_verse_keys": len(all_keys) - len(set(all_keys)),
            "track_a_track_b_disjoint": not (set(a_keys) & set(b_keys)),
        },
        "track_c": {
            "packets": len(owner_overlay),
            "unique_verse_keys": len(set(c_keys)),
            "owner_only_packets": len(c_standalone),
            "pointer_records": len(c_pointer),
            "raw_owner_note_occurrences": c_raw_occurrences,
            "duplicate_owner_note_occurrences": c_duplicate_occurrences,
            "unique_owner_verse_candidates": len(owner_candidates),
            "unresolved_owner_references": 0,
            "overlap_with_track_a": len(c_overlap_a),
            "overlap_with_track_b": len(c_overlap_b),
            "overlap_verse_keys_with_track_a": c_overlap_a,
            "overlap_verse_keys_with_track_b": c_overlap_b,
            "owner_only_verse_keys": [r["verse_key"] for r in c_standalone],
            "owner_candidates_with_direct_archive_evidence": sum(
                1 for r in owner_overlay if _owner_direct_evidence(r) is True),
            "owner_candidates_without_direct_archive_evidence": sum(
                1 for r in owner_overlay if _owner_direct_evidence(r) is False),
            "archive_evidence_threshold": None,
            "owner_reason_is_sufficient": True,
            "owner_inputs": owner_summary,
        },
        "review_universe": {
            "total_unique_verses": len(review_universe),
            "duplicate_review_identities": len(identities) - len(set(identities)),
            "identity_key": "verse_key",
            "sources": {
                "track_a_only": sum(1 for row in review_universe
                                    if row["in_track_a"] and not row["in_track_b"]
                                    and not row["in_track_c"]),
                "track_b_only": sum(1 for row in review_universe
                                    if row["in_track_b"] and not row["in_track_a"]
                                    and not row["in_track_c"]),
                "track_c_only": sum(1 for row in review_universe
                                    if row["owner_only"]),
                "owner_overlay_on_track_a": len(c_overlap_a),
                "owner_overlay_on_track_b": len(c_overlap_b),
            },
            "merge_rule": (
                "One review identity per verse_key. An owner overlay is merged "
                "into the existing A/B packet for that verse; the verse is sent "
                "to review exactly once."),
            "payload_duplication": False,
        },
        "style_policies": {
            "count": len(style_policies),
            "policy_ids": [p["policy_id"] for p in style_policies],
            "applied_count": sum(1 for p in style_policies if p["applied"]),
            "approved_count": sum(1 for p in style_policies if p["approved"]),
            "implemented_count": sum(
                1 for p in style_policies
                if p["implementation_status"] != "not_implemented"),
            "verse_packets_created": 0,
            "reverential_capitalization": next(
                ({"policy_id": p["policy_id"], "stage": p["stage"],
                  "apply_order": p["apply_order"],
                  "reversible_boundary_required":
                      p["reversible_boundary_required"],
                  "applied": p["applied"],
                  "owner_open_review_question": p.get("owner_open_review_question")}
                 for p in style_policies
                 if p.get("reversible_boundary_required")), None),
            "policies": [
                {"policy_id": p["policy_id"], "title": p["title"],
                 "status": p["status"], "approved": p["approved"],
                 "applied": p["applied"],
                 "requires_contextual_classification":
                     p["requires_contextual_classification"],
                 "blind_replacement_forbidden": p["blind_replacement_forbidden"]}
                for p in style_policies],
        },
        "serialization": {
            TRACK_A_STREAM: {
                "packets": a_total,
                "serialized_bytes_exact": bytes_a,
                "serialized_sha256": sha256_text(text_a),
                "records_with_unicode_line_boundary":
                    records_with_unicode_line_boundary(text_a),
            },
            TRACK_B_STREAM: {
                "packets": b_total,
                "serialized_bytes_exact": bytes_b,
                "serialized_sha256": sha256_text(text_b),
                "records_with_unicode_line_boundary":
                    records_with_unicode_line_boundary(text_b),
            },
            "combined_serialized_bytes_exact": bytes_a + bytes_b,
            OWNER_OVERLAY_STREAM: {
                "packets": len(owner_overlay),
                "serialized_bytes_exact":
                    len(serialize_stream(owner_overlay).encode("utf-8")),
                "serialized_sha256":
                    sha256_text(serialize_stream(owner_overlay)),
                "records_with_unicode_line_boundary":
                    records_with_unicode_line_boundary(
                        serialize_stream(owner_overlay)),
            },
            REVIEW_UNIVERSE_STREAM: {
                "packets": len(review_universe),
                "serialized_bytes_exact":
                    len(serialize_stream(review_universe).encode("utf-8")),
                "serialized_sha256":
                    sha256_text(serialize_stream(review_universe)),
                "records_with_unicode_line_boundary":
                    records_with_unicode_line_boundary(
                        serialize_stream(review_universe)),
            },
            "record_terminator": "\\n",
            "record_split_rule": (
                "consumers must split these streams on \"\\n\" only; record "
                "counts above are the authoritative packet counts and "
                "str.splitlines() also breaks on U+2028/U+2029/U+0085/"
                "U+001C-1E/U+000B/U+000C inside JSON string values"),
        },
        "checks": checks,
        "failed_checks": [c["name"] for c in checks if not c["ok"]],
    }
    audit["verdict"] = "pass" if not audit["failed_checks"] else "fail"
    return audit


def _associations_subset_of_index(packets_a, packets_b, verse_evidence_index):
    index = verse_evidence_index["by_verse"]
    for packet in packets_a + packets_b:
        verse_key = packet["verse_key"]
        allowed = index.get(verse_key, {})
        for item in packet["evidence"]:
            if item["finding_uid"] not in allowed:
                return False
    return True


def _evidence_traceable(packets_a, packets_b):
    for packet in packets_a + packets_b:
        verse_key = packet["verse_key"]
        for item in packet["evidence"]:
            if not item["finding_uid"]:
                return False
            if verse_key not in set(item["mapped_verse_keys"]):
                return False
    return True


# --------------------------------------------------------------------------
# Frozen input validation
# --------------------------------------------------------------------------


def resolve_coordinate_source(coordinates_path, enforce_pins):
    """Resolve the ONE coordinate artifact a run is allowed to use.

    A pinned run must never read one coordinate source while reporting another,
    so an explicit alternate path is refused before any packet construction.
    Unpinned (explicit test) runs may point at a synthetic coordinate table.
    """
    if coordinates_path is not None:
        if enforce_pins:
            raise PacketInputError(
                "pinned run refuses an alternate coordinate artifact "
                "({!r}); the committed default is {}".format(
                    coordinates_path, CANONICAL_COORDINATES_PATH))
        return os.path.abspath(coordinates_path)
    return CANONICAL_COORDINATES_PATH


def validate_coordinate_artifact(path, enforce_pins=True,
                                 expected_sha256=CANONICAL_COORDINATES_SHA256,
                                 expected_counts=None):
    """Hash + count-validate the coordinate artifact actually being used."""
    if expected_counts is None:
        expected_counts = COORDINATE_COUNT_PINS
    problems = []
    if not os.path.isfile(path):
        if enforce_pins:
            problems.append("missing coordinate artifact: {}".format(path))
        measured = {"path": path, "present": False, "loaded_from": path}
        if problems:
            raise PacketInputError("; ".join(problems))
        return measured
    digest = sha256_file(path)
    books = load_coordinate_books(path)
    counts = coordinate_counts(books)
    measured = {
        "path": CANONICAL_COORDINATES_PATH,
        "loaded_from": os.path.abspath(path),
        "sha256": digest,
        "expected_sha256": expected_sha256,
        "sha256_matches": digest == expected_sha256,
        "counts": counts,
        "expected_counts": dict(expected_counts),
        "counts_match": counts == dict(expected_counts),
    }
    if enforce_pins:
        if digest != expected_sha256:
            problems.append(
                "canonical coordinates sha256 {} != pinned {}".format(
                    digest, expected_sha256))
        if counts != dict(expected_counts):
            problems.append(
                "canonical coordinate counts {} != pinned {}".format(
                    counts, dict(expected_counts)))
    if problems:
        raise PacketInputError("; ".join(problems))
    return measured


def validate_code_dependencies(
        enforce_pins=True,
        expected_mapping_sha256=MAPPING_MODULE_SHA256,
        expected_mapping_version=MAPPING_MODULE_VERSION_EXPECTED,
        expected_engine_sha256=ENGINE_MODULE_SHA256,
        expected_engine_version=ENGINE_MODULE_VERSION_EXPECTED):
    """Pin the mapping module and scripture engine actually imported."""
    measured = {}
    problems = []

    mapping_version = getattr(MAPPING, "VERSION", None) or getattr(
        MAPPING, "MAPPER_VERSION", None)
    engine_version = getattr(ENGINE, "VERSION", None)
    mapping_digest = sha256_file(MAPPING_MODULE_PATH)
    engine_digest = sha256_file(ENGINE_MODULE_PATH)

    measured["gd_bible_revision_mapping"] = {
        "path": MAPPING_MODULE_PATH,
        "sha256": mapping_digest,
        "expected_sha256": expected_mapping_sha256,
        "sha256_matches": mapping_digest == expected_mapping_sha256,
        "version": mapping_version,
        "expected_version": expected_mapping_version,
        "version_matches": mapping_version == expected_mapping_version,
    }
    measured["gd_scripture_engine"] = {
        "path": ENGINE_MODULE_PATH,
        "sha256": engine_digest,
        "expected_sha256": expected_engine_sha256,
        "sha256_matches": engine_digest == expected_engine_sha256,
        "version": engine_version,
        "expected_version": expected_engine_version,
        "version_matches": engine_version == expected_engine_version,
    }
    if enforce_pins:
        if mapping_digest != expected_mapping_sha256:
            problems.append(
                "gd_bible_revision_mapping sha256 {} != pinned {}".format(
                    mapping_digest, expected_mapping_sha256))
        if mapping_version != expected_mapping_version:
            problems.append(
                "gd_bible_revision_mapping version {} != pinned {}".format(
                    mapping_version, expected_mapping_version))
        if engine_digest != expected_engine_sha256:
            problems.append(
                "gd_scripture_engine sha256 {} != pinned {}".format(
                    engine_digest, expected_engine_sha256))
        if engine_version != expected_engine_version:
            problems.append(
                "gd_scripture_engine version {} != pinned {}".format(
                    engine_version, expected_engine_version))
    if problems:
        raise PacketInputError("; ".join(problems))
    return measured


def validate_frozen_inputs(paths, enforce_pins=True, coordinate_path=None):
    """Measure and validate every frozen input. Raises on any drift.

    ``coordinate_path`` is the already-resolved coordinate artifact (see
    ``resolve_coordinate_source``); the measured provenance always records that
    exact file, never a different one.
    """
    measured = {}
    problems = []

    if coordinate_path is None:
        coordinate_path = CANONICAL_COORDINATES_PATH
    measured["canonical_coordinates"] = validate_coordinate_artifact(
        coordinate_path, enforce_pins=enforce_pins)
    measured["code_dependencies"] = validate_code_dependencies(
        enforce_pins=enforce_pins)

    for role, (_filename, expected_sha, _expected_rows) in EVIDENCE_BRIDGE_FILES.items():
        path = paths[role]
        if not os.path.isfile(path):
            if enforce_pins:
                problems.append("missing input {}: {}".format(role, path))
            measured[role] = {"path": path, "present": False}
            continue
        digest = sha256_file(path)
        entry = {"path": path, "sha256": digest,
                 "expected_sha256": expected_sha,
                 "sha256_matches": digest == expected_sha}
        measured[role] = entry
        if enforce_pins and digest != expected_sha:
            problems.append(
                "{} sha256 {} != pinned {}".format(role, digest, expected_sha))

    for role, path, expected_sha in (
            ("standard_kjv_asset", paths["standard_kjv_asset"], STANDARD_KJV_ASSET_SHA256),
            ("current_gd_asset", paths["current_gd_asset"], CURRENT_GD_ASSET_SHA256),
            ("transformation_manifest", paths["transformation_manifest"],
             TRANSFORMATION_MANIFEST_SHA256),
            ("owner_inputs", paths["owner_inputs"], OWNER_INPUTS_SHA256)):
        if not os.path.isfile(path):
            if enforce_pins:
                problems.append("missing input {}: {}".format(role, path))
            measured[role] = {"path": path, "present": False}
            continue
        digest = sha256_file(path)
        measured[role] = {"path": path, "sha256": digest,
                          "expected_sha256": expected_sha,
                          "sha256_matches": digest == expected_sha}
        if enforce_pins and digest != expected_sha:
            problems.append(
                "{} sha256 {} != pinned {}".format(role, digest, expected_sha))

    if os.path.isfile(BUILDER_SOURCE_PATH):
        measured["packet_builder_source"] = {
            "path": BUILDER_SOURCE_PATH,
            "sha256": sha256_file(BUILDER_SOURCE_PATH),
            "packet_builder_version": PACKET_BUILDER_VERSION,
        }

    # Evidence-bridge manifest: declared counts and pinned identity fields.
    bridge_manifest_path = paths["evidence_bridge_manifest"]
    declared = {}
    if os.path.isfile(bridge_manifest_path):
        try:
            with open(bridge_manifest_path, encoding="utf-8") as handle:
                bridge_manifest = json.load(handle)
        except (OSError, ValueError) as exc:
            bridge_manifest = None
            problems.append("evidence bridge manifest unreadable: {}".format(exc))
        if isinstance(bridge_manifest, dict):
            declared = bridge_manifest.get("counts") or {}
            measured["evidence_bridge_manifest"] = {
                "path": bridge_manifest_path,
                "sha256": measured.get("evidence_bridge_manifest", {}).get("sha256"),
                "schema_version": bridge_manifest.get("schema_version"),
                "artifact": bridge_manifest.get("artifact"),
                "generated_at": bridge_manifest.get("generated_at"),
                "inputs_pinned": bridge_manifest.get("inputs_pinned"),
                "declared_counts": dict(declared),
                "mapper_version": bridge_manifest.get("mapper_version"),
                "engine_version": bridge_manifest.get("engine_version"),
            }
            if enforce_pins:
                declared_pairs = (
                    ("findings", declared.get("findings")),
                    ("unique_finding_uids", declared.get("unique_finding_uids")),
                    ("finding_uid_collisions", declared.get("finding_uid_collisions")),
                    ("findings_with_verse_mapping",
                     declared.get("findings_with_verse_mapping")),
                    ("verse_evidence_rows", declared.get("verse_evidence_rows")),
                    ("unique_canonical_verses", declared.get("unique_canonical_verses")),
                    ("anomaly_rows", declared.get("anomaly_rows")),
                )
                for key, value in declared_pairs:
                    if value != EXPECTED_COUNTS[key]:
                        problems.append(
                            "evidence bridge declares {}={} expected {}".format(
                                key, value, EXPECTED_COUNTS[key]))
                if bridge_manifest.get("schema_version") != SOURCE_MAPPING_SCHEMA_VERSION:
                    problems.append(
                        "evidence bridge schema_version {} expected {}".format(
                            bridge_manifest.get("schema_version"),
                            SOURCE_MAPPING_SCHEMA_VERSION))
                if bridge_manifest.get("inputs_pinned") is not True:
                    problems.append("evidence bridge inputs_pinned is not true")

    # Independent row count for the small anomaly stream (the two large streams
    # are counted by their own loaders).
    anomalies_path = paths["reference_anomalies"]
    if os.path.isfile(anomalies_path):
        measured.setdefault("reference_anomalies", {})["row_count"] = (
            count_jsonl_rows(anomalies_path)["rows"])
        if enforce_pins and (
                measured["reference_anomalies"]["row_count"]
                != EXPECTED_COUNTS["anomaly_rows"]):
            problems.append(
                "reference_anomalies rows {} != pinned {}".format(
                    measured["reference_anomalies"]["row_count"],
                    EXPECTED_COUNTS["anomaly_rows"]))

    if problems:
        raise PacketInputError(
            "frozen input validation failed ({}): {}".format(
                len(problems), "; ".join(problems[:10])))
    measured["pins_enforced"] = bool(enforce_pins)
    return measured


# --------------------------------------------------------------------------
# Stream manifest
# --------------------------------------------------------------------------


def _dependency_pin_view(source, keys):
    """Compact, review-facing projection of a measured dependency pin."""
    if not isinstance(source, dict):
        return None
    return {key: source.get(key) for key in keys}


def build_stream_manifest(measured, manifest_summary, audit, generated_at,
                          streams, pinned=True, owner_summary=None,
                          review_universe_summary=None, track_c_summary=None):
    """Build the production stream manifest (no judgments, pins + counts)."""
    return {
        "artifact": "gd_bible_revision_review_packets",
        "packet_builder_version": PACKET_BUILDER_VERSION,
        "packet_schema_version": PACKET_SCHEMA_VERSION,
        "source_mapping_schema_version": SOURCE_MAPPING_SCHEMA_VERSION,
        "generated_at": generated_at,
        "inputs_pinned": bool(pinned),
        "inputs": measured,
        "dependency_pins": {
            "canonical_coordinates": _dependency_pin_view(
                measured.get("canonical_coordinates"), ("path", "loaded_from",
                                                        "sha256", "counts",
                                                        "sha256_matches",
                                                        "counts_match")),
            "gd_bible_revision_mapping": _dependency_pin_view(
                measured.get("code_dependencies", {}).get(
                    "gd_bible_revision_mapping"),
                ("path", "sha256", "version", "sha256_matches",
                 "version_matches")),
            "gd_scripture_engine": _dependency_pin_view(
                measured.get("code_dependencies", {}).get(
                    "gd_scripture_engine"),
                ("path", "sha256", "version", "sha256_matches",
                 "version_matches")),
        },
        "source_mapping": {
            "artifact": SOURCE_MAPPING_ARTIFACT,
            "schema_version": SOURCE_MAPPING_SCHEMA_VERSION,
            "authoritative_association": "verse_evidence_index:verse_key+finding_uid",
            "remapping_performed": False,
            "associations_inferred": False,
        },
        "selection": {
            "revision_relevant_topics": list(REVISION_RELEVANT_TOPICS),
            "track_a": {
                "name": TRACK_A_NAME,
                "rule": "every verse currently changed by TRANSFORMATION_MANIFEST.json",
                "packets": audit["track_a"]["packets"],
            },
            "track_b": {
                "name": TRACK_B_NAME,
                "rule": (
                    "not-currently-changed verse with >= {} findings whose topic "
                    "is one of {}".format(
                        TRACK_B_MIN_REVISION_RELEVANT_FINDINGS,
                        ", ".join(REVISION_RELEVANT_TOPICS))),
                "threshold": TRACK_B_MIN_REVISION_RELEVANT_FINDINGS,
                "packets": audit["track_b"]["packets"],
            },
            "track_c": {
                "name": TRACK_C_NAME,
                "rule": (
                    "every verse named by the owner in {} (no archive-evidence "
                    "threshold)".format(OWNER_INPUTS_ARTIFACT)),
                "threshold": None,
                "packets": audit["track_c"]["packets"],
                "owner_only_packets": audit["track_c"]["owner_only_packets"],
                "merge_pointer_records": audit["track_c"]["pointer_records"],
            },
            "combined_packets": audit["combined"]["packets"],
            "combined_unique_verse_keys": audit["combined"]["unique_verse_keys"],
        },
        "owner_inputs": owner_summary,
        "track_c": track_c_summary,
        "review_universe": review_universe_summary,
        "streams": streams,
        "counts": {
            "track_a": {
                "packets": audit["track_a"]["packets"],
                "packets_with_direct_archive_evidence":
                    audit["track_a"]["packets_with_direct_archive_evidence"],
                "packets_without_direct_archive_evidence":
                    audit["track_a"]["packets_without_direct_archive_evidence"],
                "evidence_rows": audit["track_a"]["evidence_rows"],
                "unique_evidence_findings":
                    audit["track_a"]["unique_evidence_findings"],
            },
            "track_b": {
                "packets": audit["track_b"]["packets"],
                "evidence_rows": audit["track_b"]["evidence_rows_summed"],
                "unique_evidence_findings":
                    audit["track_b"]["total_unique_evidence_findings"],
                "total_source_document_associations":
                    audit["track_b"]["total_source_document_associations"],
            },
            "combined_packets": audit["combined"]["packets"],
            "track_c": {
                "packets": audit["track_c"]["packets"],
                "owner_only_packets": audit["track_c"]["owner_only_packets"],
                "pointer_records": audit["track_c"]["pointer_records"],
                "raw_owner_note_occurrences":
                    audit["track_c"]["raw_owner_note_occurrences"],
                "duplicate_owner_note_occurrences":
                    audit["track_c"]["duplicate_owner_note_occurrences"],
                "overlap_with_track_a": audit["track_c"]["overlap_with_track_a"],
                "overlap_with_track_b": audit["track_c"]["overlap_with_track_b"],
                "owner_candidates_with_direct_archive_evidence":
                    audit["track_c"]["owner_candidates_with_direct_archive_evidence"],
                "owner_candidates_without_direct_archive_evidence":
                    audit["track_c"]["owner_candidates_without_direct_archive_evidence"],
            },
            "review_universe_total_unique_verses":
                audit["review_universe"]["total_unique_verses"],
            "style_policies": {
                "count": audit["style_policies"]["count"],
                "applied": audit["style_policies"]["applied_count"],
                "approved": audit["style_policies"]["approved_count"],
                "verse_packets_created": 0,
            },
        },
        "transformation_manifest": audit["transformation_manifest_summary"],
        "evidence_size_distribution_track_b": {
            "revision_relevant_findings_per_packet":
                audit["track_b"]["distribution_findings_per_packet"],
            "all_evidence_findings_per_packet":
                audit["track_b"]["distribution_all_evidence_findings_per_packet"],
            "top_20_largest_packets_by_all_evidence":
                audit["track_b"]["top_20_largest_packets_by_all_evidence"],
        },
        "provenance_statement": PROVENANCE_STATEMENT,
        "evidence_class_statement": EVIDENCE_CLASS_STATEMENT,
        "editorial_boundary_statement": EDITORIAL_BOUNDARY_STATEMENT,
        "audit_verdict": audit["verdict"],
        "audit_failed_checks": audit["failed_checks"],
    }


# --------------------------------------------------------------------------
# Owner-specified review inputs (Track C)
# --------------------------------------------------------------------------


def load_owner_inputs(path=None):
    """Load and structurally validate the durable owner-input artifact."""
    path = path or OWNER_INPUTS_PATH
    if not os.path.isfile(path):
        raise PacketInputError("missing owner review inputs: {}".format(path))
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    problems = []
    if data.get("artifact") != OWNER_INPUTS_ARTIFACT:
        problems.append("artifact {!r} != {!r}".format(
            data.get("artifact"), OWNER_INPUTS_ARTIFACT))
    if data.get("schema_version") != OWNER_INPUTS_SCHEMA_VERSION:
        problems.append("schema_version {!r} != {!r}".format(
            data.get("schema_version"), OWNER_INPUTS_SCHEMA_VERSION))
    candidates = data.get("verse_candidates")
    policies = data.get("style_policies")
    if not isinstance(candidates, list) or not candidates:
        problems.append("verse_candidates must be a non-empty list")
    if not isinstance(policies, list):
        problems.append("style_policies must be a list")
    if problems:
        raise PacketBuildError(
            "owner review inputs are malformed ({}): {}".format(
                len(problems), "; ".join(problems)))
    for candidate in candidates:
        for field in ("candidate_id", "candidate_category", "owner_reference_raw",
                      "owner_reference_parser_input", "canonical_reference",
                      "verse_key", "owner_note_occurrences"):
            if field not in candidate:
                problems.append("{}: missing field {}".format(
                    candidate.get("candidate_id", "<unnamed>"), field))
        occurrences = candidate.get("owner_note_occurrences")
        if not isinstance(occurrences, list) or not occurrences:
            problems.append("{}: owner_note_occurrences must be non-empty".format(
                candidate.get("candidate_id", "<unnamed>")))
        if candidate.get("candidate_status") != OWNER_CANDIDATE_STATUS:
            problems.append("{}: candidate_status {!r} != {!r}".format(
                candidate.get("candidate_id"), candidate.get("candidate_status"),
                OWNER_CANDIDATE_STATUS))
        if candidate.get("provenance_class") != OWNER_PROVENANCE_CLASS:
            problems.append("{}: provenance_class {!r} != {!r}".format(
                candidate.get("candidate_id"), candidate.get("provenance_class"),
                OWNER_PROVENANCE_CLASS))
        if candidate.get("accepted_translation") is not False:
            problems.append("{}: accepted_translation must be false".format(
                candidate.get("candidate_id")))
        if not (candidate.get("proposed_change")
                or candidate.get("owner_question")):
            problems.append("{}: needs a proposed_change or an owner_question".format(
                candidate.get("candidate_id")))
    for policy in policies:
        if policy.get("approved") is not False:
            problems.append("style policy {}: approved must be false".format(
                policy.get("policy_id")))
        if policy.get("applied") is not False:
            problems.append("style policy {}: applied must be false".format(
                policy.get("policy_id")))
        if policy.get("implementation_status") != "not_implemented":
            problems.append(
                "style policy {}: implementation_status must be "
                "not_implemented".format(policy.get("policy_id")))
    if problems:
        raise PacketBuildError(
            "owner review inputs are malformed ({}): {}".format(
                len(problems), "; ".join(problems[:10])))
    return data


def classify_owner_reference(raw, table=None):
    """Resolve one owner reference through the committed mapping parser."""
    core = MAPPING.classify_raw_reference(raw, table=table)
    verse_keys = core.get("verse_keys") or []
    status = core.get("status")
    if status not in MAPPING.VERSE_MAPPED_STATUSES or len(verse_keys) != 1:
        return status, None
    return status, verse_keys[0]


def classify_owner_context_reference(raw, table=None):
    """Resolve a context-only owner reference, which may legitimately be a range."""
    core = MAPPING.classify_raw_reference(raw, table=table)
    verse_keys = core.get("verse_keys") or []
    status = core.get("status")
    if status not in MAPPING.VERSE_MAPPED_STATUSES or not verse_keys:
        return status, []
    return status, list(verse_keys)


def resolve_owner_candidates(owner_inputs, books, table=None):
    """Deterministically resolve every owner candidate; fail closed on drift.

    Never guesses: an owner reference the committed parser cannot resolve is
    only usable when the owner input itself declares an explicit normalization,
    and both the raw string and the raw parser status are preserved.
    """
    problems = []
    resolved = []
    for candidate in owner_inputs["verse_candidates"]:
        candidate_id = candidate["candidate_id"]
        raw = candidate["owner_reference_raw"]
        parser_input = candidate["owner_reference_parser_input"]
        normalization = candidate.get("owner_reference_normalization")

        status, verse_key = classify_owner_reference(parser_input, table=table)
        if verse_key is None:
            problems.append("{}: parser input {!r} classified {} (not exactly "
                            "one verse)".format(candidate_id, parser_input,
                                                status))
            continue
        if normalization is not None:
            if normalization.get("authority") != "owner_declared":
                problems.append("{}: normalization authority must be "
                                "owner_declared".format(candidate_id))
            if normalization.get("to") != parser_input:
                problems.append("{}: normalization target {!r} != parser input "
                                "{!r}".format(candidate_id, normalization.get("to"),
                                              parser_input))
            if normalization.get("from") != raw:
                problems.append("{}: normalization source {!r} != raw {!r}".format(
                    candidate_id, normalization.get("from"), raw))

        raw_status, _raw_key = classify_owner_reference(raw, table=table)
        if raw_status != candidate.get("owner_reference_raw_parser_status"):
            problems.append(
                "{}: recorded raw parser status {!r} != measured {!r}".format(
                    candidate_id, candidate.get("owner_reference_raw_parser_status"),
                    raw_status))

        book_id, chapter, verse = parse_verse_key(verse_key)
        book = books[book_id - 1]["book"] if 0 < book_id <= len(books) else None
        if book is None:
            problems.append("{}: verse key {} outside the coordinate table".format(
                candidate_id, verse_key))
            continue
        reference = canonical_reference(book, chapter, verse)
        if verse_key != candidate["verse_key"]:
            problems.append("{}: stored verse_key {!r} != resolved {!r}".format(
                candidate_id, candidate["verse_key"], verse_key))
        if reference != candidate["canonical_reference"]:
            problems.append(
                "{}: stored canonical_reference {!r} != resolved {!r}".format(
                    candidate_id, candidate["canonical_reference"], reference))

        occurrences = candidate["owner_note_occurrences"]
        seen = set()
        duplicate_count = 0
        for occurrence in occurrences:
            text = occurrence.get("text")
            if not isinstance(text, str) or not text:
                problems.append("{}: occurrence {} has no text".format(
                    candidate_id, occurrence.get("occurrence")))
            if text in seen:
                duplicate_count += 1
            seen.add(text)

        context_keys = []
        for context_reference in candidate.get("context_only_references") or []:
            context_status, resolved_context = classify_owner_context_reference(
                context_reference, table=table)
            if not resolved_context:
                problems.append("{}: context reference {!r} classified "
                                "{}".format(candidate_id, context_reference,
                                            context_status))
                continue
            context_keys.extend(resolved_context)
        # ``context_only_verse_keys`` records the CONTEXT-ONLY part of a resolved
        # context reference: the candidate's own verse is excluded, so a quoted
        # range never turns an extra verse into a candidate.
        foreign_context = sorted(set(context_keys) - {verse_key})
        recorded_context = sorted(candidate.get("context_only_verse_keys") or [])
        if foreign_context != recorded_context:
            problems.append("{}: context_only_verse_keys {} != resolved {}".format(
                candidate_id, recorded_context, foreign_context))

        resolved.append({
            "candidate_id": candidate_id,
            "candidate_category": candidate["candidate_category"],
            "owner_reference_raw": raw,
            "owner_reference_parser_input": parser_input,
            "owner_reference_normalization": normalization,
            "owner_reference_raw_parser_status": raw_status,
            "canonical_reference": reference,
            "verse_key": verse_key,
            "book_id": book_id,
            "book": book,
            "chapter": chapter,
            "verse": verse,
            "owner_note_occurrences": [
                dict(occurrence) for occurrence in occurrences],
            "owner_note_occurrence_count": len(occurrences),
            "duplicate_occurrence_count": duplicate_count,
            "proposed_change": candidate.get("proposed_change"),
            "owner_question": candidate.get("owner_question"),
            "candidate_status": candidate["candidate_status"],
            "provenance_class": candidate["provenance_class"],
            "accepted_translation": False,
            "flags": dict(candidate.get("flags") or {}),
            "context_only_references": list(
                candidate.get("context_only_references") or []),
            "context_only_verse_keys": list(foreign_context),
            "resolution_note": candidate.get("resolution_note"),
        })

    candidate_keys = {c["verse_key"] for c in resolved}
    for candidate in resolved:
        for context_key in candidate["context_only_verse_keys"]:
            if context_key in candidate_keys:
                problems.append(
                    "{}: context-only verse {} is also a candidate".format(
                        candidate["candidate_id"], context_key))
    if problems:
        raise PacketBuildError(
            "owner candidate resolution failed ({}): {}".format(
                len(problems), "; ".join(problems[:10])))
    return resolved


def build_owner_block(group):
    """The owner-specified block attached to a Track C overlay record.

    Only owner-supplied text and mechanical resolution metadata: archive
    evidence is never mixed in, and no justification is invented.
    """
    return {
        "schema_version": OWNER_INPUTS_SCHEMA_VERSION,
        "authority": "owner_specified",
        "provenance_class": OWNER_PROVENANCE_CLASS,
        "candidate_status": OWNER_CANDIDATE_STATUS,
        "accepted_translation": False,
        "candidate_count": len(group),
        "candidate_ids": [c["candidate_id"] for c in group],
        "candidate_categories": sorted({c["candidate_category"] for c in group}),
        "owner_note_occurrence_count": sum(
            c["owner_note_occurrence_count"] for c in group),
        "duplicate_occurrence_count": sum(
            c["duplicate_occurrence_count"] for c in group),
        "owner_rationale_is_archive_evidence": False,
        "statement": TRACK_C_STATEMENT,
        "candidates": [
            {
                "candidate_id": c["candidate_id"],
                "candidate_category": c["candidate_category"],
                "owner_reference_raw": c["owner_reference_raw"],
                "owner_reference_parser_input": c["owner_reference_parser_input"],
                "owner_reference_normalization": c["owner_reference_normalization"],
                "owner_reference_raw_parser_status":
                    c["owner_reference_raw_parser_status"],
                "canonical_reference": c["canonical_reference"],
                "verse_key": c["verse_key"],
                "owner_note_occurrences": [
                    dict(occurrence) for occurrence in c["owner_note_occurrences"]],
                "proposed_change": c["proposed_change"],
                "owner_question": c["owner_question"],
                "candidate_status": c["candidate_status"],
                "provenance_class": c["provenance_class"],
                "accepted_translation": False,
                "flags": dict(c["flags"]),
                "context_only_references": list(c["context_only_references"]),
                "context_only_verse_keys": list(c["context_only_verse_keys"]),
                "resolution_note": c["resolution_note"],
            }
            for c in group
        ],
    }


def group_owner_candidates(candidates):
    """Group resolved candidates by canonical verse key (deterministic order)."""
    grouped = {}
    for candidate in candidates:
        grouped.setdefault(candidate["verse_key"], []).append(candidate)
    return [(verse_key, grouped[verse_key])
            for verse_key in sorted(grouped, key=verse_order_key)]


def build_owner_overlay(candidates, packets_a, packets_b, text_index,
                        verse_evidence_index, records):
    """Build the Track C overlay records, one per unique owner verse key.

    A verse already published in Track A or Track B gets a POINTER record that
    carries the owner block and names the stream holding the authoritative
    text/evidence, so no A/B payload is duplicated. An owner-only verse gets a
    complete standalone Track C review packet.
    """
    a_keys = {p["verse_key"]: p for p in packets_a}
    b_keys = {p["verse_key"]: p for p in packets_b}
    problems = []
    overlay = []
    for verse_key, group in group_owner_candidates(candidates):
        book_id, chapter, verse = parse_verse_key(verse_key)
        owner_block = build_owner_block(group)
        in_a = verse_key in a_keys
        in_b = verse_key in b_keys
        overlap = {"track_a": in_a, "track_b": in_b}
        if in_a or in_b:
            existing_stream = TRACK_A_STREAM if in_a else TRACK_B_STREAM
            existing_track = TRACK_A if in_a else TRACK_B
            existing_packet = a_keys[verse_key] if in_a else b_keys[verse_key]
            overlay.append({
                "schema_version": OWNER_OVERLAY_SCHEMA_VERSION,
                "overlay_schema_version": OWNER_OVERLAY_SCHEMA_VERSION,
                "record_type": OWNER_OVERLAY_RECORD_TYPE,
                "overlay_mode": "merge_into_existing_packet",
                "track": TRACK_C,
                "track_name": TRACK_C_NAME,
                "priority_tier": PRIORITY_TIER_C,
                "review_identity": verse_key,
                "verse_key": verse_key,
                "canonical_reference": existing_packet["canonical_reference"],
                "book_id": book_id,
                "book": existing_packet["book"],
                "chapter": chapter,
                "verse": verse,
                "owner_only": False,
                "overlap": overlap,
                "payload_embedded": False,
                "existing_packet_stream": existing_stream,
                "existing_packet_track": existing_track,
                "existing_packet_direct_archive_evidence":
                    bool(existing_packet["direct_archive_verse_evidence"]),
                "merge_instruction": (
                    "Merge this owner_input block into the existing packet for "
                    "verse_key {} in {} and send that verse to review exactly "
                    "once.".format(verse_key, existing_stream)),
                "owner_input": owner_block,
            })
        else:
            packet = build_packet(
                TRACK_C, verse_key, text_index, [],
                verse_evidence_index["by_verse"].get(verse_key, {}), records,
                problems)
            packet["overlay_schema_version"] = OWNER_OVERLAY_SCHEMA_VERSION
            packet["record_type"] = OWNER_OVERLAY_RECORD_TYPE
            packet["overlay_mode"] = "standalone_owner_packet"
            packet["review_identity"] = verse_key
            packet["owner_only"] = True
            packet["overlap"] = overlap
            packet["payload_embedded"] = True
            packet["existing_packet_stream"] = None
            packet["owner_input"] = owner_block
            overlay.append(packet)
    if problems:
        raise PacketBuildError(
            "owner overlay build failed ({}): {}".format(
                len(problems), "; ".join(problems[:10])))
    return overlay


def build_review_universe_index(packets_a, packets_b, overlay):
    """One deterministic row per unique review verse key across A + B + C.

    ``review_identity`` is the canonical verse key, so a verse can never be
    sent to the model twice just because an owner also flagged it.
    """
    a_keys = {p["verse_key"]: p for p in packets_a}
    b_keys = {p["verse_key"]: p for p in packets_b}
    c_keys = {r["verse_key"]: r for r in overlay}
    universe = set(a_keys) | set(b_keys) | set(c_keys)
    rows = []
    for verse_key in sorted(universe, key=verse_order_key):
        in_a = verse_key in a_keys
        in_b = verse_key in b_keys
        in_c = verse_key in c_keys
        source = a_keys.get(verse_key) or b_keys.get(verse_key) or c_keys[verse_key]
        if in_a:
            packet_stream, packet_track = TRACK_A_STREAM, TRACK_A
        elif in_b:
            packet_stream, packet_track = TRACK_B_STREAM, TRACK_B
        else:
            packet_stream, packet_track = OWNER_OVERLAY_STREAM, TRACK_C
        sources = []
        if in_a:
            sources.append("track_a_existing_change")
        if in_b:
            sources.append("track_b_new_change_tier_1")
        if in_c:
            sources.append("track_c_owner_specified")
        overlay_record = c_keys.get(verse_key)
        rows.append({
            "schema_version": REVIEW_UNIVERSE_SCHEMA_VERSION,
            "record_type": REVIEW_UNIVERSE_RECORD_TYPE,
            "review_identity": verse_key,
            "verse_key": verse_key,
            "canonical_reference": source["canonical_reference"],
            "book_id": source["book_id"],
            "book": source["book"],
            "chapter": source["chapter"],
            "verse": source["verse"],
            "in_track_a": in_a,
            "in_track_b": in_b,
            "in_track_c": in_c,
            "owner_only": in_c and not (in_a or in_b),
            "packet_stream": packet_stream,
            "packet_track": packet_track,
            "owner_overlay_stream": OWNER_OVERLAY_STREAM if in_c else None,
            "owner_candidate_ids": (
                list(overlay_record["owner_input"]["candidate_ids"])
                if in_c else []),
            "review_sources": sources,
            "review_once": True,
        })
    return rows


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------


def generated_at_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def resolve_generated_at(explicit=None):
    if explicit:
        try:
            datetime.datetime.fromisoformat(explicit.replace("Z", "+00:00"))
        except ValueError:
            raise PacketBuildError(
                "invalid --generated-at value: {!r}".format(explicit))
        return explicit
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch and epoch.strip().isdigit():
        return datetime.datetime.fromtimestamp(
            int(epoch), datetime.timezone.utc).isoformat()
    return generated_at_now()


def run_build(paths, enforce_pins=True, coordinates_path=None,
              generated_at=None):
    """Run the whole deterministic build and audit in memory.

    The coordinate source is resolved FIRST: a pinned run refuses an explicit
    alternate path before any input is read, so provenance can never describe a
    different file than the one actually used.
    """
    resolved_coordinates = resolve_coordinate_source(coordinates_path,
                                                     enforce_pins)
    measured = validate_frozen_inputs(
        paths, enforce_pins=enforce_pins, coordinate_path=resolved_coordinates)

    books = load_coordinate_books(resolved_coordinates)

    standard_asset = load_bible_asset(paths["standard_kjv_asset"])
    current_asset = load_bible_asset(paths["current_gd_asset"])
    text_index = BibleTextIndex(standard_asset, current_asset, books)

    manifest = load_transformation_manifest(paths["transformation_manifest"])
    manifest_summary, verse_rules = parse_transformation_manifest(manifest)
    if enforce_pins:
        for key in ("transformation_rules", "transformation_applications",
                    "manifest_reference_entries", "unique_changed_verses"):
            if manifest_summary[key] != EXPECTED_COUNTS[key]:
                raise PacketInputError(
                    "transformation manifest {}={} expected {}".format(
                        key, manifest_summary[key], EXPECTED_COUNTS[key]))

    verse_evidence_index = load_verse_evidence_index(paths["verse_evidence_index"])
    if enforce_pins:
        for key, value in (("verse_evidence_rows", verse_evidence_index["rows"]),
                           ("unique_canonical_verses",
                            verse_evidence_index["unique_verses"])):
            if value != EXPECTED_COUNTS[key]:
                raise PacketInputError(
                    "verse evidence index {}={} expected {}".format(
                        key, value, EXPECTED_COUNTS[key]))

    changed_keys = sorted(verse_rules, key=verse_order_key)
    track_a_keys = select_track_a(changed_keys)
    track_b_keys = select_track_b(verse_evidence_index, changed_keys)
    if enforce_pins:
        if len(track_a_keys) != EXPECTED_COUNTS["track_a_packets"]:
            raise PacketInputError(
                "track A packets {} expected {}".format(
                    len(track_a_keys), EXPECTED_COUNTS["track_a_packets"]))
        if len(track_b_keys) != EXPECTED_COUNTS["track_b_packets"]:
            raise PacketInputError(
                "track B packets {} expected {}".format(
                    len(track_b_keys), EXPECTED_COUNTS["track_b_packets"]))
    overlap = set(track_a_keys) & set(track_b_keys)
    if overlap:
        raise PacketBuildError(
            "track A and track B overlap on {} verse(s)".format(len(overlap)))

    # ---- Track C: owner-specified review candidates --------------------
    # Resolved BEFORE the finding load so owner-only verses also get their
    # deterministic archive evidence attached.
    owner_inputs = load_owner_inputs(paths["owner_inputs"])
    owner_candidates = resolve_owner_candidates(owner_inputs, books)
    if enforce_pins:
        if len(owner_candidates) != EXPECTED_COUNTS["owner_verse_candidates"]:
            raise PacketInputError(
                "owner verse candidates {} expected {}".format(
                    len(owner_candidates),
                    EXPECTED_COUNTS["owner_verse_candidates"]))
        owner_occurrences = sum(
            c["owner_note_occurrence_count"] for c in owner_candidates)
        if owner_occurrences != EXPECTED_COUNTS["owner_note_occurrences"]:
            raise PacketInputError(
                "owner note occurrences {} expected {}".format(
                    owner_occurrences, EXPECTED_COUNTS["owner_note_occurrences"]))
    owner_keys = sorted({c["verse_key"] for c in owner_candidates},
                        key=verse_order_key)

    needed_uids = set()
    for verse_key in track_a_keys + track_b_keys + owner_keys:
        needed_uids.update(verse_evidence_index["by_verse"].get(verse_key, {}))
    finding_load = load_finding_records(
        paths["finding_reference_map"], needed_uids)

    packets_a, packets_b, problems = build_all_packets(
        text_index, verse_rules, verse_evidence_index,
        finding_load["records"], track_a_keys, track_b_keys)
    if finding_load["missing_needed_uids"]:
        problems.append("missing_needed_uids:{}".format(
            len(finding_load["missing_needed_uids"])))
    if problems:
        raise PacketBuildError(
            "packet build failed ({} problem(s)): {}".format(
                len(problems), "; ".join(problems[:10])))

    owner_overlay = build_owner_overlay(
        owner_candidates, packets_a, packets_b, text_index,
        verse_evidence_index, finding_load["records"])
    review_universe = build_review_universe_index(
        packets_a, packets_b, owner_overlay)

    owner_summary = {
        "owner_inputs_path": paths["owner_inputs"],
        "owner_inputs_sha256": sha256_file(paths["owner_inputs"]),
        "schema_version": owner_inputs["schema_version"],
        "raw_owner_note_occurrences": sum(
            c["owner_note_occurrence_count"] for c in owner_candidates),
        "unique_owner_verse_candidates": len(owner_candidates),
        "duplicate_owner_note_occurrences": sum(
            c["duplicate_occurrence_count"] for c in owner_candidates),
        "candidates_with_multiple_occurrences": sum(
            1 for c in owner_candidates if c["owner_note_occurrence_count"] > 1),
        "resolved_verse_keys": [
            {"verse_key": c["verse_key"],
             "canonical_reference": c["canonical_reference"]}
            for c in sorted(owner_candidates,
                            key=lambda c: verse_order_key(c["verse_key"]))],
        "style_policy_count": len(owner_inputs["style_policies"]),
        "style_policy_ids": [p["policy_id"] for p in owner_inputs["style_policies"]],
        "style_policies_implemented": sum(
            1 for p in owner_inputs["style_policies"] if p["applied"]),
        "style_policies_approved": sum(
            1 for p in owner_inputs["style_policies"] if p["approved"]),
        "style_policy_reverential_capitalization_stage": next(
            (p["stage"] for p in owner_inputs["style_policies"]
             if p.get("reversible_boundary_required")), None),
        "style_policy_reverential_capitalization_apply_order": next(
            (p["apply_order"] for p in owner_inputs["style_policies"]
             if p.get("reversible_boundary_required")), None),
    }

    audit = build_audit(packets_a, packets_b, measured, manifest_summary,
                        verse_evidence_index, finding_load,
                        text_index=text_index, pinned=enforce_pins,
                        owner_candidates=owner_candidates,
                        owner_overlay=owner_overlay,
                        review_universe=review_universe,
                        owner_summary=owner_summary,
                        style_policies=owner_inputs["style_policies"])
    if enforce_pins and audit["verdict"] != "pass":
        raise PacketBuildError(
            "audit failed: {}".format(", ".join(audit["failed_checks"][:10])))

    stream_a_text = serialize_stream(packets_a)
    stream_b_text = serialize_stream(packets_b)
    owner_overlay_text = serialize_stream(owner_overlay)
    review_universe_text = serialize_stream(review_universe)
    streams = {
        TRACK_A_STREAM: {
            "packets": len(packets_a),
            "bytes": len(stream_a_text.encode("utf-8")),
            "sha256": sha256_text(stream_a_text),
        },
        TRACK_B_STREAM: {
            "packets": len(packets_b),
            "bytes": len(stream_b_text.encode("utf-8")),
            "sha256": sha256_text(stream_b_text),
        },
        OWNER_OVERLAY_STREAM: {
            "packets": len(owner_overlay),
            "bytes": len(owner_overlay_text.encode("utf-8")),
            "sha256": sha256_text(owner_overlay_text),
            "track": TRACK_C,
            "stream_role": "owner_overlay",
        },
        REVIEW_UNIVERSE_STREAM: {
            "packets": len(review_universe),
            "bytes": len(review_universe_text.encode("utf-8")),
            "sha256": sha256_text(review_universe_text),
            "track": None,
            "stream_role": "review_universe_index",
        },
    }
    manifest_out = build_stream_manifest(
        measured, manifest_summary, audit,
        resolve_generated_at(generated_at), streams, pinned=enforce_pins,
        owner_summary=owner_summary,
        review_universe_summary=audit["review_universe"],
        track_c_summary=audit["track_c"])

    return {
        "packets_a": packets_a,
        "packets_b": packets_b,
        "owner_overlay": owner_overlay,
        "review_universe": review_universe,
        "audit": audit,
        "manifest": manifest_out,
        "stream_a_text": stream_a_text,
        "stream_b_text": stream_b_text,
        "owner_overlay_text": owner_overlay_text,
        "review_universe_text": review_universe_text,
    }


def _stream_manifest_entries(manifest):
    streams = (manifest or {}).get("streams") or {}
    return streams


# Stream filename -> (result key holding its records, result key holding its text).
STREAM_PAYLOAD_KEYS = {
    TRACK_A_STREAM: ("packets_a", "stream_a_text"),
    TRACK_B_STREAM: ("packets_b", "stream_b_text"),
    OWNER_OVERLAY_STREAM: ("owner_overlay", "owner_overlay_text"),
    REVIEW_UNIVERSE_STREAM: ("review_universe", "review_universe_text"),
}


def _expected_stream_values(manifest):
    """Return ``{filename: {packets, bytes, sha256}}`` from the manifest."""
    streams = _stream_manifest_entries(manifest)
    expected = {}
    for name in ARTIFACT_FILES:
        if name == MANIFEST_NAME:
            continue
        entry = streams.get(name) or {}
        expected[name] = {
            "packets": entry.get("packets"),
            "bytes": entry.get("bytes"),
            "sha256": entry.get("sha256"),
        }
    return expected


def validate_publishable_result(result, require_pins=True):
    """Re-validate a build result at the publication boundary.

    Guards against a caller mutating a previously validated result object and
    then handing altered stream content to ``write_artifacts``. Re-derives every
    stream from the packet objects, so mutating either the serialized text or
    the packet list is detected. Returns the validated stream payloads.
    """
    if not isinstance(result, dict):
        raise PacketInputError("refusing to publish a non-mapping result")
    manifest = result.get("manifest")
    audit = result.get("audit")
    if not isinstance(manifest, dict) or not isinstance(audit, dict):
        raise PacketInputError(
            "refusing to publish a result without manifest and audit")
    problems = []

    if require_pins and manifest.get("inputs_pinned") is not True:
        problems.append("manifest inputs_pinned is not true")
    if audit.get("verdict") != "pass":
        problems.append("audit verdict is {!r}".format(audit.get("verdict")))
    if audit.get("failed_checks"):
        problems.append("audit has failed checks: {}".format(
            ", ".join(audit["failed_checks"][:5])))
    if manifest.get("audit_verdict") != "pass":
        problems.append("manifest audit_verdict is {!r}".format(
            manifest.get("audit_verdict")))
    if manifest.get("audit_failed_checks"):
        problems.append("manifest records failed audit checks: {}".format(
            ", ".join(manifest["audit_failed_checks"][:5])))

    expected = _expected_stream_values(manifest)
    payloads = {}
    for name in ARTIFACT_FILES:
        if name == MANIFEST_NAME:
            continue
        packet_key, text_key = STREAM_PAYLOAD_KEYS[name]
        packets = result.get(packet_key)
        text = result.get(text_key)
        if not isinstance(packets, list) or not isinstance(text, str):
            problems.append("{}: packets/text missing from result".format(name))
            continue
        # Re-derive from the record objects: catches mutation of either side.
        derived = serialize_stream(packets)
        if derived != text:
            problems.append(
                "{}: in-memory stream text does not match its record list".format(
                    name))
        payloads[name] = text
        packet_count = len(packets)
        byte_length = len(text.encode("utf-8"))
        digest = sha256_text(text)
        expectation = expected.get(name) or {}
        if expectation.get("packets") != packet_count:
            problems.append(
                "{}: packets {} != manifest {}".format(
                    name, packet_count, expectation.get("packets")))
        if expectation.get("bytes") != byte_length:
            problems.append(
                "{}: bytes {} != manifest {}".format(
                    name, byte_length, expectation.get("bytes")))
        if expectation.get("sha256") != digest:
            problems.append(
                "{}: sha256 {} != manifest {}".format(
                    name, digest, expectation.get("sha256")))

    if problems:
        raise PacketInputError(
            "refusing to publish an invalid result ({}): {}".format(
                len(problems), "; ".join(problems[:8])))
    payloads[MANIFEST_NAME] = json.dumps(
        result["manifest"], ensure_ascii=False, indent=2) + "\n"
    return payloads


def _write_artifact_file(path, text):
    """Single file write hook (patchable for publication fault injection)."""
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


# Characters that ``str.splitlines()`` treats as line boundaries IN ADDITION to
# "\n". This matters because ``json.dumps(..., ensure_ascii=False)`` escapes the
# C0 controls (so U+001E is written as the six ASCII characters ``\u001e``) but
# leaves U+2028 / U+2029 / U+0085 raw inside string values. A serialized record
# can therefore contain a character that ``str.splitlines()`` mistakes for a
# record terminator, splitting one JSON object into two invalid fragments.
UNICODE_LINE_BOUNDARIES = ("\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x85",
                           "\u2028", "\u2029")


def split_jsonl_records(text):
    """Split a serialized JSONL stream into the records the writer wrote.

    A record is everything between two "\n" characters. ``str.splitlines()``
    must never be used on a record stream: it also breaks on the Unicode line
    boundaries listed in ``UNICODE_LINE_BOUNDARIES``, which a JSON string value
    may legally contain.
    """
    if text == "":
        return []
    parts = text.split("\n")
    if parts[-1] != "":
        raise PacketInputError("serialized stream is not newline-terminated")
    return parts[:-1]


def records_with_unicode_line_boundary(text):
    """Count records containing a non-"\\n" Unicode line boundary character."""
    return sum(1 for record in split_jsonl_records(text)
               if any(char in record for char in UNICODE_LINE_BOUNDARIES))


def _verify_staged_artifact(staging_dir, payloads):
    """Verify the staged artifact set before it is published."""
    problems = []
    for name in ARTIFACT_FILES:
        path = os.path.join(staging_dir, name)
        if not os.path.isfile(path):
            problems.append("{}: missing from staging".format(name))
            continue
        with open(path, "rb") as handle:
            raw = handle.read()
        if raw.decode("utf-8") != payloads[name]:
            problems.append("{}: staged bytes differ from payload".format(name))
        if len(raw) != len(payloads[name].encode("utf-8")):
            problems.append("{}: staged byte length differs".format(name))
        if hashlib.sha256(raw).hexdigest() != sha256_text(payloads[name]):
            problems.append("{}: staged sha256 differs".format(name))

    manifest_path = os.path.join(staging_dir, MANIFEST_NAME)
    if os.path.isfile(manifest_path):
        try:
            with open(manifest_path, encoding="utf-8") as handle:
                staged_manifest = json.load(handle)
        except ValueError as exc:
            staged_manifest = None
            problems.append("{}: staged manifest is not JSON ({})".format(
                MANIFEST_NAME, exc))
        if isinstance(staged_manifest, dict):
            streams = staged_manifest.get("streams") or {}
            for name in ARTIFACT_FILES:
                if name == MANIFEST_NAME or name not in payloads:
                    continue
                expected = streams.get(name) or {}
                payload = payloads[name]
                try:
                    records = split_jsonl_records(payload)
                except PacketInputError as exc:
                    problems.append("{}: {}".format(name, exc))
                    continue
                if len(records) != expected.get("packets"):
                    problems.append(
                        "{}: staged record count {} != manifest packets {}".format(
                            name, len(records), expected.get("packets")))
                if len(payload.encode("utf-8")) != expected.get("bytes"):
                    problems.append(
                        "{}: payload bytes {} != manifest bytes {}".format(
                            name, len(payload.encode("utf-8")),
                            expected.get("bytes")))
                if sha256_text(payload) != expected.get("sha256"):
                    problems.append(
                        "{}: payload sha256 != manifest sha256".format(name))
                expected_track = ARTIFACT_STREAM_TRACKS.get(name)
                for record in records:
                    if not record.strip():
                        problems.append(
                            "{}: staged record is blank".format(name))
                        break
                    try:
                        record_object = json.loads(record)
                    except ValueError:
                        problems.append(
                            "{}: staged record is not JSON".format(name))
                        break
                    if (expected_track is not None
                            and record_object.get("track") != expected_track):
                        problems.append(
                            "{}: staged packet track {!r} != {!r}".format(
                                name, record_object.get("track"),
                                expected_track))
                        break
                    if (name in ARTIFACT_INDEX_STREAMS
                            and (record_object.get("record_type")
                                 != REVIEW_UNIVERSE_RECORD_TYPE
                                 or record_object.get("review_identity")
                                 != record_object.get("verse_key"))):
                        problems.append(
                            "{}: staged index record is malformed".format(name))
                        break

    if problems:
        raise PacketInputError(
            "staged artifact failed verification ({}): {}".format(
                len(problems), "; ".join(problems[:8])))
    return True


def write_artifacts(result, out_dir, require_pins=True):
    """Publish the production artifact set atomically.

    All five files (the Track A stream, the Track B stream, the Track C owner
    overlay, the review-universe index and the manifest) are written into a
    temporary sibling directory, verified in full (byte lengths, SHA-256,
    record/packet counts under the ``"\\n"`` record rule, packet tracks, overlay
    ``track``, index record type and review identity, manifest self-consistency),
    and only then is the completed directory renamed onto the requested
    destination. Any failure removes the staging directory and leaves the
    destination absent. An existing destination is never overwritten or merged
    into.

    ``require_pins=False`` is the explicit test-only path for synthetic results;
    production callers must use the default.
    """
    if not out_dir:
        raise PacketInputError(
            "publication requires an explicit destination directory")
    destination = os.path.abspath(out_dir)
    payloads = validate_publishable_result(result, require_pins=require_pins)

    if os.path.lexists(destination):
        raise PacketInputError(
            "refusing to publish over an existing destination: {}".format(
                destination))
    parent = os.path.dirname(destination) or "."
    if not os.path.isdir(parent):
        raise PacketInputError(
            "destination parent directory does not exist: {}".format(parent))

    staging_dir = tempfile.mkdtemp(prefix=STAGING_PREFIX, dir=parent)
    published = False
    try:
        for name in ARTIFACT_FILES:
            _write_artifact_file(os.path.join(staging_dir, name),
                                 payloads[name])
        _verify_staged_artifact(staging_dir, payloads)
        # Atomic publication of the complete artifact set.
        os.rename(staging_dir, destination)
        published = True
    finally:
        if not published and os.path.isdir(staging_dir):
            shutil.rmtree(staging_dir, ignore_errors=True)
    return [os.path.join(destination, name) for name in ARTIFACT_FILES]


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Build deterministic GD Bible revision review packets "
            "(Track A existing change audit + Track B new change tier 1 + "
            "Track C owner-specified review candidates published as the owner "
            "overlay and the unique review-universe index). "
            "Default mode is audit-only and writes nothing."))
    parser.add_argument("--audit-only", action="store_true",
                        help="compute and audit packets without writing (default)")
    parser.add_argument("--write", action="store_true",
                        help="publish the production packet artifact; requires "
                             "an explicit --out-dir")
    parser.add_argument("--out-dir", default=None,
                        help="explicit destination directory for --write "
                             "(required; never defaulted)")
    parser.add_argument("--evidence-bridge-dir", default=None)
    parser.add_argument("--standard-kjv", default=None)
    parser.add_argument("--current-gd", default=None)
    parser.add_argument("--transformation-manifest", default=None)
    parser.add_argument("--coordinates", default=None)
    parser.add_argument("--owner-inputs", default=None,
                        help="path to the durable owner review inputs "
                             "(default: {})".format(OWNER_INPUTS_PATH))
    parser.add_argument("--allow-unpinned", action="store_true",
                        help="explicit test mode: do not enforce frozen pins")
    parser.add_argument("--generated-at", default=None)
    parser.add_argument("--audit-report", default=None,
                        help="optional path for the audit report JSON")
    parser.add_argument("--quiet", action="store_true")
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    enforce_pins = not args.allow_unpinned

    # Production intent is validated BEFORE any input is read or written.
    if args.write:
        if not args.out_dir:
            sys.stderr.write(
                "REFUSED: --write requires an explicit --out-dir; refusing to "
                "choose a destination automatically.\n")
            return 2
        if not enforce_pins:
            sys.stderr.write(
                "REFUSED: --write with --allow-unpinned would emit an unpinned "
                "production artifact; production write must be pinned.\n")
            return 2

    paths = resolve_input_paths(
        evidence_bridge_dir=args.evidence_bridge_dir,
        standard_kjv_asset=args.standard_kjv,
        current_gd_asset=args.current_gd,
        transformation_manifest=args.transformation_manifest,
        owner_inputs=args.owner_inputs,
    )
    try:
        result = run_build(paths, enforce_pins=enforce_pins,
                           coordinates_path=args.coordinates,
                           generated_at=args.generated_at)
    except (PacketInputError, PacketBuildError) as exc:
        sys.stderr.write("ERROR: {}\n".format(exc))
        return 2

    if args.audit_report:
        with open(args.audit_report, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(result["audit"], ensure_ascii=False, indent=2))
            handle.write("\n")

    if not args.quiet:
        sys.stdout.write(json.dumps(result["audit"], ensure_ascii=False, indent=2))
        sys.stdout.write("\n")

    if args.write:
        try:
            written = write_artifacts(result, args.out_dir)
        except (PacketInputError, PacketBuildError) as exc:
            sys.stderr.write("ERROR: {}\n".format(exc))
            return 2
        sys.stderr.write("published:\n" + "\n".join(written) + "\n")
    else:
        sys.stderr.write(
            "audit-only: no packet artifact written "
            "(pass --write to emit production packets)\n")
    return 0 if result["audit"]["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
