"""Focused tests for gd_bible_revision_review_packets (Review Packets V1).

Run:
    python3 -m unittest tests.test_gd_bible_revision_review_packets -v
    GD_RUN_FULL_PACKET_AUDIT=1 python3 -m unittest \
        tests.test_gd_bible_revision_review_packets -v

These tests cover the deterministic packet layer only. They assert no Bible
translation decision, invoke no model, and modify no Bible or archive file.

Most tests run against a synthetic fixture whose *shape* matches production
(the real committed 66-book coordinate table) but whose Bible text, evidence
and transformation manifest are generated. The heavy end-to-end audit against
the frozen production inputs is gated behind GD_RUN_FULL_PACKET_AUDIT=1.
"""

import contextlib
import copy
import hashlib
import inspect
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

import gd_bible_revision_review_packets as PACKETS  # noqa: E402

_COORD_BOOKS = None


def coord_books():
    global _COORD_BOOKS
    if _COORD_BOOKS is None:
        _COORD_BOOKS = PACKETS.load_coordinate_books()
    return _COORD_BOOKS


def book_name(book_id):
    return coord_books()[book_id - 1]["book"]


def canon(verse_key):
    book_id, chapter, verse = PACKETS.parse_verse_key(verse_key)
    return "{} {}:{}".format(book_name(book_id), chapter, verse)


def finding_uid(seed):
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Synthetic fixture (production-shaped, tiny content)
# --------------------------------------------------------------------------

FIXTURE_MANIFEST = {
    "manifestVersion": "1.0",
    "standardAsset": "assets/bible/en_kjv.json",
    "customAsset": "assets/bible/kjv_modified.json",
    "rules": [
        {
            "ruleId": "R001",
            "description": "duplicate reference entries on one verse",
            "standardToken": "Ghost",
            "customToken": "Spirit",
            "caseSensitive": True,
            "tokenCountBefore": 1,
            "tokenCountAfter": 1,
            "applicationCount": 3,
            "references": ["Genesis 1:2", "Genesis 1:2", "Genesis 1:1"],
        },
        {
            "ruleId": "R002",
            "description": "second rule on the same verse",
            "standardPhrase": "Holy Ghost",
            "customPhrase": "Holy Spirit",
            "caseSensitive": True,
            "tokenCountBefore": 2,
            "tokenCountAfter": 2,
            "applicationCount": 1,
            "references": ["Genesis 1:1"],
        },
        {
            "ruleId": "R003",
            "description": "changed verse carrying archive evidence",
            "standardToken": "charity",
            "customToken": "love",
            "caseSensitive": True,
            "tokenCountBefore": 1,
            "tokenCountAfter": 1,
            "applicationCount": 1,
            "references": ["Genesis 1:5"],
        },
        {
            "ruleId": "R004",
            "description": "changed verse with no mapped archive evidence",
            "standardToken": "prevent",
            "customToken": "precede",
            "caseSensitive": False,
            "tokenCountBefore": 1,
            "tokenCountAfter": 1,
            "applicationCount": 1,
            "references": ["Exodus 1:1"],
        },
    ],
}

FIXTURE_SPECS = (
    [("b1:c1:v1", "terminology")]
    + [("b1:c1:v5", "wording"), ("b1:c1:v5", "capitalization")]
    + [("b1:c1:v3", "translation")] * 20
    + [("b1:c1:v3", "scripture")] * 3
    + [("b1:c1:v4", "terminology")] * 19
    + [("b1:c1:v6", "scripture")] * 25
    + [("b2:c1:v1", "translation")] * 40
)

# Verses whose current GD text differs from the standard text in the fixture.
CURRENT_OVERRIDES = {
    (1, 1, 1): "And God said, Let there be light: and there was light. [changed]",
    (1, 1, 2): "And the earth became without form, and void. [changed]",
    (1, 1, 5): "And God called the light Day. [changed]",
    (2, 1, 1): "Now these are the names. [changed]",
}


def default_text(book, chapter, verse):
    return "synthetic {} {}:{}".format(book, chapter, verse)


def make_asset(overrides=None):
    overrides = overrides or {}
    asset = []
    for entry in coord_books():
        book_id = entry["book_id"]
        chapters = []
        for chapter_index, count in enumerate(entry["chapter_verse_counts"], start=1):
            verses = []
            for verse_index in range(1, count + 1):
                key = (book_id, chapter_index, verse_index)
                verses.append(overrides.get(key, default_text(
                    entry["book"], chapter_index, verse_index)))
            chapters.append(verses)
        asset.append({"name": entry["book"], "abbrev": entry.get("source_abbrev"),
                      "chapters": chapters})
    return asset


def make_index_row(verse_key, uid, topic, chunk_id="c0000",
                   generation="fresh-2026-full-archive", final_pass="screen",
                   doc_sha=None):
    book_id, chapter, verse = PACKETS.parse_verse_key(verse_key)
    canonical = canon(verse_key)
    return {
        "book": book_name(book_id),
        "book_id": book_id,
        "canonical": canonical,
        "chapter": chapter,
        "chunk_id": chunk_id,
        "engine_version": "1.5.0",
        "final_pass": final_pass,
        "finding_topic": topic,
        "finding_uid": uid,
        "mapper_version": "1.0.0",
        "raw_refs": [canonical],
        "research_generation": generation,
        "schema_version": "gd-bible-revision-reference-map/1",
        "source_document_sha256": doc_sha or hashlib.sha256(
            ("doc-" + verse_key).encode("utf-8")).hexdigest(),
        "verse": verse,
        "verse_key": verse_key,
    }


def make_record(verse_key, uid, topic, chunk_id="c0000",
                generation="fresh-2026-full-archive", final_pass="screen",
                doc_sha=None, note="fixture note", confidence="high"):
    canonical = canon(verse_key)
    doc_sha = doc_sha or hashlib.sha256(
        ("doc-" + verse_key).encode("utf-8")).hexdigest()
    document = "PCG/Fixture/{}.doc".format(verse_key.replace(":", "-"))
    return {
        "duplicate_mappings_removed": 0,
        "engine_version": "1.5.0",
        "expanded_mapping_count": 1,
        "finding": {
            "char_end": 40, "char_start": 20, "confidence": confidence,
            "finding_index": 0, "note": note, "occurrences": 1,
            "provenance": "in_chunk_exact", "quote": "fixture quote for " + verse_key,
            "speaker": "other", "topic": topic,
        },
        "finding_uid": uid,
        "has_verse_mapping": True,
        "identity": {
            "chunk_id": chunk_id, "final_pass": final_pass,
            "final_pass_key": "f" * 23, "finding_char_end": 40,
            "finding_char_start": 20, "finding_index": 0,
            "finding_quote_sha256": hashlib.sha256(
                ("fixture quote for " + verse_key).encode("utf-8")).hexdigest(),
            "finding_topic": topic, "identity_version": "1.0.0",
            "research_generation": generation, "source_document": document,
            "source_document_sha256": doc_sha,
        },
        "mapped_verse_count": 1,
        "mapped_verse_keys": [verse_key],
        "mapper_version": "1.0.0",
        "outcomes": [{
            "canonical_verse_count": 1, "canonical_verse_keys": [verse_key],
            "context": None,
            "engine_rows": [{
                "canonical": canonical, "canonical_issues": [],
                "canonical_status": "asserted_valid", "citation_context": "explicit",
                "granularity": "verse", "raw_match": canonical,
                "reference_key": verse_key, "resolution_status": "syntactically_parsed",
            }],
            "normalized_references": [],
            "raw": canonical, "raw_index": 0,
            "raw_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            "reason": "", "status": "mapped_verse",
            "unexplained_residual": "", "unexplained_symbols": [],
            "unexplained_tokens": [],
        }],
        "passage": {
            "chunk_id": chunk_id, "current_path": document,
            "final_pass": final_pass, "final_pass_key": "f" * 23,
            "research_generation": generation,
            "source_collection": "PCG/Fixture", "source_document": document,
            "source_document_sha256": doc_sha,
        },
        "raw_reference_count": 1,
        "raw_scripture_refs": [canonical],
        "schema_version": "gd-bible-revision-reference-map/1",
        "status_counts": {"mapped_verse": 1},
        "verse_key_sources": [{"raw_refs": [canonical], "verse_key": verse_key}],
    }


def write_json(path, obj):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(obj, ensure_ascii=False))
    return path


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(PACKETS.dumps(row) + "\n")
    return path


def build_fixture(root, drop_record_seed=None, duplicate_index_seed=None,
                  specs=None, current_asset=None, extra_current_overrides=None):
    """Create a complete synthetic input set; return the resolved path map."""
    os.makedirs(root, exist_ok=True)
    specs = list(FIXTURE_SPECS if specs is None else specs)

    overlays = dict(CURRENT_OVERRIDES)
    if extra_current_overrides:
        overlays.update(extra_current_overrides)
    standard = make_asset()
    current = make_asset(overrides=overlays)
    if current_asset is not None:
        current = current_asset
    write_json(os.path.join(root, "en_kjv.json"), standard)
    write_json(os.path.join(root, "kjv_modified.json"), current)
    write_json(os.path.join(root, "TRANSFORMATION_MANIFEST.json"), FIXTURE_MANIFEST)

    index_rows = []
    records = []
    for position, (verse_key, topic) in enumerate(specs):
        uid = finding_uid("{}|{}|{}".format(verse_key, topic, position))
        index_rows.append(make_index_row(verse_key, uid, topic))
        records.append(make_record(verse_key, uid, topic))
        if duplicate_index_seed is not None and verse_key == duplicate_index_seed[0] \
                and topic == duplicate_index_seed[1]:
            index_rows.append(make_index_row(verse_key, uid, topic))

    if drop_record_seed is not None:
        records = [r for r in records if r["finding_uid"] != drop_record_seed]

    write_jsonl(os.path.join(root, "verse_evidence_index.jsonl"), index_rows)
    write_jsonl(os.path.join(root, "finding_reference_map.jsonl"), records)
    write_jsonl(os.path.join(root, "reference_anomalies.jsonl"), [])
    write_json(os.path.join(root, "manifest.json"), {
        "artifact": "gd_bible_revision_reference_map",
        "schema_version": "gd-bible-revision-reference-map/1",
        "inputs_pinned": True,
        "counts": {},
    })

    paths = {
        "evidence_bridge_dir": root,
        "verse_evidence_index": os.path.join(root, "verse_evidence_index.jsonl"),
        "finding_reference_map": os.path.join(root, "finding_reference_map.jsonl"),
        "reference_anomalies": os.path.join(root, "reference_anomalies.jsonl"),
        "evidence_bridge_manifest": os.path.join(root, "manifest.json"),
        "standard_kjv_asset": os.path.join(root, "en_kjv.json"),
        "current_gd_asset": os.path.join(root, "kjv_modified.json"),
        "transformation_manifest": os.path.join(root, "TRANSFORMATION_MANIFEST.json"),
        "owner_inputs": write_owner_inputs(root),
    }
    return paths


def hash_tree(root):
    digests = {}
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            with open(path, "rb") as handle:
                digests[os.path.relpath(path, root)] = hashlib.sha256(
                    handle.read()).hexdigest()
    return digests


def make_packet(track, verse_key):
    book_id, chapter, verse = PACKETS.parse_verse_key(verse_key)
    return {
        "schema_version": PACKETS.PACKET_SCHEMA_VERSION,
        "packet_builder_version": PACKETS.PACKET_BUILDER_VERSION,
        "track": track,
        "track_name": (PACKETS.TRACK_A_NAME if track == PACKETS.TRACK_A
                       else PACKETS.TRACK_B_NAME),
        "priority_tier": (PACKETS.PRIORITY_TIER_A if track == PACKETS.TRACK_A
                          else PACKETS.PRIORITY_TIER_B),
        "verse_key": verse_key,
        "canonical_reference": canon(verse_key),
        "book_id": book_id,
        "book": book_name(book_id),
        "chapter": chapter,
        "verse": verse,
        "direct_archive_verse_evidence": False,
        "evidence": [],
    }


def make_publishable_result(a_keys=("b1:c1:v1", "b1:c1:v2"),
                            b_keys=("b2:c1:v1",), pinned=True,
                            packets_a=None, packets_b=None):
    """A small, fully self-consistent result for publication-path tests."""
    if packets_a is None:
        packets_a = [make_packet(PACKETS.TRACK_A, key) for key in a_keys]
    if packets_b is None:
        packets_b = [make_packet(PACKETS.TRACK_B, key) for key in b_keys]
    text_a = PACKETS.serialize_stream(packets_a)
    text_b = PACKETS.serialize_stream(packets_b)
    # One owner overlay pointer onto a verse already in Track A: exercises the
    # overlay + universe streams without needing a Bible text index.
    overlay = PACKETS.build_owner_overlay(
        [make_resolved_candidate(packets_a[0]["verse_key"])],
        packets_a, packets_b, None, None, None)
    universe = PACKETS.build_review_universe_index(packets_a, packets_b, overlay)
    text_overlay = PACKETS.serialize_stream(overlay)
    text_universe = PACKETS.serialize_stream(universe)
    manifest = {
        "artifact": "gd_bible_revision_review_packets",
        "packet_builder_version": PACKETS.PACKET_BUILDER_VERSION,
        "packet_schema_version": PACKETS.PACKET_SCHEMA_VERSION,
        "inputs_pinned": bool(pinned),
        "audit_verdict": "pass",
        "audit_failed_checks": [],
        "streams": {
            PACKETS.TRACK_A_STREAM: {
                "packets": len(packets_a),
                "bytes": len(text_a.encode("utf-8")),
                "sha256": PACKETS.sha256_text(text_a),
            },
            PACKETS.TRACK_B_STREAM: {
                "packets": len(packets_b),
                "bytes": len(text_b.encode("utf-8")),
                "sha256": PACKETS.sha256_text(text_b),
            },
            PACKETS.OWNER_OVERLAY_STREAM: {
                "packets": len(overlay),
                "bytes": len(text_overlay.encode("utf-8")),
                "sha256": PACKETS.sha256_text(text_overlay),
            },
            PACKETS.REVIEW_UNIVERSE_STREAM: {
                "packets": len(universe),
                "bytes": len(text_universe.encode("utf-8")),
                "sha256": PACKETS.sha256_text(text_universe),
            },
        },
    }
    return {
        "packets_a": packets_a,
        "packets_b": packets_b,
        "owner_overlay": overlay,
        "review_universe": universe,
        "stream_a_text": text_a,
        "stream_b_text": text_b,
        "owner_overlay_text": text_overlay,
        "review_universe_text": text_universe,
        "manifest": manifest,
        "audit": {"verdict": "pass", "failed_checks": []},
    }


def make_resolved_candidate(verse_key, candidate_id="owner-test-01",
                            text="synthetic owner note"):
    """A resolved-candidate record shaped exactly like the resolver's output."""
    book_id, chapter, verse = PACKETS.parse_verse_key(verse_key)
    reference = canon(verse_key)
    return {
        "candidate_id": candidate_id,
        "candidate_category": "modernization",
        "owner_reference_raw": reference,
        "owner_reference_parser_input": reference,
        "owner_reference_normalization": None,
        "owner_reference_raw_parser_status": "mapped_verse",
        "canonical_reference": reference,
        "verse_key": verse_key,
        "book_id": book_id,
        "book": book_name(book_id),
        "chapter": chapter,
        "verse": verse,
        "owner_note_occurrences": [{"occurrence": 1, "text": text}],
        "owner_note_occurrence_count": 1,
        "duplicate_occurrence_count": 0,
        "proposed_change": {"kind": "word_replacement", "from": "alpha",
                            "to": ["beta"], "alternatives_preserved": False,
                            "selection": "single"},
        "owner_question": None,
        "candidate_status": PACKETS.OWNER_CANDIDATE_STATUS,
        "provenance_class": PACKETS.OWNER_PROVENANCE_CLASS,
        "accepted_translation": False,
        "flags": {"owner_cites_external_translation": False,
                  "external_translation_is_evidence": False},
        "context_only_references": [],
        "context_only_verse_keys": [],
        "resolution_note": None,
    }


def write_owner_inputs(root, candidates=None, policies=None):
    """A minimal but structurally valid owner-input artifact for synthetic runs."""
    if candidates is None:
        candidates = [{
            "candidate_id": "owner-test-01",
            "candidate_category": "modernization",
            "owner_reference_raw": "Genesis 1:1",
            "owner_reference_parser_input": "Genesis 1:1",
            "owner_reference_normalization": None,
            "owner_reference_raw_parser_status": "mapped_verse",
            "canonical_reference": "Genesis 1:1",
            "verse_key": "b1:c1:v1",
            "owner_note_occurrences": [
                {"occurrence": 1, "text": "synthetic owner note about Genesis 1:1"}],
            "proposed_change": {"kind": "word_replacement", "from": "alpha",
                                "to": ["beta"], "alternatives_preserved": False,
                                "selection": "single"},
            "owner_question": None,
            "candidate_status": PACKETS.OWNER_CANDIDATE_STATUS,
            "provenance_class": PACKETS.OWNER_PROVENANCE_CLASS,
            "accepted_translation": False,
            "flags": {"owner_cites_external_translation": False,
                      "external_translation_is_evidence": False},
            "context_only_references": [],
            "context_only_verse_keys": [],
            "resolution_note": None,
        }]
    if policies is None:
        policies = [{
            "policy_id": "style-test-01",
            "policy_scope": "bible_wide_typographic_style",
            "title": "Synthetic style policy",
            "owner_note_raw": "synthetic style note",
            "owner_intent": "synthetic style intent",
            "examples": [{"from": "x", "to": "X", "condition": "synthetic"}],
            "requires_contextual_classification": True,
            "blind_replacement_forbidden": True,
            "status": "review_candidate",
            "approved": False,
            "implementation_status": "not_implemented",
            "applied": False,
        }]
    return write_json(os.path.join(root, "gd_bible_owner_review_inputs.json"), {
        "artifact": PACKETS.OWNER_INPUTS_ARTIFACT,
        "schema_version": PACKETS.OWNER_INPUTS_SCHEMA_VERSION,
        "recorded": "2026-01-01",
        "authority": "owner_specified",
        "provenance_class": PACKETS.OWNER_PROVENANCE_CLASS,
        "statements": {"authority": "synthetic"},
        "verse_candidates": candidates,
        "style_policies": policies,
    })


def staging_entries(parent):
    return [name for name in os.listdir(parent)
            if name.startswith(PACKETS.STAGING_PREFIX)]


def build_small_fixture(root):
    """Alternate-coordinate fixture: 2 books, small assets, one changed verse."""
    os.makedirs(root, exist_ok=True)
    books = [dict(entry) for entry in SMALL_BOOKS]
    coordinates_path = write_json(os.path.join(root, "coordinates.json"),
                                 {"artifact": "synthetic", "artifact_version": "1.0",
                                  "books": books})
    write_json(os.path.join(root, "en_kjv.json"), small_asset())
    write_json(os.path.join(root, "kjv_modified.json"), small_asset("!"))
    manifest = {"rules": [{
        "ruleId": "RS1", "description": "synthetic", "applicationCount": 1,
        "standardToken": "g1v1", "customToken": "g1v1!",
        "caseSensitive": True, "tokenCountBefore": 1, "tokenCountAfter": 1,
        "references": ["Genesis 1:1"],
    }]}
    write_json(os.path.join(root, "TRANSFORMATION_MANIFEST.json"), manifest)
    uid = finding_uid("small|b1:c1:v1|translation")
    write_jsonl(os.path.join(root, "verse_evidence_index.jsonl"),
                [make_index_row("b1:c1:v1", uid, "translation")])
    write_jsonl(os.path.join(root, "finding_reference_map.jsonl"),
                [make_record("b1:c1:v1", uid, "translation")])
    write_jsonl(os.path.join(root, "reference_anomalies.jsonl"), [])
    write_json(os.path.join(root, "manifest.json"), {
        "artifact": "gd_bible_revision_reference_map",
        "schema_version": "gd-bible-revision-reference-map/1",
        "inputs_pinned": True, "counts": {}})
    paths = {
        "evidence_bridge_dir": root,
        "verse_evidence_index": os.path.join(root, "verse_evidence_index.jsonl"),
        "finding_reference_map": os.path.join(root, "finding_reference_map.jsonl"),
        "reference_anomalies": os.path.join(root, "reference_anomalies.jsonl"),
        "evidence_bridge_manifest": os.path.join(root, "manifest.json"),
        "standard_kjv_asset": os.path.join(root, "en_kjv.json"),
        "current_gd_asset": os.path.join(root, "kjv_modified.json"),
        "transformation_manifest": os.path.join(root, "TRANSFORMATION_MANIFEST.json"),
        "owner_inputs": write_owner_inputs(root),
    }
    return paths, coordinates_path


# --------------------------------------------------------------------------
# Coordinate / Bible text
# --------------------------------------------------------------------------


SMALL_BOOKS = [
    {"book_id": 1, "book": "Genesis", "source_abbrev": "gn",
     "chapter_count": 2, "chapter_verse_counts": [3, 2]},
    {"book_id": 2, "book": "Exodus", "source_abbrev": "ex",
     "chapter_count": 1, "chapter_verse_counts": [2]},
]


def small_asset(offset=""):
    return [
        {"name": "Genesis", "abbrev": "gn",
         "chapters": [["g1v1" + offset, "g1v2" + offset, "g1v3" + offset],
                      ["g2v1" + offset, "g2v2" + offset]]},
        {"name": "Exodus", "abbrev": "ex",
         "chapters": [["e1v1" + offset, "e1v2" + offset]]},
    ]


class BibleCoordinateTests(unittest.TestCase):
    def setUp(self):
        self.index = PACKETS.BibleTextIndex(
            small_asset(), small_asset(), [dict(b) for b in SMALL_BOOKS])

    def test_deterministic_verse_retrieval(self):
        self.assertEqual(self.index.lookup(1, 1, 1), ("g1v1", "g1v1"))
        self.assertEqual(self.index.lookup(2, 1, 2), ("e1v2", "e1v2"))
        self.assertEqual(self.index.lookup_verse_key("b1:c2:v2"), ("g2v2", "g2v2"))
        self.assertEqual(self.index.book_name(2), "Exodus")

    def test_standard_and_current_text_preserved_verbatim(self):
        index = PACKETS.BibleTextIndex(
            small_asset(), small_asset("!"), [dict(b) for b in SMALL_BOOKS])
        standard, current = index.lookup(1, 1, 1)
        self.assertEqual(standard, "g1v1")
        self.assertEqual(current, "g1v1!")
        self.assertNotEqual(standard, current)

    def test_book_out_of_range_fails_closed(self):
        for book_id in (0, -1, 67, 999):
            with self.assertRaises(PACKETS.CoordinateError):
                self.index.lookup(book_id, 1, 1)

    def test_book_absent_from_coordinate_table_fails_closed(self):
        with self.assertRaises(PACKETS.CoordinateError):
            self.index.lookup(3, 1, 1)

    def test_non_integer_coordinate_fails_closed(self):
        with self.assertRaises(PACKETS.CoordinateError):
            self.index.lookup(1, "1", 1)
        with self.assertRaises(PACKETS.CoordinateError):
            self.index.lookup(1, 1, None)

    def test_chapter_out_of_range_fails_closed(self):
        with self.assertRaises(PACKETS.CoordinateError):
            self.index.lookup(1, 3, 1)
        with self.assertRaises(PACKETS.CoordinateError):
            self.index.lookup(1, 0, 1)

    def test_verse_out_of_range_fails_closed(self):
        with self.assertRaises(PACKETS.CoordinateError):
            self.index.lookup(1, 1, 4)
        with self.assertRaises(PACKETS.CoordinateError):
            self.index.lookup(1, 2, 3)

    def test_assets_must_share_the_required_coordinate(self):
        trimmed = small_asset()
        trimmed[0]["chapters"][0] = trimmed[0]["chapters"][0][:2]
        with self.assertRaises(PACKETS.CoordinateError):
            PACKETS.BibleTextIndex(
                small_asset(), trimmed, [dict(b) for b in SMALL_BOOKS])

    def test_asset_book_name_mismatch_fails_closed(self):
        with self.assertRaises(PACKETS.CoordinateError):
            PACKETS.BibleTextIndex(
                small_asset(), small_asset(), [
                    {"book_id": 1, "book": "Wrong", "chapter_verse_counts": [3, 2]},
                    {"book_id": 2, "book": "Exodus", "chapter_verse_counts": [2]},
                ])

    def test_non_string_verse_fails_closed(self):
        broken = small_asset()
        broken[0]["chapters"][0][0] = 17
        with self.assertRaises(PACKETS.PacketBuildError):
            PACKETS.BibleTextIndex(
                broken, small_asset(), [dict(b) for b in SMALL_BOOKS])


# --------------------------------------------------------------------------
# Transformation manifest parsing
# --------------------------------------------------------------------------


class TransformationManifestTests(unittest.TestCase):
    def test_reference_parsing_and_counts(self):
        summary, verse_rules = PACKETS.parse_transformation_manifest(FIXTURE_MANIFEST)
        self.assertEqual(summary["transformation_rules"], 4)
        self.assertEqual(summary["transformation_applications"], 6)
        self.assertEqual(summary["manifest_reference_entries"], 6)
        self.assertEqual(summary["unique_changed_verses"], 4)
        self.assertEqual(
            sorted(verse_rules),
            ["b1:c1:v1", "b1:c1:v2", "b1:c1:v5", "b2:c1:v1"])

    def test_multiple_rules_on_one_verse_preserved_in_order(self):
        _summary, verse_rules = PACKETS.parse_transformation_manifest(FIXTURE_MANIFEST)
        self.assertEqual([r["ruleId"] for r in verse_rules["b1:c1:v1"]],
                         ["R001", "R002"])

    def test_duplicate_manifest_reference_entries_preserved(self):
        _summary, verse_rules = PACKETS.parse_transformation_manifest(FIXTURE_MANIFEST)
        rule = verse_rules["b1:c1:v2"][0]
        self.assertEqual(rule["manifest_reference_strings"],
                         ["Genesis 1:2", "Genesis 1:2"])
        self.assertEqual(rule["rule_reference_entry_count"], 3)
        self.assertEqual(rule["duplicate_reference_entry_count"], 1)

    def test_optional_fields_only_when_present(self):
        _summary, verse_rules = PACKETS.parse_transformation_manifest(FIXTURE_MANIFEST)
        self.assertIn("standardToken", verse_rules["b1:c1:v2"][0])
        self.assertNotIn("standardPhrase", verse_rules["b1:c1:v2"][0])
        self.assertIn("standardPhrase", verse_rules["b1:c1:v1"][1])
        self.assertNotIn("standardToken", verse_rules["b1:c1:v1"][1])

    def test_unresolvable_reference_fails_closed(self):
        manifest = {"rules": [{
            "ruleId": "RX", "description": "bad", "applicationCount": 1,
            "references": ["Genesis 99:1"],
        }]}
        with self.assertRaises(PACKETS.PacketBuildError):
            PACKETS.parse_transformation_manifest(manifest)

    def test_range_reference_resolving_to_many_verses_fails_closed(self):
        manifest = {"rules": [{
            "ruleId": "RX", "description": "range", "applicationCount": 1,
            "references": ["Genesis 1:1-2"],
        }]}
        with self.assertRaises(PACKETS.PacketBuildError):
            PACKETS.parse_transformation_manifest(manifest)

    def test_application_count_below_distinct_references_fails_closed(self):
        manifest = {"rules": [{
            "ruleId": "RX", "description": "bad count", "applicationCount": 1,
            "references": ["Genesis 1:1", "Genesis 1:2"],
        }]}
        with self.assertRaises(PACKETS.PacketBuildError):
            PACKETS.parse_transformation_manifest(manifest)

    def test_application_count_may_exceed_reference_entries(self):
        manifest = {"rules": [{
            "ruleId": "RX", "description": "token-level count", "applicationCount": 55,
            "references": ["Genesis 1:1", "Genesis 1:2"],
        }]}
        summary, _verse_rules = PACKETS.parse_transformation_manifest(manifest)
        self.assertEqual(summary["transformation_applications"], 55)
        self.assertEqual(summary["manifest_reference_entries"], 2)


# --------------------------------------------------------------------------
# Evidence loading / join
# --------------------------------------------------------------------------


class EvidenceJoinTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="gd_pkt_ev_")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.paths = build_fixture(self.root)

    def test_index_rows_and_unique_verses(self):
        index = PACKETS.load_verse_evidence_index(self.paths["verse_evidence_index"])
        self.assertEqual(index["rows"], len(FIXTURE_SPECS))
        self.assertEqual(index["pairs"], len(FIXTURE_SPECS))
        self.assertEqual(index["duplicate_pairs"], 0)
        self.assertEqual(index["unique_verses"], 6)

    def test_duplicate_finding_uid_deduped_per_verse(self):
        root = tempfile.mkdtemp(prefix="gd_pkt_dup_")
        self.addCleanup(shutil.rmtree, root, True)
        paths = build_fixture(root, duplicate_index_seed=("b1:c1:v5", "wording"))
        index = PACKETS.load_verse_evidence_index(paths["verse_evidence_index"])
        self.assertEqual(index["duplicate_pairs"], 1)
        self.assertEqual(len(index["by_verse"]["b1:c1:v5"]), 2)
        result = PACKETS.run_build(paths, enforce_pins=False,
                                   generated_at="2026-01-01T00:00:00+00:00")
        packet = next(p for p in result["packets_a"] if p["verse_key"] == "b1:c1:v5")
        self.assertEqual(len(packet["evidence"]), 2)
        uids = [item["finding_uid"] for item in packet["evidence"]]
        self.assertEqual(len(uids), len(set(uids)))

    def test_missing_finding_uid_fails_closed(self):
        root = tempfile.mkdtemp(prefix="gd_pkt_missing_")
        self.addCleanup(shutil.rmtree, root, True)
        dropped = finding_uid("b1:c1:v5|wording|1")
        paths = build_fixture(root, drop_record_seed=dropped)
        with self.assertRaises(PACKETS.PacketBuildError) as ctx:
            PACKETS.run_build(paths, enforce_pins=False)
        self.assertIn("missing_needed_uids", str(ctx.exception))

    def test_finding_record_join_preserves_evidence(self):
        record = make_record("b1:c1:v1", finding_uid("u"), "terminology")
        association = {"finding_topic": "terminology", "final_pass": "screen",
                       "research_generation": "fresh-2026-full-archive",
                       "chunk_id": "c0000",
                       "raw_refs": ["Genesis 1:1"],
                       "source_document_sha256": record["identity"]["source_document_sha256"]}
        problems = []
        item = PACKETS.build_evidence_item(
            "u", record, association, problems)
        self.assertEqual(problems, [])
        self.assertEqual(item["finding_uid"], "u")
        self.assertEqual(item["finding_quote"], record["finding"]["quote"])
        self.assertEqual(item["finding_note"], record["finding"]["note"])
        self.assertEqual(item["finding_confidence"], "high")
        self.assertEqual(item["finding_provenance"], "in_chunk_exact")
        self.assertEqual(item["source_document"], record["passage"]["source_document"])
        self.assertEqual(item["source_document_sha256"],
                         record["identity"]["source_document_sha256"])
        self.assertEqual(item["chunk_id"], "c0000")
        self.assertEqual(item["research_generation"], "fresh-2026-full-archive")
        self.assertEqual(item["final_pass"], "screen")
        self.assertEqual(item["raw_scripture_refs"], ["Genesis 1:1"])
        self.assertEqual(item["verse_raw_refs"], ["Genesis 1:1"])
        self.assertEqual(item["mapped_verse_keys"], ["b1:c1:v1"])
        self.assertEqual(item["provenance"]["association"],
                         "verse_evidence_index:verse_key+finding_uid")
        self.assertEqual(item["provenance"]["evidence_class"],
                         "model_attributed_archive_evidence")

    def test_evidence_metadata_mismatch_fails_closed(self):
        record = make_record("b1:c1:v1", "u", "terminology")
        association = {"finding_topic": "wording", "final_pass": "screen",
                       "research_generation": "fresh-2026-full-archive",
                       "chunk_id": "c0000",
                       "source_document_sha256":
                           record["identity"]["source_document_sha256"]}
        problems = []
        PACKETS.build_evidence_item("u", record, association, problems)
        self.assertTrue(any("topic_mismatch" in p for p in problems))


# --------------------------------------------------------------------------
# Selection rules
# --------------------------------------------------------------------------


class SelectionTests(unittest.TestCase):
    def _index(self, mapping):
        by_verse = {}
        for verse_key, topics in mapping.items():
            by_verse[verse_key] = {
                "uid-" + verse_key + "-" + str(i): {"finding_topic": topic}
                for i, topic in enumerate(topics)
            }
        return {"by_verse": by_verse}

    def test_track_b_threshold_exactly_20_included(self):
        index = self._index({
            "b1:c1:v3": ["translation"] * 20,
            "b1:c1:v4": ["translation"] * 19,
        })
        self.assertEqual(PACKETS.select_track_b(index, []), ["b1:c1:v3"])

    def test_track_b_threshold_19_excluded(self):
        index = self._index({"b1:c1:v4": ["terminology"] * 19})
        self.assertEqual(PACKETS.select_track_b(index, []), [])

    def test_track_b_accepts_all_revision_relevant_topics(self):
        index = self._index({
            "b1:c1:v1": (["translation"] * 5 + ["terminology"] * 5
                         + ["wording"] * 5 + ["capitalization"] * 5),
        })
        self.assertEqual(PACKETS.select_track_b(index, []), ["b1:c1:v1"])

    def test_scripture_only_evidence_does_not_qualify_track_b(self):
        index = self._index({"b1:c1:v6": ["scripture"] * 25})
        self.assertEqual(PACKETS.select_track_b(index, []), [])

    def test_scripture_does_not_count_toward_threshold_mix(self):
        index = self._index({
            "b1:c1:v7": ["translation"] * 19 + ["scripture"] * 50,
        })
        self.assertEqual(PACKETS.select_track_b(index, []), [])

    def test_currently_changed_verse_excluded_from_track_b(self):
        index = self._index({"b1:c1:v8": ["translation"] * 500})
        self.assertEqual(PACKETS.select_track_b(index, ["b1:c1:v8"]), [])

    def test_track_a_is_every_changed_verse(self):
        changed = ["b10:c1:v1", "b2:c1:v1", "b1:c2:v3"]
        self.assertEqual(PACKETS.select_track_a(changed),
                         ["b1:c2:v3", "b2:c1:v1", "b10:c1:v1"])


# --------------------------------------------------------------------------
# End-to-end synthetic build
# --------------------------------------------------------------------------


class SyntheticBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp(prefix="gd_pkt_e2e_")
        cls.paths = build_fixture(cls.root)
        cls.result = PACKETS.run_build(
            cls.paths, enforce_pins=False,
            generated_at="2026-01-01T00:00:00+00:00")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, ignore_errors=True)

    def packet(self, packets, verse_key):
        return next(p for p in packets if p["verse_key"] == verse_key)

    def test_track_a_contains_every_changed_verse_once(self):
        keys = [p["verse_key"] for p in self.result["packets_a"]]
        self.assertEqual(keys, ["b1:c1:v1", "b1:c1:v2", "b1:c1:v5", "b2:c1:v1"])
        self.assertEqual(len(keys), len(set(keys)))

    def test_track_a_evidence_packet(self):
        packet = self.packet(self.result["packets_a"], "b1:c1:v5")
        self.assertTrue(packet["currently_changed"])
        self.assertTrue(packet["direct_archive_verse_evidence"])
        self.assertTrue(packet["text_differs"])
        self.assertEqual(packet["evidence_summary"]["total_unique_findings"], 2)
        self.assertEqual(packet["evidence_summary"]["counts_by_topic"],
                         {"capitalization": 1, "wording": 1})
        self.assertEqual(len(packet["evidence"]), 2)
        self.assertEqual(
            [r["ruleId"] for r in packet["current_transformation_rules"]], ["R003"])

    def test_track_a_no_evidence_packet_still_emitted(self):
        packet = self.packet(self.result["packets_a"], "b1:c1:v2")
        self.assertTrue(packet["currently_changed"])
        self.assertFalse(packet["direct_archive_verse_evidence"])
        self.assertEqual(packet["evidence"], [])
        self.assertEqual(packet["evidence_summary"]["total_unique_findings"], 0)
        self.assertEqual(packet["evidence_summary"]["total_unique_source_documents"], 0)
        self.assertEqual(packet["current_transformation_rules"][0]["ruleId"], "R001")
        self.assertEqual(packet["selection_basis"]["rule"],
                         "existing_gd_transformation_review")
        self.assertIn("NOT evidence that the current wording is wrong",
                      packet["selection_basis"]["archive_evidence_note"])

    def test_multiple_transformation_rules_on_one_verse(self):
        packet = self.packet(self.result["packets_a"], "b1:c1:v1")
        self.assertEqual([r["ruleId"] for r in packet["current_transformation_rules"]],
                         ["R001", "R002"])

    def test_duplicate_manifest_reference_handling(self):
        packet = self.packet(self.result["packets_a"], "b1:c1:v2")
        rule = packet["current_transformation_rules"][0]
        self.assertEqual(rule["manifest_reference_strings"],
                         ["Genesis 1:2", "Genesis 1:2"])
        self.assertEqual(rule["applicationCount"], 3)

    def test_track_b_selection_and_threshold(self):
        keys = [p["verse_key"] for p in self.result["packets_b"]]
        self.assertEqual(keys, ["b1:c1:v3"])
        packet = self.result["packets_b"][0]
        self.assertFalse(packet["currently_changed"])
        self.assertEqual(packet["current_transformation_rules"], [])
        self.assertFalse(packet["text_differs"])
        self.assertEqual(packet["selection_basis"]["revision_relevant_threshold"], 20)
        self.assertEqual(
            packet["evidence_summary"]["revision_relevant_finding_count"], 20)
        self.assertEqual(packet["evidence_summary"]["total_unique_findings"], 23)

    def test_track_b_records_relevant_count_separately_from_all_evidence(self):
        packet = self.result["packets_b"][0]
        summary = packet["evidence_summary"]
        self.assertEqual(summary["revision_relevant_finding_count"], 20)
        self.assertEqual(summary["total_unique_findings"], 23)
        self.assertEqual(summary["counts_by_topic"],
                         {"scripture": 3, "translation": 20})

    def test_track_a_and_track_b_disjoint(self):
        a = {p["verse_key"] for p in self.result["packets_a"]}
        b = {p["verse_key"] for p in self.result["packets_b"]}
        self.assertFalse(a & b)

    def test_changed_verse_with_many_findings_not_in_track_b(self):
        keys = [p["verse_key"] for p in self.result["packets_b"]]
        self.assertNotIn("b2:c1:v1", keys)
        packet = self.packet(self.result["packets_a"], "b2:c1:v1")
        self.assertEqual(len(packet["evidence"]), 40)

    def test_packet_schema_required_fields(self):
        required = {
            "schema_version", "packet_builder_version", "track", "priority_tier",
            "verse_key", "canonical_reference", "book_id", "book", "chapter",
            "verse", "standard_kjv_text", "current_gd_text", "text_differs",
            "currently_changed", "current_transformation_rules",
            "evidence_summary", "evidence", "selection_basis",
            "direct_archive_verse_evidence",
        }
        for packet in self.result["packets_a"] + self.result["packets_b"]:
            self.assertTrue(required <= set(packet))
            self.assertEqual(packet["schema_version"],
                             PACKETS.PACKET_SCHEMA_VERSION)
            self.assertEqual(packet["packet_builder_version"],
                             PACKETS.PACKET_BUILDER_VERSION)
            summary = packet["evidence_summary"]
            self.assertTrue({
                "total_unique_findings", "total_unique_source_documents",
                "counts_by_topic", "counts_by_generation",
                "counts_by_final_pass",
            } <= set(summary))

    def test_evidence_is_deduplicated_and_ordered_deterministically(self):
        packet = self.packet(self.result["packets_a"], "b2:c1:v1")
        uids = [item["finding_uid"] for item in packet["evidence"]]
        self.assertEqual(len(uids), len(set(uids)))
        self.assertEqual(uids, sorted(uids))

    def test_deterministic_rerun_identical_bytes(self):
        again = PACKETS.run_build(
            self.paths, enforce_pins=False,
            generated_at="2026-01-01T00:00:00+00:00")
        self.assertEqual(again["stream_a_text"], self.result["stream_a_text"])
        self.assertEqual(again["stream_b_text"], self.result["stream_b_text"])
        self.assertEqual(PACKETS.dumps(again["manifest"]),
                         PACKETS.dumps(self.result["manifest"]))
        self.assertEqual(PACKETS.sha256_text(again["stream_a_text"]),
                         PACKETS.sha256_text(self.result["stream_a_text"]))

    def test_generated_at_can_be_pinned(self):
        self.assertEqual(self.result["manifest"]["generated_at"],
                         "2026-01-01T00:00:00+00:00")

    def test_no_bible_or_archive_mutation(self):
        before = hash_tree(self.root)
        PACKETS.run_build(self.paths, enforce_pins=False,
                          generated_at="2026-01-01T00:00:00+00:00")
        self.assertEqual(hash_tree(self.root), before)

    def test_unpinned_manifest_marks_pins_not_enforced(self):
        self.assertFalse(self.result["manifest"]["inputs_pinned"])
        self.assertFalse(self.result["audit"]["pins_enforced"])

    def test_audit_reverifies_every_bible_coordinate(self):
        checks = {c["name"]: c for c in self.result["audit"]["checks"]}
        combined = self.result["audit"]["combined"]["packets"]
        self.assertTrue(checks["bible_coordinate_lookups_performed"]["ok"])
        self.assertEqual(checks["bible_coordinate_lookups_performed"]["observed"],
                         combined)
        self.assertEqual(checks["bible_coordinate_lookup_failures"]["observed"], 0)

    def test_unmanifested_text_difference_check_present_and_zero(self):
        checks = {c["name"]: c for c in self.result["audit"]["checks"]}
        self.assertIn("track_b_packets_with_unmanifested_text_difference", checks)
        self.assertTrue(
            checks["track_b_packets_with_unmanifested_text_difference"]["ok"])
        self.assertEqual(
            checks["track_b_packets_with_unmanifested_text_difference"]["observed"], 0)
        self.assertEqual(
            self.result["audit"]["track_b"]["packets_with_unmanifested_text_difference"],
            0)

    def test_unmanifested_text_difference_is_detected_and_fails_audit(self):
        root = tempfile.mkdtemp(prefix="gd_pkt_unmanifested_")
        self.addCleanup(shutil.rmtree, root, True)
        paths = build_fixture(root, extra_current_overrides={
            (1, 1, 3): "synthetic Genesis 1:3 [silently changed]",
        })
        result = PACKETS.run_build(
            paths, enforce_pins=False,
            generated_at="2026-01-01T00:00:00+00:00")
        self.assertEqual(
            result["audit"]["track_b"]["packets_with_unmanifested_text_difference"], 1)
        self.assertIn("track_b_packets_with_unmanifested_text_difference",
                      result["audit"]["failed_checks"])
        packet = next(p for p in result["packets_b"] if p["verse_key"] == "b1:c1:v3")
        self.assertTrue(packet["text_differs"])
        self.assertTrue(
            packet["selection_basis"]["unmanifested_text_difference"])

    def test_production_publication_refuses_unpinned_result(self):
        out_dir = os.path.join(tempfile.mkdtemp(prefix="gd_pkt_out_"), "artifact")
        self.addCleanup(shutil.rmtree, os.path.dirname(out_dir), True)
        with self.assertRaises(PACKETS.PacketInputError):
            PACKETS.write_artifacts(self.result, out_dir, require_pins=True)
        self.assertFalse(os.path.exists(out_dir))

    def test_cli_write_with_unpinned_flag_is_refused(self):
        parent = tempfile.mkdtemp(prefix="gd_pkt_cli_")
        self.addCleanup(shutil.rmtree, parent, True)
        out_dir = os.path.join(parent, "artifact")
        with contextlib.redirect_stderr(io.StringIO()):
            code = PACKETS.main([
                "--audit-only", "--allow-unpinned", "--quiet", "--out-dir", out_dir,
                "--evidence-bridge-dir", self.paths["evidence_bridge_dir"],
                "--standard-kjv", self.paths["standard_kjv_asset"],
                "--current-gd", self.paths["current_gd_asset"],
                "--transformation-manifest", self.paths["transformation_manifest"],
                "--write",
            ])
        self.assertEqual(code, 2)
        self.assertFalse(os.path.exists(out_dir))
        self.assertEqual(staging_entries(parent), [])


# --------------------------------------------------------------------------
# Frozen input validation
# --------------------------------------------------------------------------


class FrozenInputTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="gd_pkt_pin_")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.paths = build_fixture(self.root)

    def test_pinned_validation_rejects_fixture_hashes(self):
        with self.assertRaises(PACKETS.PacketInputError):
            PACKETS.validate_frozen_inputs(self.paths, enforce_pins=True)

    def test_unpinned_validation_measures_without_enforcing(self):
        measured = PACKETS.validate_frozen_inputs(self.paths, enforce_pins=False)
        self.assertFalse(measured["pins_enforced"])
        self.assertIn("sha256", measured["finding_reference_map"])
        self.assertIn("packet_builder_source", measured)

    def test_tampered_input_fails_closed_even_unpinned_build_is_consistent(self):
        result = PACKETS.run_build(self.paths, enforce_pins=False)
        self.assertEqual(result["audit"]["verdict"], "fail")
        self.assertIn("track_a_packets", result["audit"]["failed_checks"])

    def test_broken_bible_asset_fails_closed(self):
        root = tempfile.mkdtemp(prefix="gd_pkt_bad_")
        self.addCleanup(shutil.rmtree, root, True)
        paths = build_fixture(root)
        with open(paths["current_gd_asset"], encoding="utf-8") as handle:
            asset = json.load(handle)
        asset[0]["chapters"] = asset[0]["chapters"][:1]
        write_json(paths["current_gd_asset"], asset)
        with self.assertRaises(PACKETS.CoordinateError):
            PACKETS.run_build(paths, enforce_pins=False)

    def test_missing_required_input_fails_closed_when_pinned(self):
        paths = dict(self.paths)
        paths["finding_reference_map"] = os.path.join(self.root, "absent.jsonl")
        with self.assertRaises(PACKETS.PacketInputError):
            PACKETS.validate_frozen_inputs(paths, enforce_pins=True)

    def test_parse_verse_key_fails_closed(self):
        for bad in ("", "b1:c1", "b1:c1:v1:x", "genesis 1:1", "bX:c1:v1", None):
            with self.assertRaises(PACKETS.PacketBuildError):
                PACKETS.parse_verse_key(bad)

    def test_verse_order_key_is_numeric(self):
        keys = ["b10:c1:v1", "b2:c1:v1", "b1:c2:v1", "b1:c10:v1"]
        self.assertEqual(sorted(keys, key=PACKETS.verse_order_key),
                         ["b1:c2:v1", "b1:c10:v1", "b2:c1:v1", "b10:c1:v1"])


# --------------------------------------------------------------------------
# Frozen coordinate / code dependency pins
# --------------------------------------------------------------------------


class DependencyPinTests(unittest.TestCase):
    def test_committed_dependency_files_match_pins(self):
        self.assertEqual(PACKETS.sha256_file(PACKETS.MAPPING_MODULE_PATH),
                         PACKETS.MAPPING_MODULE_SHA256)
        self.assertEqual(PACKETS.sha256_file(PACKETS.ENGINE_MODULE_PATH),
                         PACKETS.ENGINE_MODULE_SHA256)
        measured = PACKETS.validate_code_dependencies(enforce_pins=True)
        self.assertTrue(measured["gd_bible_revision_mapping"]["sha256_matches"])
        self.assertTrue(measured["gd_bible_revision_mapping"]["version_matches"])
        self.assertTrue(measured["gd_scripture_engine"]["sha256_matches"])
        self.assertTrue(measured["gd_scripture_engine"]["version_matches"])
        self.assertEqual(measured["gd_bible_revision_mapping"]["version"], "1.0.0")
        self.assertEqual(measured["gd_scripture_engine"]["version"], "1.5.0")

    def test_mapping_sha_mismatch_fails_closed(self):
        with self.assertRaises(PACKETS.PacketInputError) as ctx:
            PACKETS.validate_code_dependencies(
                enforce_pins=True, expected_mapping_sha256="0" * 64)
        self.assertIn("gd_bible_revision_mapping", str(ctx.exception))

    def test_mapping_version_mismatch_fails_closed(self):
        with self.assertRaises(PACKETS.PacketInputError) as ctx:
            PACKETS.validate_code_dependencies(
                enforce_pins=True, expected_mapping_version="9.9.9")
        self.assertIn("version", str(ctx.exception))

    def test_engine_sha_and_version_mismatch_fail_closed(self):
        with self.assertRaises(PACKETS.PacketInputError) as ctx:
            PACKETS.validate_code_dependencies(
                enforce_pins=True, expected_engine_sha256="0" * 64)
        self.assertIn("gd_scripture_engine", str(ctx.exception))
        with self.assertRaises(PACKETS.PacketInputError) as ctx:
            PACKETS.validate_code_dependencies(
                enforce_pins=True, expected_engine_version="9.9.9")
        self.assertIn("gd_scripture_engine version", str(ctx.exception))

    def test_committed_coordinate_artifact_matches_pins(self):
        measured = PACKETS.validate_coordinate_artifact(
            PACKETS.CANONICAL_COORDINATES_PATH, enforce_pins=True)
        self.assertEqual(measured["sha256"], PACKETS.CANONICAL_COORDINATES_SHA256)
        self.assertTrue(measured["sha256_matches"])
        self.assertTrue(measured["counts_match"])
        self.assertEqual(measured["counts"],
                         {"book_count": 66, "chapter_count": 1189,
                          "verse_count": 31102})
        self.assertEqual(measured["loaded_from"], PACKETS.CANONICAL_COORDINATES_PATH)

    def test_coordinate_sha_mismatch_fails_closed(self):
        with self.assertRaises(PACKETS.PacketInputError) as ctx:
            PACKETS.validate_coordinate_artifact(
                PACKETS.CANONICAL_COORDINATES_PATH, enforce_pins=True,
                expected_sha256="0" * 64)
        self.assertIn("canonical coordinates sha256", str(ctx.exception))

    def test_coordinate_count_mismatch_fails_closed(self):
        with self.assertRaises(PACKETS.PacketInputError) as ctx:
            PACKETS.validate_coordinate_artifact(
                PACKETS.CANONICAL_COORDINATES_PATH, enforce_pins=True,
                expected_counts={"book_count": 66, "chapter_count": 1189,
                                 "verse_count": 31101})
        self.assertIn("canonical coordinate counts", str(ctx.exception))


class CoordinateSourceGuardTests(unittest.TestCase):
    def test_pinned_run_refuses_any_explicit_coordinates_path(self):
        paths = PACKETS.resolve_input_paths()
        for alternate in ("/tmp/alternate_coordinates.json",
                          PACKETS.CANONICAL_COORDINATES_PATH):
            with self.assertRaises(PACKETS.PacketInputError) as ctx:
                PACKETS.run_build(paths, enforce_pins=True,
                                  coordinates_path=alternate)
            self.assertIn("alternate coordinate artifact", str(ctx.exception))

    def test_resolve_coordinate_source_defaults_to_committed_file(self):
        self.assertEqual(
            PACKETS.resolve_coordinate_source(None, enforce_pins=True),
            PACKETS.CANONICAL_COORDINATES_PATH)
        self.assertEqual(
            PACKETS.resolve_coordinate_source(None, enforce_pins=False),
            PACKETS.CANONICAL_COORDINATES_PATH)

    def test_unpinned_run_accepts_alternate_coordinates(self):
        root = tempfile.mkdtemp(prefix="gd_pkt_altcoord_")
        self.addCleanup(shutil.rmtree, root, True)
        paths, coordinates_path = build_small_fixture(root)
        result = PACKETS.run_build(
            paths, enforce_pins=False, coordinates_path=coordinates_path,
            generated_at="2026-01-01T00:00:00+00:00")
        measured = result["audit"]["inputs_measured"]["canonical_coordinates"]
        self.assertEqual(measured["loaded_from"], os.path.abspath(coordinates_path))
        self.assertEqual(measured["sha256"], PACKETS.sha256_file(coordinates_path))
        self.assertEqual(measured["counts"],
                         {"book_count": 2, "chapter_count": 3, "verse_count": 7})
        self.assertFalse(measured["counts_match"])
        self.assertEqual(len(result["packets_a"]), 1)
        self.assertEqual(result["packets_a"][0]["verse_key"], "b1:c1:v1")
        self.assertEqual(
            result["manifest"]["dependency_pins"]["canonical_coordinates"]["loaded_from"],
            os.path.abspath(coordinates_path))

    def test_unpinned_default_measures_the_committed_coordinates(self):
        root = tempfile.mkdtemp(prefix="gd_pkt_defcoord_")
        self.addCleanup(shutil.rmtree, root, True)
        paths = build_fixture(root)
        result = PACKETS.run_build(paths, enforce_pins=False)
        measured = result["audit"]["inputs_measured"]["canonical_coordinates"]
        self.assertEqual(measured["loaded_from"], PACKETS.CANONICAL_COORDINATES_PATH)
        self.assertEqual(measured["sha256"], PACKETS.CANONICAL_COORDINATES_SHA256)


# --------------------------------------------------------------------------
# Explicit --out-dir and artifact-set atomic publication
# --------------------------------------------------------------------------


class OutDirCliTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="gd_pkt_cliout_")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.paths = build_fixture(self.root)

    def cli(self, extra):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(io.StringIO()):
            code = PACKETS.main([
                "--audit-only", "--allow-unpinned", "--quiet",
                "--evidence-bridge-dir", self.paths["evidence_bridge_dir"],
                "--standard-kjv", self.paths["standard_kjv_asset"],
                "--current-gd", self.paths["current_gd_asset"],
                "--transformation-manifest", self.paths["transformation_manifest"],
            ] + extra)
        return code, stderr.getvalue()

    def test_write_without_out_dir_is_refused_before_writing(self):
        code, stderr = self.cli(["--write"])
        self.assertEqual(code, 2)
        self.assertIn("--out-dir", stderr)
        self.assertIn("REFUSED", stderr)
        # No artifact file and no destination directory was created anywhere.
        # (manifest.json belongs to the synthetic evidence bridge, not to us.)
        for name in PACKETS.ARTIFACT_FILES:
            if name == PACKETS.MANIFEST_NAME:
                continue
            self.assertFalse(os.path.exists(os.path.join(self.root, name)))
        self.assertEqual(
            [name for name in os.listdir(self.root) if os.path.isdir(
                os.path.join(self.root, name)) and name != "artifact"],
            [])

    def test_audit_only_needs_no_out_dir(self):
        code, stderr = self.cli([])
        self.assertNotEqual(code, 2)
        self.assertIn("audit-only", stderr)

    def test_out_dir_has_no_default(self):
        parser = PACKETS.build_arg_parser()
        self.assertIsNone(parser.get_default("out_dir"))


class JsonlRecordBoundaryTests(unittest.TestCase):
    """Regression for the exact production failure: 317 records / not JSON."""

    def setUp(self):
        self.parent = tempfile.mkdtemp(prefix="gd_pkt_linesep_")
        self.addCleanup(shutil.rmtree, self.parent, True)
        self.destination = os.path.join(self.parent, "artifact")

    def tricky_packets(self):
        packet = make_packet(PACKETS.TRACK_B, "b46:c15:v50")
        packet["evidence"] = [
            # The real frozen quote contains a raw U+2028 (LINE SEPARATOR):
            # "…flesh-and-blood human being? \u20281 Corinthians 15:50."
            {"finding_quote": "human being? \u20281 Corinthians 15:50."},
            # A C0 control (U+001E) is escaped by json.dumps and is harmless.
            {"finding_quote": "Matthew 24:21\x1e22"},
        ]
        return [packet]

    def test_unicode_line_separator_survives_serialization_unescaped(self):
        text = PACKETS.serialize_stream(self.tricky_packets())
        self.assertIn("\u2028", text)
        self.assertNotIn("\x1e", text)
        self.assertIn("\\u001e", text)

    def test_splitlines_miscounts_but_record_splitter_does_not(self):
        text = PACKETS.serialize_stream(self.tricky_packets())
        # the naive splitter reports 2 pieces for 1 record (the real bug)
        self.assertEqual(len(text.splitlines()), 2)
        self.assertEqual(len(PACKETS.split_jsonl_records(text)), 1)
        self.assertEqual(PACKETS.records_with_unicode_line_boundary(text), 1)
        records = PACKETS.split_jsonl_records(text)
        self.assertEqual(json.loads(records[0])["verse_key"], "b46:c15:v50")

    def test_publication_succeeds_with_unicode_line_separator_in_record(self):
        packets_b = self.tricky_packets()
        result = make_publishable_result(packets_b=packets_b)
        PACKETS.write_artifacts(result, self.destination, require_pins=True)
        with open(os.path.join(self.destination, PACKETS.TRACK_B_STREAM),
                  encoding="utf-8") as handle:
            staged = handle.read()
        self.assertEqual(staged, result["stream_b_text"])
        self.assertEqual(len(PACKETS.split_jsonl_records(staged)), 1)
        self.assertEqual(staging_entries(self.parent), [])

    def test_split_jsonl_records_requires_newline_termination(self):
        with self.assertRaises(PACKETS.PacketInputError):
            PACKETS.split_jsonl_records('{"a":1}')
        self.assertEqual(PACKETS.split_jsonl_records(""), [])
        self.assertEqual(PACKETS.split_jsonl_records('{"a":1}\n'),
                         ['{"a":1}'])

    def test_record_splitter_counts_real_blank_records_only(self):
        # A genuinely blank record is still visible as a blank record, and is
        # rejected by the staged-artifact verifier rather than being skipped.
        records = PACKETS.split_jsonl_records('{"a":1}\n\n')
        self.assertEqual(records, ['{"a":1}', ''])


class ArtifactPublicationTests(unittest.TestCase):
    def setUp(self):
        self.parent = tempfile.mkdtemp(prefix="gd_pkt_pub_")
        self.addCleanup(shutil.rmtree, self.parent, True)
        self.destination = os.path.join(self.parent, "artifact")
        self.result = make_publishable_result()

    def test_successful_publication_exposes_all_three_files_together(self):
        written = PACKETS.write_artifacts(self.result, self.destination,
                                          require_pins=True)
        self.assertEqual(sorted(os.path.basename(p) for p in written),
                         sorted(PACKETS.ARTIFACT_FILES))
        for name in PACKETS.ARTIFACT_FILES:
            self.assertTrue(os.path.isfile(os.path.join(self.destination, name)))
        self.assertTrue(os.path.isdir(self.destination))
        self.assertEqual(staging_entries(self.parent), [])
        self.assertEqual(os.listdir(self.parent), ["artifact"])

    def test_written_bytes_and_hashes_equal_manifest(self):
        PACKETS.write_artifacts(self.result, self.destination, require_pins=True)
        manifest = self.result["manifest"]
        for name, text_key in ((PACKETS.TRACK_A_STREAM, "stream_a_text"),
                               (PACKETS.TRACK_B_STREAM, "stream_b_text")):
            with open(os.path.join(self.destination, name), "rb") as handle:
                raw = handle.read()
            self.assertEqual(len(raw), manifest["streams"][name]["bytes"])
            self.assertEqual(hashlib.sha256(raw).hexdigest(),
                             manifest["streams"][name]["sha256"])
            self.assertEqual(raw.decode("utf-8"), self.result[text_key])
        with open(os.path.join(self.destination, PACKETS.MANIFEST_NAME),
                  encoding="utf-8") as handle:
            staged_manifest = json.load(handle)
        self.assertEqual(staged_manifest, manifest)

    def test_existing_destination_is_refused_untouched(self):
        os.makedirs(self.destination)
        sentinel = os.path.join(self.destination, "keep.txt")
        with open(sentinel, "w", encoding="utf-8") as handle:
            handle.write("do not touch")
        with self.assertRaises(PACKETS.PacketInputError) as ctx:
            PACKETS.write_artifacts(self.result, self.destination,
                                    require_pins=True)
        self.assertIn("existing destination", str(ctx.exception))
        self.assertEqual(os.listdir(self.destination), ["keep.txt"])
        with open(sentinel, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "do not touch")
        self.assertEqual(staging_entries(self.parent), [])

    def test_existing_destination_file_is_refused(self):
        with open(self.destination, "w", encoding="utf-8") as handle:
            handle.write("existing file")
        with self.assertRaises(PACKETS.PacketInputError):
            PACKETS.write_artifacts(self.result, self.destination,
                                    require_pins=True)
        with open(self.destination, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "existing file")
        self.assertEqual(staging_entries(self.parent), [])

    def _failing_writer(self, fail_on_call):
        real = PACKETS._write_artifact_file
        calls = {"n": 0}

        def flaky(path, text):
            calls["n"] += 1
            if calls["n"] == fail_on_call:
                raise OSError("injected failure on call {}".format(calls["n"]))
            return real(path, text)

        return flaky

    def test_failure_after_first_file_leaves_destination_absent(self):
        with mock.patch.object(PACKETS, "_write_artifact_file",
                               self._failing_writer(2)):
            with self.assertRaises(OSError):
                PACKETS.write_artifacts(self.result, self.destination,
                                        require_pins=True)
        self.assertFalse(os.path.exists(self.destination))
        self.assertEqual(staging_entries(self.parent), [])
        self.assertEqual(os.listdir(self.parent), [])

    def test_failure_after_second_file_leaves_destination_absent(self):
        with mock.patch.object(PACKETS, "_write_artifact_file",
                               self._failing_writer(3)):
            with self.assertRaises(OSError):
                PACKETS.write_artifacts(self.result, self.destination,
                                        require_pins=True)
        self.assertFalse(os.path.exists(self.destination))
        self.assertEqual(staging_entries(self.parent), [])
        self.assertEqual(os.listdir(self.parent), [])

    def test_verification_failure_prevents_publication(self):
        real = PACKETS._write_artifact_file

        def corrupting(path, text):
            if path.endswith(PACKETS.TRACK_B_STREAM):
                return real(path, text + "corrupted\n")
            return real(path, text)

        with mock.patch.object(PACKETS, "_write_artifact_file", corrupting):
            with self.assertRaises(PACKETS.PacketInputError) as ctx:
                PACKETS.write_artifacts(self.result, self.destination,
                                        require_pins=True)
        self.assertIn("verification", str(ctx.exception))
        self.assertFalse(os.path.exists(self.destination))
        self.assertEqual(staging_entries(self.parent), [])

    def test_missing_parent_directory_is_refused(self):
        destination = os.path.join(self.parent, "absent", "artifact")
        with self.assertRaises(PACKETS.PacketInputError) as ctx:
            PACKETS.write_artifacts(self.result, destination, require_pins=True)
        self.assertIn("parent directory", str(ctx.exception))
        self.assertFalse(os.path.exists(destination))

    def test_publication_requires_a_destination(self):
        for destination in (None, ""):
            with self.assertRaises(PACKETS.PacketInputError):
                PACKETS.write_artifacts(self.result, destination,
                                        require_pins=True)


class PublicationBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.parent = tempfile.mkdtemp(prefix="gd_pkt_bound_")
        self.addCleanup(shutil.rmtree, self.parent, True)
        self.destination = os.path.join(self.parent, "artifact")

    def test_tampered_stream_text_is_refused(self):
        result = make_publishable_result()
        result["stream_a_text"] = result["stream_a_text"] + "{}\n"
        with self.assertRaises(PACKETS.PacketInputError) as ctx:
            PACKETS.write_artifacts(result, self.destination, require_pins=True)
        self.assertIn("does not match", str(ctx.exception))
        self.assertFalse(os.path.exists(self.destination))

    def test_tampered_packet_list_is_refused(self):
        result = make_publishable_result()
        result["packets_a"].append(make_packet(PACKETS.TRACK_A, "b1:c1:v9"))
        with self.assertRaises(PACKETS.PacketInputError):
            PACKETS.write_artifacts(result, self.destination, require_pins=True)
        self.assertFalse(os.path.exists(self.destination))

    def test_tampered_manifest_hash_is_refused(self):
        result = make_publishable_result()
        result["manifest"]["streams"][PACKETS.TRACK_A_STREAM]["sha256"] = "0" * 64
        with self.assertRaises(PACKETS.PacketInputError) as ctx:
            PACKETS.write_artifacts(result, self.destination, require_pins=True)
        self.assertIn("sha256", str(ctx.exception))
        self.assertFalse(os.path.exists(self.destination))

    def test_tampered_manifest_byte_count_is_refused(self):
        result = make_publishable_result()
        result["manifest"]["streams"][PACKETS.TRACK_B_STREAM]["bytes"] = 1
        with self.assertRaises(PACKETS.PacketInputError):
            PACKETS.write_artifacts(result, self.destination, require_pins=True)
        self.assertFalse(os.path.exists(self.destination))

    def test_failed_audit_is_refused(self):
        result = make_publishable_result()
        result["audit"]["verdict"] = "fail"
        result["audit"]["failed_checks"] = ["track_a_packets"]
        with self.assertRaises(PACKETS.PacketInputError) as ctx:
            PACKETS.write_artifacts(result, self.destination, require_pins=True)
        self.assertIn("audit", str(ctx.exception))
        self.assertFalse(os.path.exists(self.destination))

    def test_manifest_audit_mismatch_is_refused(self):
        result = make_publishable_result()
        result["manifest"]["audit_failed_checks"] = ["track_b_packets"]
        with self.assertRaises(PACKETS.PacketInputError):
            PACKETS.write_artifacts(result, self.destination, require_pins=True)
        self.assertFalse(os.path.exists(self.destination))

    def test_unpinned_result_refused_for_production_but_allowed_for_tests(self):
        unpinned = make_publishable_result(pinned=False)
        with self.assertRaises(PACKETS.PacketInputError) as ctx:
            PACKETS.write_artifacts(unpinned, self.destination, require_pins=True)
        self.assertIn("inputs_pinned", str(ctx.exception))
        self.assertFalse(os.path.exists(self.destination))
        PACKETS.write_artifacts(unpinned, self.destination, require_pins=False)
        for name in PACKETS.ARTIFACT_FILES:
            self.assertTrue(os.path.isfile(os.path.join(self.destination, name)))

    def test_validate_publishable_result_returns_payloads(self):
        result = make_publishable_result()
        payloads = PACKETS.validate_publishable_result(result, require_pins=True)
        self.assertEqual(sorted(payloads), sorted(PACKETS.ARTIFACT_FILES))
        self.assertEqual(payloads[PACKETS.TRACK_A_STREAM],
                         result["stream_a_text"])


# --------------------------------------------------------------------------
# Gated full audit against the frozen production inputs
# --------------------------------------------------------------------------

FULL_AUDIT_ENV = "GD_RUN_FULL_PACKET_AUDIT"
_FULL_ENABLED = os.environ.get(FULL_AUDIT_ENV) == "1"
_FROZEN_BUILD_CACHE = {}


def frozen_pinned_build():
    """One pinned end-to-end build shared by the gated frozen-input classes."""
    if "result" not in _FROZEN_BUILD_CACHE:
        _FROZEN_BUILD_CACHE["result"] = PACKETS.run_build(
            PACKETS.resolve_input_paths(), enforce_pins=True,
            generated_at="2026-01-01T00:00:00+00:00")
    return _FROZEN_BUILD_CACHE["result"]


@unittest.skipUnless(_FULL_ENABLED, "set {} =1 for the frozen-input audit".format(
    FULL_AUDIT_ENV))
class FullFrozenInputAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = PACKETS.resolve_input_paths()
        cls.before = {
            role: PACKETS.sha256_file(path)
            for role, path in cls.paths.items() if os.path.isfile(path)
        }
        cls.result = frozen_pinned_build()
        cls.audit = cls.result["audit"]

    def test_audit_verdict_pass(self):
        self.assertEqual(self.audit["verdict"], "pass")
        self.assertEqual(self.audit["failed_checks"], [])

    def test_track_a_counts(self):
        self.assertEqual(self.audit["track_a"]["packets"], 335)
        self.assertEqual(self.audit["track_a"]["packets_with_direct_archive_evidence"], 215)
        self.assertEqual(self.audit["track_a"]["packets_without_direct_archive_evidence"], 120)
        self.assertEqual(self.audit["track_a"]["evidence_rows"], 2385)
        self.assertEqual(self.audit["track_a"]["unique_evidence_findings"], 2121)

    def test_track_b_counts(self):
        self.assertEqual(self.audit["track_b"]["packets"], 316)
        self.assertEqual(self.audit["track_b"]["overlap_with_track_a"], 0)
        self.assertGreaterEqual(self.audit["track_b"]["min_revision_relevant_findings"], 20)

    def test_combined_counts(self):
        self.assertEqual(self.audit["combined"]["packets"], 651)
        self.assertEqual(self.audit["combined"]["unique_verse_keys"], 651)
        self.assertEqual(self.audit["combined"]["duplicate_verse_keys"], 0)

    def test_frozen_inputs_not_mutated(self):
        after = {
            role: PACKETS.sha256_file(path)
            for role, path in self.paths.items() if os.path.isfile(path)
        }
        self.assertEqual(after, self.before)

    def test_serialized_sizes_reported(self):
        serialization = self.audit["serialization"]
        self.assertGreater(
            serialization[PACKETS.TRACK_A_STREAM]["serialized_bytes_exact"], 0)
        self.assertGreater(
            serialization[PACKETS.TRACK_B_STREAM]["serialized_bytes_exact"], 0)

    def test_exact_serialized_bytes_and_hashes(self):
        serialization = self.audit["serialization"]
        self.assertEqual(
            serialization[PACKETS.TRACK_A_STREAM]["serialized_bytes_exact"],
            4394249)
        self.assertEqual(
            serialization[PACKETS.TRACK_B_STREAM]["serialized_bytes_exact"],
            27657062)
        self.assertEqual(serialization["combined_serialized_bytes_exact"],
                         32051311)

    def test_dependency_pins_are_recorded_and_match(self):
        pins = self.result["manifest"]["dependency_pins"]
        coordinates = pins["canonical_coordinates"]
        self.assertEqual(coordinates["sha256"],
                         PACKETS.CANONICAL_COORDINATES_SHA256)
        self.assertTrue(coordinates["sha256_matches"])
        self.assertEqual(coordinates["counts"],
                         {"book_count": 66, "chapter_count": 1189,
                          "verse_count": 31102})
        self.assertTrue(coordinates["counts_match"])
        self.assertEqual(coordinates["loaded_from"],
                         PACKETS.CANONICAL_COORDINATES_PATH)
        mapping = pins["gd_bible_revision_mapping"]
        self.assertEqual(mapping["sha256"], PACKETS.MAPPING_MODULE_SHA256)
        self.assertEqual(mapping["version"], PACKETS.MAPPING_MODULE_VERSION_EXPECTED)
        self.assertTrue(mapping["sha256_matches"])
        self.assertTrue(mapping["version_matches"])
        engine = pins["gd_scripture_engine"]
        self.assertEqual(engine["sha256"], PACKETS.ENGINE_MODULE_SHA256)
        self.assertEqual(engine["version"], PACKETS.ENGINE_MODULE_VERSION_EXPECTED)
        self.assertTrue(engine["sha256_matches"])
        self.assertTrue(engine["version_matches"])

    def test_real_result_is_publishable_without_writing(self):
        payloads = PACKETS.validate_publishable_result(
            self.result, require_pins=True)
        self.assertEqual(sorted(payloads), sorted(PACKETS.ARTIFACT_FILES))

    def test_track_b_unmanifested_difference_is_zero(self):
        check = next(
            c for c in self.audit["checks"]
            if c["name"] == "track_b_packets_with_unmanifested_text_difference")
        self.assertTrue(check["ok"])
        self.assertEqual(check["observed"], 0)


class OwnerInputArtifactTests(unittest.TestCase):
    """The durable owner-input artifact is the only source of Track C."""

    @classmethod
    def setUpClass(cls):
        cls.paths = PACKETS.resolve_input_paths()
        cls.owner = PACKETS.load_owner_inputs(cls.paths["owner_inputs"])
        cls.books = PACKETS.load_coordinate_books()
        cls.candidates = PACKETS.resolve_owner_candidates(cls.owner, cls.books)
        cls.by_id = {c["candidate_id"]: c for c in cls.candidates}

    # (1) exactly ten unique owner verse candidates.
    def test_exactly_ten_unique_owner_verse_candidates(self):
        self.assertEqual(len(self.owner["verse_candidates"]), 10)
        self.assertEqual(len(self.candidates), 10)
        self.assertEqual(len({c["verse_key"] for c in self.candidates}), 10)

    # (2) a duplicated owner note is preserved, without a duplicate identity.
    def test_duplicate_occurrence_preserved_without_duplicate_identity(self):
        duplicates = [c for c in self.candidates if c["duplicate_occurrence_count"]]
        self.assertEqual(len(duplicates), 1)
        repeated = duplicates[0]
        self.assertEqual(repeated["verse_key"], "b62:c2:v20")
        self.assertEqual(repeated["owner_note_occurrence_count"], 2)
        self.assertEqual(repeated["duplicate_occurrence_count"], 1)
        texts = [o["text"] for o in repeated["owner_note_occurrences"]]
        self.assertEqual(texts[0], texts[1])
        self.assertEqual(repeated["owner_note_occurrences"][1].get(
            "repeat_of_occurrence"), 1)
        # Both occurrences stay in ONE review identity.
        self.assertEqual(
            len({c["verse_key"] for c in self.candidates
                 if c["candidate_id"] == repeated["candidate_id"]}), 1)

    # (3) \"Jude 1\" resolves through single-chapter semantics.
    def test_jude_single_chapter_reference_resolves_to_verse_one(self):
        jude = self.by_id["owner-c02-jude-1-called"]
        self.assertEqual(jude["owner_reference_raw"], "Jude 1")
        self.assertEqual(jude["verse_key"], "b65:c1:v1")
        self.assertEqual(jude["canonical_reference"], "Jude 1:1")
        self.assertEqual(jude["owner_reference_raw_parser_status"], "mapped_verse")
        self.assertEqual(PACKETS.classify_owner_reference("Jude 1")[1], "b65:c1:v1")

    # (4) the raw owner spelling is preserved while the canonical form is Isaiah.
    def test_isaias_is_preserved_while_canonical_is_isaiah(self):
        isaias = self.by_id["owner-c08-isaiah-35-7-dragons"]
        self.assertEqual(isaias["owner_reference_raw"], "Isaias 35:7")
        self.assertEqual(isaias["canonical_reference"], "Isaiah 35:7")
        self.assertEqual(isaias["verse_key"], "b23:c35:v7")
        # The committed parser cannot resolve the raw spelling: it is recorded
        # as unresolved and the normalization is owner-declared, not an alias.
        self.assertEqual(isaias["owner_reference_raw_parser_status"], "unresolved")
        self.assertIsNone(PACKETS.classify_owner_reference("Isaias 35:7")[1])
        normalization = isaias["owner_reference_normalization"]
        self.assertEqual(normalization["from"], "Isaias 35:7")
        self.assertEqual(normalization["to"], "Isaiah 35:7")
        self.assertEqual(normalization["authority"], "owner_declared")
        self.assertEqual(isaias["owner_reference_parser_input"], "Isaiah 35:7")

    # (5) a quoted context range never promotes the neighbouring verse.
    def test_john_14_3_context_does_not_become_a_candidate(self):
        john = self.by_id["owner-c07-john-14-2-mansions"]
        self.assertEqual(john["verse_key"], "b43:c14:v2")
        self.assertEqual(john["context_only_references"], ["John 14:2-3"])
        self.assertEqual(john["context_only_verse_keys"], ["b43:c14:v3"])
        self.assertNotIn("b43:c14:v3",
                         {c["verse_key"] for c in self.candidates})

    # (6) every owner alternative is preserved, none is silently chosen.
    def test_three_jeremiah_alternatives_are_preserved(self):
        jeremiah = self.by_id["owner-c10-jeremiah-17-9-desperately-wicked"]
        change = jeremiah["proposed_change"]
        self.assertEqual(len(change["to"]), 3)
        self.assertTrue(change["alternatives_preserved"])
        self.assertIsNone(change["selection"])
        self.assertEqual(jeremiah["accepted_translation"], False)
        self.assertEqual(jeremiah["candidate_status"], "review_candidate")
        self.assertEqual(jeremiah["provenance_class"],
                         "owner_specified_editorial_candidate")

    # (7) owner rationale is never archive evidence.
    def test_owner_rationale_is_never_archive_evidence(self):
        for candidate in self.candidates:
            self.assertEqual(candidate["provenance_class"],
                             PACKETS.OWNER_PROVENANCE_CLASS)
            self.assertEqual(candidate["accepted_translation"], False)
            self.assertNotIn("evidence", candidate)
            self.assertNotIn("finding_uid", json.dumps(candidate))
        statements = self.owner["statements"]
        self.assertIn("authority", statements)
        self.assertIn("evidence_separation", statements)

    # (11) style policies are not verse packets.
    def test_style_policies_are_not_verse_packets(self):
        policies = self.owner["style_policies"]
        self.assertEqual([p["policy_id"] for p in policies],
                         ["style-01-reverential-capitalization",
                          "style-02-gods-kingdom",
                          "style-03-gods-word"])
        candidate_ids = {c["candidate_id"] for c in self.candidates}
        for policy in policies:
            self.assertNotIn(policy["policy_id"], candidate_ids)
            self.assertEqual(policy["applied"], False)
            self.assertEqual(policy["approved"], False)
            self.assertEqual(policy["implementation_status"], "not_implemented")
        # Every policy example reference is context, never a Track C candidate.
        candidate_keys = {c["verse_key"] for c in self.candidates}
        for policy in policies:
            for example in policy.get("examples", []):
                reference = example.get("reference_raw") or example.get("reference")
                if not reference:
                    continue
                _status, key = PACKETS.classify_owner_reference(reference)
                if key:
                    self.assertNotIn(key, candidate_keys)

    # (12) reverential capitalization is a final, reversible pass, not applied.
    def test_reverential_capitalization_is_final_reversible_and_not_applied(self):
        policy = next(p for p in self.owner["style_policies"]
                      if p["policy_id"] == "style-01-reverential-capitalization")
        self.assertEqual(policy["stage"], "final_reversible_style_pass")
        self.assertEqual(policy["apply_order"], "last")
        self.assertTrue(policy["reversible_boundary_required"])
        self.assertEqual(policy["applied"], False)
        self.assertTrue(policy["owner_open_review_question"])
        self.assertTrue(policy["owner_intends_to_use_regardless"])
        self.assertTrue(policy["owner_requires_review_before_presenting_to_minister"])
        self.assertEqual(policy["status"], "review_candidate")

    # (13) the Kingdom policy is contextual, never a blind replacement.
    def test_kingdom_policy_is_contextual_not_blind_replace(self):
        policy = next(p for p in self.owner["style_policies"]
                      if p["policy_id"] == "style-02-gods-kingdom")
        self.assertTrue(policy["requires_contextual_classification"])
        self.assertTrue(policy["blind_replacement_forbidden"])
        self.assertEqual(policy["applied"], False)
        self.assertEqual(policy["status"], "review_candidate")
        self.assertIn("context", json.dumps(policy).lower())

    # (14) the Word policy stays an open candidate question.
    def test_word_policy_remains_a_candidate_question(self):
        policy = next(p for p in self.owner["style_policies"]
                      if p["policy_id"] == "style-03-gods-word")
        self.assertEqual(policy["status"], "review_candidate_question")
        self.assertTrue(policy["requires_contextual_classification"])
        self.assertTrue(policy["blind_replacement_forbidden"])
        self.assertEqual(policy["applied"], False)
        self.assertEqual(policy["wording_hedge_preserved"], "might")

    def test_owner_inputs_sha256_matches_the_pin(self):
        self.assertEqual(PACKETS.sha256_file(self.paths["owner_inputs"]),
                         PACKETS.OWNER_INPUTS_SHA256)

    def test_unresolved_owner_reference_is_reported_not_guessed(self):
        # A raw spelling with neither a parse nor a declared normalization must
        # fail closed instead of silently dropping or inventing a verse.
        broken = copy.deepcopy(self.owner)
        candidate = broken["verse_candidates"][0]
        candidate["owner_reference_raw"] = "Hesekiel 99:99"
        candidate["owner_reference_parser_input"] = "Hesekiel 99:99"
        candidate["owner_reference_normalization"] = None
        candidate["owner_reference_raw_parser_status"] = None
        with self.assertRaises(PACKETS.PacketBuildError) as caught:
            PACKETS.resolve_owner_candidates(broken, self.books)
        self.assertIn("not exactly one verse", str(caught.exception))


class OwnerOverlayMergeTests(unittest.TestCase):
    """Overlay / universe behaviour on an isolated synthetic fixture."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="owner_overlay_")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.paths = build_fixture(self.root)

    def build_with(self, candidates, policies=None):
        self.paths["owner_inputs"] = write_owner_inputs(
            self.root, candidates=candidates, policies=policies)
        return PACKETS.run_build(self.paths, enforce_pins=False,
                                 generated_at="2026-01-01T00:00:00+00:00")

    def owner_candidate(self, candidate_id, raw, parser_input, verse_key,
                        canonical, occurrences=None, status="mapped_verse"):
        return {
            "candidate_id": candidate_id,
            "candidate_category": "owner_note",
            "owner_reference_raw": raw,
            "owner_reference_parser_input": parser_input,
            "owner_reference_normalization": None,
            "owner_reference_raw_parser_status": status,
            "canonical_reference": canonical,
            "verse_key": verse_key,
            "owner_note_occurrences": occurrences or [
                {"occurrence": 1, "text": "owner note for " + candidate_id}],
            "proposed_change": {"kind": "word_replacement", "from": "alpha",
                                "to": ["beta"], "alternatives_preserved": False,
                                "selection": "single"},
            "owner_question": None,
            "candidate_status": PACKETS.OWNER_CANDIDATE_STATUS,
            "provenance_class": PACKETS.OWNER_PROVENANCE_CLASS,
            "accepted_translation": False,
            "flags": {"owner_cites_external_translation": False,
                      "external_translation_is_evidence": False},
            "context_only_references": [],
            "context_only_verse_keys": [],
            "resolution_note": None,
        }

    # (8) an owner-only verse with zero archive evidence is still review eligible.
    def test_owner_only_candidate_with_zero_archive_evidence_is_eligible(self):
        result = self.build_with([self.owner_candidate(
            "own-01", "Genesis 2:1", "Genesis 2:1", "b1:c2:v1", "Genesis 2:1")])
        overlay = result["owner_overlay"]
        self.assertEqual(len(overlay), 1)
        record = overlay[0]
        self.assertTrue(record["owner_only"])
        self.assertEqual(record["overlay_mode"], "standalone_owner_packet")
        self.assertEqual(record["existing_packet_stream"], None)
        self.assertEqual(record["evidence"], [])
        self.assertFalse(record["direct_archive_verse_evidence"])
        self.assertEqual(record["selection_basis"]["archive_evidence_threshold_required"],
                         False)
        self.assertEqual(
            record["selection_basis"]["revision_relevant_threshold"], None)
        row = next(r for r in result["review_universe"]
                   if r["verse_key"] == "b1:c2:v1")
        self.assertTrue(row["in_track_c"])
        self.assertTrue(row["owner_only"])
        self.assertEqual(row["packet_stream"], PACKETS.OWNER_OVERLAY_STREAM)
        self.assertIn("owner_candidate_review_overlay.jsonl", result["manifest"]["streams"])

    # (9) an owner candidate already in Track A or B merges by verse key.
    def test_overlap_merges_by_verse_key(self):
        result = self.build_with([
            self.owner_candidate("own-a", "Genesis 1:1", "Genesis 1:1",
                                 "b1:c1:v1", "Genesis 1:1"),
            self.owner_candidate("own-b", "Genesis 1:3", "Genesis 1:3",
                                 "b1:c1:v3", "Genesis 1:3"),
            self.owner_candidate("own-c", "Genesis 2:1", "Genesis 2:1",
                                 "b1:c2:v1", "Genesis 2:1"),
        ])
        a_keys = {p["verse_key"] for p in result["packets_a"]}
        b_keys = {p["verse_key"] for p in result["packets_b"]}
        self.assertIn("b1:c1:v1", a_keys)
        self.assertIn("b1:c1:v3", b_keys)
        overlay = {r["verse_key"]: r for r in result["owner_overlay"]}
        self.assertEqual(len(overlay), 3)

        merged_a = overlay["b1:c1:v1"]
        self.assertFalse(merged_a["owner_only"])
        self.assertFalse(merged_a["payload_embedded"])
        self.assertEqual(merged_a["overlay_mode"], "merge_into_existing_packet")
        self.assertEqual(merged_a["existing_packet_stream"], PACKETS.TRACK_A_STREAM)
        self.assertEqual(merged_a["existing_packet_track"], PACKETS.TRACK_A)
        self.assertNotIn("evidence", merged_a)
        self.assertIn("merge", merged_a["merge_instruction"].lower())
        self.assertEqual(merged_a["owner_input"]["candidate_ids"], ["own-a"])

        merged_b = overlay["b1:c1:v3"]
        self.assertEqual(merged_b["existing_packet_stream"], PACKETS.TRACK_B_STREAM)
        self.assertEqual(merged_b["existing_packet_track"], PACKETS.TRACK_B)
        self.assertFalse(merged_b["payload_embedded"])

        standalone = overlay["b1:c2:v1"]
        self.assertTrue(standalone["owner_only"])
        self.assertTrue(standalone["payload_embedded"])

        track_c = result["audit"]["track_c"]
        self.assertEqual(track_c["overlap_with_track_a"], 1)
        self.assertEqual(track_c["overlap_with_track_b"], 1)
        self.assertEqual(track_c["owner_only_packets"], 1)
        self.assertEqual(track_c["pointer_records"], 2)

    # (10) no verse is ever sent to the model twice after A + B + C.
    def test_no_duplicate_model_review_identity_after_a_b_c(self):
        result = self.build_with([
            self.owner_candidate("own-a", "Genesis 1:1", "Genesis 1:1",
                                 "b1:c1:v1", "Genesis 1:1"),
            self.owner_candidate("own-b", "Genesis 1:3", "Genesis 1:3",
                                 "b1:c1:v3", "Genesis 1:3"),
            self.owner_candidate("own-c", "Genesis 2:1", "Genesis 2:1",
                                 "b1:c2:v1", "Genesis 2:1"),
        ])
        universe = result["review_universe"]
        identities = [row["review_identity"] for row in universe]
        self.assertEqual(len(identities), len(set(identities)))
        expected = ({p["verse_key"] for p in result["packets_a"]}
                    | {p["verse_key"] for p in result["packets_b"]}
                    | {r["verse_key"] for r in result["owner_overlay"]})
        self.assertEqual(set(identities), expected)
        self.assertEqual(len(universe), len(expected))
        # Each owner verse names exactly one authoritative packet stream.
        for row in universe:
            if row["in_track_c"]:
                self.assertEqual(
                    sum(1 for other in universe
                        if other["verse_key"] == row["verse_key"]), 1)
        # Track C never re-publishes an A/B payload.
        overlay_bytes = len(result["owner_overlay_text"].encode("utf-8"))
        self.assertLess(overlay_bytes, 400000)

    def test_owner_streams_are_not_duplicated_a_b_payloads(self):
        result = self.build_with([self.owner_candidate(
            "own-a", "Genesis 1:1", "Genesis 1:1", "b1:c1:v1", "Genesis 1:1")])
        for record in result["owner_overlay"]:
            if record["owner_only"]:
                continue
            self.assertNotIn("standard_kjv_text", record)
            self.assertNotIn("current_gd_text", record)
            self.assertNotIn("evidence", record)

    def test_style_policies_do_not_create_packets(self):
        result = self.build_with(
            [self.owner_candidate("own-a", "Genesis 2:1", "Genesis 2:1",
                                  "b1:c2:v1", "Genesis 2:1")],
            policies=[{
                "policy_id": "style-01", "policy_scope": "bible_wide",
                "title": "Reverential capitalization", "owner_note_raw": "note",
                "owner_intent": "intent",
                "examples": [{"from": "he", "to": "He", "reference_raw": "John 8:29"}],
                "requires_contextual_classification": True,
                "blind_replacement_forbidden": True,
                "stage": "final_reversible_style_pass", "apply_order": "last",
                "reversible_boundary_required": True, "status": "review_candidate",
                "approved": False, "implementation_status": "not_implemented",
                "applied": False,
            }])
        audit = result["audit"]
        self.assertEqual(audit["style_policies"]["count"], 1)
        self.assertEqual(audit["style_policies"]["applied_count"], 0)
        self.assertEqual(audit["style_policies"]["verse_packets_created"], 0)
        self.assertEqual(len(result["owner_overlay"]), 1)
        # The policy example reference is not promoted into the review universe.
        self.assertNotIn("b43:c8:v29",
                         {row["verse_key"] for row in result["review_universe"]})


class OwnerContextPreservationTests(unittest.TestCase):
    """Raw owner context is preserved verbatim and never becomes evidence."""

    @classmethod
    def setUpClass(cls):
        cls.paths = PACKETS.resolve_input_paths()
        cls.owner = PACKETS.load_owner_inputs(cls.paths["owner_inputs"])
        cls.books = PACKETS.load_coordinate_books()
        cls.candidates = PACKETS.resolve_owner_candidates(cls.owner, cls.books)
        cls.candidate_keys = {c["verse_key"] for c in cls.candidates}
        cls.jude = next(c for c in cls.candidates
                        if c["candidate_id"] == "owner-c02-jude-1-called")
        cls.reverential = next(
            p for p in cls.owner["style_policies"]
            if p["policy_id"] == "style-01-reverential-capitalization")
        cls.reverential_notes = cls.reverential["owner_note_occurrences"]

    # (1) the full first Jude note is preserved, not truncated.
    def test_jude_note_preserves_the_owner_scripture_contrast(self):
        first = self.jude["owner_note_occurrences"][0]["text"]
        self.assertIn("many are called, but few are chosen", first)
        self.assertIn("Matthew 22:14", first)
        self.assertIn("sanctified by God the Father, and preserved in Jesus Christ",
                      first)
        self.assertNotIn("...", first)
        self.assertGreater(len(first), 500)

    # (2) the owner's personally-inviting context is preserved.
    def test_jude_note_preserves_the_personal_invitation_context(self):
        first = self.jude["owner_note_occurrences"][0]["text"]
        self.assertIn("That word called is better read as invited", first)
        self.assertIn("This is God personally inviting someone to be part of His Family",
                      first)
        self.assertIn("before God calls an individual, God the Father sanctifies him "
                      "or her", first)
        # The existing second occurrence is untouched, and both stay on ONE identity.
        self.assertEqual(self.jude["owner_note_occurrences"][1]["text"],
                         '"Called" (Jude 1) -> better translated as "invited."')
        self.assertEqual(self.jude["verse_key"], "b65:c1:v1")
        self.assertEqual(self.jude["owner_note_occurrence_count"], 2)

    # (3) a scripture reference inside an owner note creates no candidate.
    def test_matthew_22_14_is_not_promoted_into_track_c(self):
        status, key = PACKETS.classify_owner_reference("Matthew 22:14")
        self.assertEqual(status, "mapped_verse")
        self.assertEqual(key, "b40:c22:v14")
        # The reference really is present in the preserved note ...
        self.assertIn("Matthew 22:14", self.jude["owner_note_occurrences"][0]["text"])
        # ... and it still created nothing: no candidate, no context promotion.
        self.assertNotIn(key, self.candidate_keys)
        self.assertEqual(len(self.candidates), 10)
        for candidate in self.candidates:
            self.assertNotIn(key, candidate["context_only_verse_keys"])

    # (4) NKJV/NASB mentions stay owner context.
    def test_reverential_notes_keep_external_translations_as_owner_context(self):
        joined = "\n".join(o["text"] for o in self.reverential_notes)
        self.assertIn("New King James Version", joined)
        self.assertIn("New American Standard Bible", joined)
        self.assertIn("owner-supplied rationale only", json.dumps(
            self.owner["statements"], ensure_ascii=False))
        # No external-translation mention is turned into evidence or a claim.
        self.assertNotIn("finding_uid", joined)
        self.assertNotIn("source_document", joined)
        self.assertEqual(self.reverential["example_is_illustrative_only"], True)
        self.assertEqual(self.reverential["approved"], False)
        self.assertEqual(self.reverential["applied"], False)

    # (5) the Me/My lack-of-humility explanation is preserved.
    def test_reverential_notes_preserve_the_me_my_explanation(self):
        second = self.reverential_notes[1]["text"]
        self.assertIn("it does not imply a lack of humility in His spoken words",
                      second)
        self.assertIn("typographic reverence of the translation itself", second)
        self.assertIn("visual guide to help readers track who is acting or speaking",
                      second)
        self.assertIn("pronoun-dense verses", second)

    # (6) the owner's reversibility rationale is preserved.
    def test_reverential_notes_preserve_the_reversibility_rationale(self):
        third = self.reverential_notes[2]["text"]
        self.assertIn("This rule should be last", third)
        self.assertIn("always modify the rule", third)
        self.assertIn("easy to revert to when the reverential capitalization happened",
                      third)
        self.assertIn("easier to get it back to before that last change", third)
        self.assertIn("before I get a minister to look at it", third)
        self.assertEqual(len(self.reverential_notes), 3)
        # Structured policy fields are unchanged by the raw-note restoration.
        self.assertEqual(self.reverential["stage"], "final_reversible_style_pass")
        self.assertEqual(self.reverential["apply_order"], "last")
        self.assertTrue(self.reverential["reversible_boundary_required"])
        self.assertEqual(self.reverential["approved"], False)
        self.assertEqual(self.reverential["applied"], False)
        self.assertEqual(self.reverential["implementation_status"], "not_implemented")

    # (7) John 8:29 stays illustrative only.
    def test_john_8_29_remains_illustrative_only(self):
        status, key = PACKETS.classify_owner_reference("John 8:29")
        self.assertEqual(status, "mapped_verse")
        self.assertEqual(key, "b43:c8:v29")
        joined = "\n".join(o["text"] for o in self.reverential_notes)
        self.assertIn("John 8:29 And He that sent Me is with Me", joined)
        self.assertNotIn(key, self.candidate_keys)
        self.assertEqual(self.reverential["example_reference_raw"], "John 8:29")
        self.assertEqual(self.reverential["example_is_illustrative_only"], True)
        self.assertNotIn("proposed_change", self.reverential)

    # (8) style-policy raw notes never become archive evidence.
    def test_style_policy_raw_notes_never_become_archive_evidence(self):
        for policy in self.owner["style_policies"]:
            self.assertNotIn("evidence", policy)
            self.assertNotIn("finding_uid", policy)
            self.assertNotIn("source_document_sha256", policy)
            self.assertEqual(policy["implementation_status"], "not_implemented")
            self.assertFalse(policy["approved"])
            self.assertFalse(policy["applied"])
            for occurrence in policy["owner_note_occurrences"]:
                self.assertIsInstance(occurrence["text"], str)
                self.assertTrue(occurrence["text"])
        # No style policy is a candidate and no policy id is a verse key.
        policy_ids = {p["policy_id"] for p in self.owner["style_policies"]}
        self.assertEqual(policy_ids & self.candidate_keys, set())
        self.assertEqual(policy_ids & {c["candidate_id"] for c in self.candidates},
                         set())

    def test_raw_owner_text_is_not_parsed_for_references(self):
        # Behavioural proof: replacing every raw note (candidate and style) with
        # injected references changes no candidate's identity or verse key.
        baseline = {(c["candidate_id"], c["verse_key"]) for c in self.candidates}
        mutated = copy.deepcopy(self.owner)
        for candidate in mutated["verse_candidates"]:
            for occurrence in candidate["owner_note_occurrences"]:
                occurrence["text"] = "Genesis 9:9, Malachi 4:6, Revelation 22:21"
        for policy in mutated["style_policies"]:
            for occurrence in policy["owner_note_occurrences"]:
                occurrence["text"] = "Matthew 22:14, John 8:29, Revelation 22:21"
        after = {(c["candidate_id"], c["verse_key"])
                 for c in PACKETS.resolve_owner_candidates(mutated, self.books)}
        self.assertEqual(baseline, after)
        self.assertEqual(len(after), 10)
        # Structural guard: the resolver never reads the policy block and never
        # feeds note text to the reference parser.
        source = inspect.getsource(PACKETS.resolve_owner_candidates)
        self.assertNotIn("style_policies", source)
        self.assertNotIn("classify_owner_reference(text", source)
        self.assertNotIn("classify_owner_context_reference(text", source)
        self.assertNotIn("re.findall", source)


class WriterRegressionTests(unittest.TestCase):
    """The exact production writer failure: 317 staged lines for 316 packets."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="writer_regression_")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def test_regression_exact_production_line_count_failure(self):
        # One record, exactly like the real Track B packet for 1 Corinthians
        # 15:50 (verse_key b46:c15:v50), whose evidence[24].finding_quote
        # contains a RAW U+2028 at offset 95 inside a JSON string value.
        quote = ("Is this addressing flesh-and-blood human being? \u2028"
                 "1 Corinthians 15:50.")
        packet = make_packet(PACKETS.TRACK_B, "b46:c15:v50")
        packet["evidence"] = [{"finding_uid": "a" * 64,
                               "finding_quote": quote}]
        result = make_publishable_result(
            a_keys=("b1:c1:v1", "b1:c1:v2"), b_keys=("b46:c15:v50",),
            packets_b=[packet])
        manifest = result["manifest"]
        payload = result["stream_b_text"]

        # The old verifier rule really does over-count this record ...
        self.assertEqual(len(payload.splitlines()), 2)
        # ... while the record contract sees exactly the one record written.
        self.assertEqual(len(PACKETS.split_jsonl_records(payload)), 1)
        self.assertEqual(manifest["streams"][PACKETS.TRACK_B_STREAM]["packets"], 1)
        # The verifier no longer contains the buggy rule.
        source = inspect.getsource(PACKETS._verify_staged_artifact)
        self.assertNotIn("splitlines", source)
        self.assertIn("split_jsonl_records", source)

        destination = os.path.join(self.root, "artifact")
        written = PACKETS.write_artifacts(result, destination,
                                          require_pins=False)
        self.assertEqual(len(written), len(PACKETS.ARTIFACT_FILES))
        staged_b = os.path.join(destination, PACKETS.TRACK_B_STREAM)
        with open(staged_b, encoding="utf-8") as handle:
            raw = handle.read()
        self.assertEqual(len(PACKETS.split_jsonl_records(raw)), 1)
        self.assertEqual(
            PACKETS.records_with_unicode_line_boundary(raw), 1)
        self.assertEqual(PACKETS.sha256_text(raw),
                         manifest["streams"][PACKETS.TRACK_B_STREAM]["sha256"])

    def test_regression_blank_line_is_not_silently_accepted(self):
        # A genuinely extra blank record must still fail closed.
        result = make_publishable_result()
        result["stream_a_text"] = result["stream_a_text"] + "\n"
        result["manifest"]["streams"][PACKETS.TRACK_A_STREAM]["bytes"] = len(
            result["stream_a_text"].encode("utf-8"))
        result["manifest"]["streams"][PACKETS.TRACK_A_STREAM]["sha256"] = (
            PACKETS.sha256_text(result["stream_a_text"]))
        with self.assertRaises(PACKETS.PacketInputError) as caught:
            PACKETS.validate_publishable_result(result, require_pins=False)
        self.assertIn("does not match its record list", str(caught.exception))

    def test_regression_expected_stream_values_uses_record_contract(self):
        packet = make_packet(PACKETS.TRACK_B, "b46:c15:v50")
        packet["evidence"] = [{"finding_quote": "a \u2028 b"}]
        result = make_publishable_result(
            a_keys=("b1:c1:v1",), b_keys=("b46:c15:v50",), packets_b=[packet])
        values = PACKETS._expected_stream_values(result["manifest"])
        self.assertEqual(values[PACKETS.TRACK_B_STREAM]["packets"], 1)
        self.assertEqual(values[PACKETS.TRACK_B_STREAM]["bytes"],
                         len(result["stream_b_text"].encode("utf-8")))


@unittest.skipUnless(_FULL_ENABLED, "set {} =1 for the frozen-input audit".format(
    FULL_AUDIT_ENV))
class TrackCRealDataAuditTests(unittest.TestCase):
    """Track C invariants measured from the frozen inputs (no writes)."""

    @classmethod
    def setUpClass(cls):
        cls.paths = PACKETS.resolve_input_paths()
        cls.result = frozen_pinned_build()
        cls.audit = cls.result["audit"]

    def test_track_c_counts(self):
        track_c = self.audit["track_c"]
        self.assertEqual(track_c["packets"], 10)
        self.assertEqual(track_c["unique_verse_keys"], 10)
        self.assertEqual(track_c["raw_owner_note_occurrences"], 12)
        self.assertEqual(track_c["duplicate_owner_note_occurrences"], 1)
        self.assertEqual(track_c["unresolved_owner_references"], 0)
        self.assertEqual(track_c["owner_only_packets"], 6)
        self.assertEqual(track_c["pointer_records"], 4)

    def test_track_c_overlap_with_a_and_b_measured(self):
        track_c = self.audit["track_c"]
        self.assertEqual(track_c["overlap_with_track_a"], 0)
        self.assertEqual(track_c["overlap_with_track_b"], 4)
        self.assertEqual(track_c["overlap_verse_keys_with_track_a"], [])
        self.assertEqual(track_c["overlap_verse_keys_with_track_b"],
                         ["b24:c17:v9", "b39:c3:v17", "b43:c14:v2", "b49:c1:v14"])
        self.assertEqual(track_c["owner_only_verse_keys"],
                         ["b23:c35:v7", "b42:c15:v25", "b46:c2:v12",
                          "b62:c2:v20", "b62:c4:v2", "b65:c1:v1"])

    def test_review_universe_counts(self):
        universe = self.audit["review_universe"]
        self.assertEqual(universe["total_unique_verses"], 657)
        self.assertEqual(universe["duplicate_review_identities"], 0)
        self.assertEqual(universe["sources"]["track_a_only"], 335)
        self.assertEqual(universe["sources"]["track_b_only"], 312)
        self.assertEqual(universe["sources"]["track_c_only"], 6)
        self.assertEqual(universe["sources"]["owner_overlay_on_track_b"], 4)
        self.assertEqual(len(self.result["review_universe"]), 657)

    def test_track_c_owner_only_verses_have_archive_evidence_here(self):
        track_c = self.audit["track_c"]
        # Measured: all ten owner verses do have at least one archive finding,
        # so Track C is not evidence-free here; the threshold is what differs.
        self.assertEqual(track_c["owner_candidates_with_direct_archive_evidence"], 10)
        self.assertEqual(track_c["owner_candidates_without_direct_archive_evidence"], 0)
        self.assertIsNone(track_c["archive_evidence_threshold"])

    # (16) Track A stream is byte-identical to the pre-Track-C artifact.
    def test_track_a_bytes_and_sha_unchanged(self):
        serialization = self.audit["serialization"]
        self.assertEqual(
            serialization[PACKETS.TRACK_A_STREAM]["serialized_bytes_exact"],
            4394249)
        self.assertEqual(
            serialization[PACKETS.TRACK_A_STREAM]["serialized_sha256"],
            "be68fe90ecdd924d6b57cfc19055fe8c978dcf8ff87dbf388fc0f7c7b915d1cf")
        self.assertEqual(self.audit["track_a"]["packets"], 335)

    # (17) Track B stream is byte-identical to the pre-Track-C artifact.
    def test_track_b_bytes_and_sha_unchanged(self):
        serialization = self.audit["serialization"]
        self.assertEqual(
            serialization[PACKETS.TRACK_B_STREAM]["serialized_bytes_exact"],
            27657062)
        self.assertEqual(
            serialization[PACKETS.TRACK_B_STREAM]["serialized_sha256"],
            "b11d8176e4854930bd819da5911244c08129cf84425dd7e7e96633fe5e371f08")
        self.assertEqual(self.audit["track_b"]["packets"], 316)

    def test_embedded_note_references_are_not_track_c_or_in_the_overlay(self):
        # Scripture references that appear only inside raw owner notes or style
        # examples must not appear in the owner overlay; if such a verse is in the
        # review universe at all it is there because Track A/B selected it.
        overlay_keys = {r["verse_key"] for r in self.result["owner_overlay"]}
        for reference in ("Matthew 22:14", "John 8:29"):
            status, key = PACKETS.classify_owner_reference(reference)
            self.assertEqual(status, "mapped_verse")
            self.assertNotIn(key, overlay_keys)
            for row in self.result["review_universe"]:
                if row["verse_key"] == key:
                    self.assertFalse(row["in_track_c"])
                    self.assertNotEqual(row["packet_stream"],
                                        PACKETS.OWNER_OVERLAY_STREAM)

    def test_track_a_and_b_streams_still_avoid_duplicated_owner_payloads(self):
        by_key = {r["verse_key"]: r for r in self.result["owner_overlay"]}
        for verse_key, record in by_key.items():
            if record["owner_only"]:
                continue
            if record["existing_packet_track"] == PACKETS.TRACK_A:
                packet = next(p for p in self.result["packets_a"]
                              if p["verse_key"] == verse_key)
            else:
                packet = next(p for p in self.result["packets_b"]
                              if p["verse_key"] == verse_key)
            # The A/B packet itself is untouched by the owner overlay.
            self.assertNotIn("owner_input", packet)
