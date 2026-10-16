"""Focused tests for gd_bible_revision_mapping (GD Bible Revision Mapping V1).

Run:
    python3 -m unittest tests.test_gd_bible_revision_mapping -v
    GD_RUN_FULL_CORPUS_AUDIT=1 python3 -m unittest tests.test_gd_bible_revision_mapping -v

These tests cover the deterministic bridge only. They assert no Bible
translation decision and modify no Bible text.
"""

import contextlib
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

import gd_bible_revision_mapping as MAPPING  # noqa: E402
import gd_scripture_engine as ENGINE  # noqa: E402


DOC_SHA = "a" * 64
PASS_KEY = "0" * 23


def make_finding(refs=(), topic="scripture", quote="quoted evidence",
                 **extra):
    finding = {
        "topic": topic,
        "quote": quote,
        "note": "note text",
        "confidence": "high",
        "provenance": "in_chunk_exact",
        "speaker": "other",
        "char_start": 10,
        "char_end": 20,
        "occurrences": 1,
        "ambiguous": False,
        "in_chunk": True,
        "scripture_refs": list(refs),
        "verified": True,
    }
    finding.update(extra)
    return finding


def make_pass(key=PASS_KEY, findings=(), status="ok", quarantined=()):
    return {"key": key, "status": status,
            "verified": [dict(f) for f in findings],
            "quarantined": [dict(q) for q in quarantined]}


def make_passage(chunk_id="c0000", sha=DOC_SHA,
                 generation="fresh-2026-full-archive",
                 document="PCG/Test/doc.doc", screen=None, escalate=None):
    passes = {}
    if screen is not None:
        passes["screen"] = screen
    if escalate is not None:
        passes["escalate"] = escalate
    return {
        "chunk_id": chunk_id,
        "sha256": sha,
        "source_document": document,
        "source_collection": "PCG/Test",
        "current_path": document,
        "research_generation": generation,
        "chunk": {"passes": passes},
    }


def map_refs(refs, **finding_kwargs):
    """Map one synthetic finding carrying exactly ``refs``."""
    passage = make_passage(screen=make_pass(findings=[make_finding(refs, **finding_kwargs)]))
    finding_ref = next(MAPPING.iter_final_findings(passage))
    return MAPPING.map_finding(passage, finding_ref)


def outcome(row, index=0):
    return row["outcomes"][index]


def _read_lines(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read().splitlines()


class FinalPassSelectionTests(unittest.TestCase):
    def test_escalation_replaces_screen(self):
        passage = make_passage(
            screen=make_pass("s" * 23,
                             findings=[make_finding(["Rev. 5:10"], topic="screen")]),
            escalate=make_pass("e" * 23,
                               findings=[make_finding(["Rev. 5:10"], topic="escalated")]),
        )
        name, pass_obj = MAPPING.select_final_pass(passage)
        self.assertEqual(name, "escalate")
        self.assertEqual(pass_obj["key"], "e" * 23)
        findings = list(MAPPING.iter_final_findings(passage))
        self.assertEqual(len(findings), 1)
        # The screen-only finding must NOT also be counted.
        self.assertEqual(findings[0]["finding"]["topic"], "escalated")
        self.assertEqual(findings[0]["final_pass"], "escalate")

    def test_screen_used_when_no_escalation_exists(self):
        passage = make_passage(
            screen=make_pass("s" * 23, findings=[make_finding(["Rev. 5:10"])]))
        name, _ = MAPPING.select_final_pass(passage)
        self.assertEqual(name, "screen")
        findings = list(MAPPING.iter_final_findings(passage))
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["final_pass"], "screen")
        self.assertEqual(findings[0]["final_pass_key"], "s" * 23)

    def test_only_verified_true_entries_are_selected(self):
        not_verified = make_finding(["Rev. 5:10"])
        not_verified["verified"] = False
        passage = make_passage(screen=make_pass(
            findings=[make_finding(["Rev. 5:10"]), not_verified]))
        self.assertEqual(len(list(MAPPING.iter_final_findings(passage))), 1)


class IdentityTests(unittest.TestCase):
    def test_exact_identity_reconstruction(self):
        finding = make_finding(["Eph. 3:14-15"], topic="scripture")
        passage = make_passage(screen=make_pass(findings=[finding]))
        finding_ref = next(MAPPING.iter_final_findings(passage))
        identity = MAPPING.build_identity(passage, finding_ref)

        expected_payload = {
            "identity_version": MAPPING.IDENTITY_VERSION,
            "source_document_sha256": DOC_SHA,
            "source_document": "PCG/Test/doc.doc",
            "chunk_id": "c0000",
            "research_generation": "fresh-2026-full-archive",
            "final_pass": "screen",
            "final_pass_key": PASS_KEY,
            "finding_index": 0,
            "finding_topic": "scripture",
            "finding_char_start": 10,
            "finding_char_end": 20,
            "finding_quote_sha256": hashlib.sha256(
                b"quoted evidence").hexdigest(),
        }
        self.assertEqual(identity, expected_payload)

        canonical = json.dumps(expected_payload, sort_keys=True,
                               separators=(",", ":"), ensure_ascii=False)
        expected_uid = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        self.assertEqual(MAPPING.finding_uid(identity), expected_uid)
        self.assertEqual(len(expected_uid), 64)

        row = MAPPING.map_finding(passage, finding_ref)
        self.assertEqual(row["finding_uid"], expected_uid)

    def test_uid_distinguishes_two_findings_from_same_passage(self):
        first = make_finding(["Rev. 5:10"], char_start=1)
        second = make_finding(["Rev. 5:10"], char_start=99, char_end=120)
        passage = make_passage(screen=make_pass(findings=[first, second]))
        rows = [MAPPING.map_finding(passage, fr)
                for fr in MAPPING.iter_final_findings(passage)]
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(rows[0]["finding_uid"], rows[1]["finding_uid"])

    def test_uid_is_stable_for_identical_finding(self):
        finding = make_finding(["Rev. 5:10"])
        passage = make_passage(screen=make_pass(findings=[finding]))
        finding_ref = next(MAPPING.iter_final_findings(passage))
        self.assertEqual(MAPPING.finding_uid(MAPPING.build_identity(passage, finding_ref)),
                         MAPPING.finding_uid(MAPPING.build_identity(passage, finding_ref)))

    def test_duplicate_finding_uid_prevention(self):
        guard = MAPPING.FindingUidGuard()
        self.assertTrue(guard.add("deadbeef"))
        self.assertFalse(guard.add("deadbeef"))
        self.assertEqual(guard.collisions, 1)
        self.assertEqual(len(guard), 1)
        guard.add("cafebabe")
        self.assertEqual(len(guard), 2)

    def test_index_is_part_of_identity(self):
        finding = make_finding(["Rev. 5:10"])
        passage = make_passage(screen=make_pass(findings=[finding]))
        ref_a = {"final_pass": "screen", "final_pass_key": PASS_KEY,
                 "finding_index": 0, "finding": finding}
        ref_b = dict(ref_a, finding_index=1)
        self.assertNotEqual(
            MAPPING.finding_uid(MAPPING.build_identity(passage, ref_a)),
            MAPPING.finding_uid(MAPPING.build_identity(passage, ref_b)))


class RawReferencePreservationTests(unittest.TestCase):
    def test_raw_scripture_refs_preserved_verbatim(self):
        raw_refs = ["Heb. 8:8, 13", "12:24", "  Gen. 9:8 ", "Rev. 12.10",
                    "Esther 13:12-14", ""]
        row = map_refs(raw_refs)
        self.assertEqual(row["raw_scripture_refs"], raw_refs)
        for index, raw in enumerate(raw_refs):
            self.assertEqual(outcome(row, index)["raw"], raw)
        self.assertEqual(row["raw_reference_count"], len(raw_refs))

    def test_finding_with_no_refs_is_still_a_valid_finding_row(self):
        row = map_refs([])
        self.assertEqual(row["raw_reference_count"], 0)
        self.assertEqual(row["mapped_verse_count"], 0)
        self.assertFalse(row["has_verse_mapping"])
        self.assertTrue(row["finding_uid"])
        self.assertEqual(row["outcomes"], [])
        self.assertEqual(row["raw_scripture_refs"], [])

    def test_empty_refs_array_and_missing_key_both_yield_empty(self):
        row = map_refs([])
        self.assertEqual(row["raw_reference_count"], 0)
        finding = make_finding()
        del finding["scripture_refs"]
        passage = make_passage(screen=make_pass(findings=[finding]))
        row = MAPPING.map_finding(passage, next(MAPPING.iter_final_findings(passage)))
        self.assertEqual(row["raw_scripture_refs"], [])
        self.assertEqual(row["raw_reference_count"], 0)


class MappingClassificationTests(unittest.TestCase):
    def test_simple_verse_mapping(self):
        row = map_refs(["Rev. 5:10"])
        item = outcome(row)
        self.assertEqual(item["status"], MAPPING.STATUS_MAPPED_VERSE)
        self.assertEqual(item["canonical_verse_keys"], ["b66:c5:v10"])
        self.assertEqual(row["mapped_verse_keys"], ["b66:c5:v10"])

    def test_verse_list_mapping(self):
        row = map_refs(["Heb. 8:8, 13"])
        item = outcome(row)
        self.assertEqual(item["status"], MAPPING.STATUS_MAPPED_VERSE)
        self.assertEqual(item["canonical_verse_keys"], ["b58:c8:v13", "b58:c8:v8"])

    def test_same_chapter_range_expansion(self):
        row = map_refs(["Eph. 3:14-15"])
        item = outcome(row)
        self.assertEqual(item["status"], MAPPING.STATUS_MAPPED_RANGE)
        self.assertEqual(item["canonical_verse_keys"],
                         ["b49:c3:v14", "b49:c3:v15"])
        self.assertEqual(row["mapped_verse_count"], 2)

    def test_cross_chapter_range_expansion(self):
        row = map_refs(["Romans 8:18-9:5"])
        item = outcome(row)
        self.assertEqual(item["status"], MAPPING.STATUS_MAPPED_RANGE)
        keys = item["canonical_verse_keys"]
        # Romans 8 has 39 verses; 8:18..8:39 = 22 verses, 9:1..9:5 = 5 verses.
        self.assertEqual(len(keys), 27)
        self.assertEqual(keys[0], "b45:c8:v18")
        self.assertEqual(keys[-1], "b45:c9:v5")
        self.assertIn("b45:c8:v39", keys)
        self.assertIn("b45:c9:v1", keys)
        self.assertNotIn("b45:c9:v6", keys)

    def test_duplicate_verse_mapping_deduplicated_per_finding(self):
        # "Eph. 3:14-15" and "Eph. 3:14" describe the same coordinate twice.
        row = map_refs(["Eph. 3:14-15", "Eph. 3:14"])
        self.assertEqual(row["mapped_verse_keys"], ["b49:c3:v14", "b49:c3:v15"])
        self.assertEqual(row["mapped_verse_count"], 2)
        self.assertEqual(row["duplicate_mappings_removed"], 1)
        self.assertEqual(row["expanded_mapping_count"], 3)
        # raw occurrences are preserved separately, not lost by dedup
        self.assertEqual(outcome(row, 0)["canonical_verse_keys"],
                         ["b49:c3:v14", "b49:c3:v15"])
        self.assertEqual(outcome(row, 1)["canonical_verse_keys"], ["b49:c3:v14"])
        sources = {entry["verse_key"]: entry["raw_refs"]
                   for entry in row["verse_key_sources"]}
        self.assertEqual(sources["b49:c3:v14"], ["Eph. 3:14-15", "Eph. 3:14"])
        self.assertEqual(sources["b49:c3:v15"], ["Eph. 3:14-15"])

    def test_asserted_invalid_does_not_map(self):
        for raw in ("Esther 13:12-14", "Jude 3:4", "Romans 6:34"):
            with self.subTest(raw=raw):
                row = map_refs([raw])
                item = outcome(row)
                self.assertEqual(item["status"], MAPPING.STATUS_ASSERTED_INVALID)
                self.assertEqual(item["canonical_verse_keys"], [])
                self.assertEqual(row["mapped_verse_keys"], [])
                self.assertIn("asserted_invalid",
                              item["engine_rows"][0]["canonical_status"])

    def test_bare_chapter_verse_does_not_inherit_previous_array_element(self):
        row = map_refs(["Heb. 8:8, 13", "12:24"])
        self.assertEqual(outcome(row, 0)["status"], MAPPING.STATUS_MAPPED_VERSE)
        self.assertEqual(outcome(row, 1)["status"], MAPPING.STATUS_UNRESOLVED)
        self.assertEqual(outcome(row, 1)["canonical_verse_keys"], [])
        # No Hebrews 12:24 (or any chapter 12) may appear from the bare element.
        for key in row["mapped_verse_keys"]:
            self.assertTrue(key.startswith("b58:c8:"), key)

    def test_chapter_only_does_not_become_verse(self):
        row = map_refs(["Matthew 24"])
        item = outcome(row)
        self.assertEqual(item["status"], MAPPING.STATUS_CHAPTER_ONLY)
        self.assertEqual(item["canonical_verse_keys"], [])
        self.assertEqual(row["mapped_verse_keys"], [])
        self.assertEqual(item["context"], "Matthew 24")

    def test_book_only_does_not_become_verse(self):
        row = map_refs(["Revelation"])
        item = outcome(row)
        self.assertEqual(item["status"], MAPPING.STATUS_BOOK_ONLY)
        self.assertEqual(item["canonical_verse_keys"], [])
        self.assertEqual(row["mapped_verse_keys"], [])
        self.assertEqual(item["context"], "Revelation")

    def test_unstructured_does_not_become_verse(self):
        for raw in ("verse 5", "Antiq. 11.11"):
            with self.subTest(raw=raw):
                row = map_refs([raw])
                self.assertEqual(outcome(row)["status"], MAPPING.STATUS_UNSTRUCTURED)
                self.assertEqual(row["mapped_verse_keys"], [])

    def test_partial_prose_reference_is_not_silently_accepted(self):
        raw = "Genesis 1:26-27; James 3:9, last part"
        row = map_refs([raw])
        item = outcome(row)
        self.assertEqual(item["status"], MAPPING.STATUS_PARTIAL_PARSE)
        self.assertEqual(item["canonical_verse_keys"], [])
        self.assertEqual(row["mapped_verse_keys"], [])
        self.assertIn("last", item["unexplained_tokens"])
        # the recognised rows are preserved for review, not mapped
        self.assertTrue(item["engine_rows"])
        self.assertTrue(item["normalized_references"])

    def test_prose_around_a_valid_reference_is_partial(self):
        raw = "Paul wrote about this in Romans 8:18 to the church"
        row = map_refs([raw])
        item = outcome(row)
        self.assertEqual(item["status"], MAPPING.STATUS_PARTIAL_PARSE)
        self.assertEqual(row["mapped_verse_keys"], [])

    def test_citation_connectors_are_harmless(self):
        row = map_refs(["Jude 3 and 19"])
        item = outcome(row)
        self.assertEqual(item["status"], MAPPING.STATUS_MAPPED_VERSE)
        self.assertEqual(item["canonical_verse_keys"],
                         ["b65:c1:v19", "b65:c1:v3"])

    def test_partial_parse_never_yields_an_embedded_valid_mapping(self):
        row = map_refs(["Revelation 3:7:13"])
        item = outcome(row)
        self.assertEqual(item["status"], MAPPING.STATUS_PARTIAL_PARSE)
        self.assertEqual(item["canonical_verse_keys"], [])
        self.assertEqual(row["mapped_verse_keys"], [])


class RepresentativeRealFormTests(unittest.TestCase):
    """The exact forms the milestone names, end to end."""

    def test_eph_3_14_15(self):
        item = outcome(map_refs(["Eph. 3:14-15"]))
        self.assertEqual(item["status"], MAPPING.STATUS_MAPPED_RANGE)
        self.assertEqual(item["canonical_verse_keys"],
                         ["b49:c3:v14", "b49:c3:v15"])

    def test_heb_8_8_13(self):
        item = outcome(map_refs(["Heb. 8:8, 13"]))
        self.assertEqual(item["status"], MAPPING.STATUS_MAPPED_VERSE)
        self.assertEqual(item["canonical_verse_keys"],
                         ["b58:c8:v13", "b58:c8:v8"])

    def test_romans_8_18_to_9_5(self):
        item = outcome(map_refs(["Romans 8:18-9:5"]))
        self.assertEqual(item["status"], MAPPING.STATUS_MAPPED_RANGE)
        self.assertEqual(len(item["canonical_verse_keys"]), 27)

    def test_jude_6(self):
        item = outcome(map_refs(["Jude 6"]))
        self.assertEqual(item["status"], MAPPING.STATUS_MAPPED_VERSE)
        self.assertEqual(item["canonical_verse_keys"], ["b65:c1:v6"])

    def test_hab_1_3_4_european_comma(self):
        item = outcome(map_refs(["Hab. 1,3-4"]))
        self.assertEqual(item["status"], MAPPING.STATUS_MAPPED_RANGE)
        self.assertEqual(item["canonical_verse_keys"],
                         ["b35:c1:v3", "b35:c1:v4"])

    def test_malformed_and_invalid_references_are_never_mapped(self):
        cases = {
            "Esther 13:12-14": MAPPING.STATUS_ASSERTED_INVALID,
            "Nehemiah 25": MAPPING.STATUS_ASSERTED_INVALID,
            "12:24": MAPPING.STATUS_UNRESOLVED,
            "Hezekiah 1:1": MAPPING.STATUS_UNRESOLVED,
            "": MAPPING.STATUS_UNSTRUCTURED,
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                row = map_refs([raw])
                self.assertEqual(outcome(row)["status"], expected)
                self.assertEqual(row["mapped_verse_keys"], [])


class VerseEvidenceTests(unittest.TestCase):
    def test_verse_evidence_rows_are_one_per_unique_pair(self):
        row = map_refs(["Eph. 3:14-15", "Eph. 3:14"])
        rows = list(MAPPING.verse_evidence_rows(row))
        self.assertEqual(len(rows), 2)
        keys = [r["verse_key"] for r in rows]
        self.assertEqual(keys, sorted(set(keys)))
        self.assertEqual(rows[0]["canonical"], "Ephesians 3:14")
        self.assertEqual(rows[0]["book_id"], 49)
        self.assertEqual(rows[0]["finding_uid"], row["finding_uid"])
        self.assertEqual(rows[0]["raw_refs"], ["Eph. 3:14-15", "Eph. 3:14"])

    def test_anomaly_rows_cover_every_non_mapped_raw_reference(self):
        raw_refs = ["Matthew 24", "Revelation", "12:24", "Esther 13:12-14",
                    "verse 5", "Genesis 1:26-27; James 3:9, last part"]
        row = map_refs(raw_refs)
        statuses = sorted(a["status"] for a in MAPPING.anomaly_rows(row))
        self.assertEqual(statuses, sorted([
            MAPPING.STATUS_CHAPTER_ONLY, MAPPING.STATUS_BOOK_ONLY,
            MAPPING.STATUS_UNRESOLVED, MAPPING.STATUS_ASSERTED_INVALID,
            MAPPING.STATUS_UNSTRUCTURED, MAPPING.STATUS_PARTIAL_PARSE,
        ]))

    def test_mapped_rows_emit_no_anomaly_unless_embedded_anomaly(self):
        row = map_refs(["Eph. 3:14-15"])
        self.assertEqual(list(MAPPING.anomaly_rows(row)), [])

    def test_expansion_never_guesses_across_invalid_coordinates(self):
        table = ENGINE.CANONICAL_COORDINATES
        # Reverse span yields nothing rather than a guessed range.
        row = {"canonical_status": "asserted_valid", "granularity": "range",
               "book": "Jude", "book_id": 65, "chapter": 1,
               "verse_start": 20, "verse_end": 5, "chapter_end": None}
        self.assertEqual(MAPPING.expand_verse_keys(row, table), [])
        # Out-of-range coordinate is skipped, never clamped.
        row = {"canonical_status": "asserted_valid", "granularity": "verse",
               "book": "Jude", "book_id": 65, "chapter": 1, "verse_start": 999,
               "verse_end": None, "chapter_end": None}
        self.assertEqual(MAPPING.expand_verse_keys(row, table), [])
        # Non-asserted rows never expand.
        row = {"canonical_status": "asserted_invalid", "granularity": "verse",
               "book": "Jude", "book_id": 65, "chapter": 1, "verse_start": 6,
               "verse_end": None, "chapter_end": None}
        self.assertEqual(MAPPING.expand_verse_keys(row, table), [])

    def test_canonical_coordinate_system_is_the_pinned_one(self):
        table = ENGINE.CANONICAL_COORDINATES
        self.assertIsNotNone(
            table, "pinned canonical coordinate table must load")
        self.assertEqual(len(table), 66)
        self.assertEqual(sum(len(v) for v in table.values()), 1189)
        self.assertEqual(sum(sum(v) for v in table.values()), 31102)


class DeterminismAndArtifactTests(unittest.TestCase):
    def _write_fixture_corpus(self, path):
        passages = [
            make_passage(chunk_id="c0000", screen=make_pass(findings=[
                make_finding(["Eph. 3:14-15", "Heb. 8:8, 13", "12:24"]),
                make_finding(["Genesis 1:26-27; James 3:9, last part"],
                             topic="terminology"),
                make_finding([], topic="wording"),
            ])),
            make_passage(chunk_id="c0001", sha="b" * 64,
                         generation="historical-validated-reuse",
                         screen=make_pass("s2" + "0" * 21,
                                          findings=[make_finding(["Revelation 5:10"])]),
                         escalate=make_pass("e2" + "0" * 21, findings=[
                             make_finding(["Romans 8:18-9:5"]),
                             make_finding(["Matthew 24"]),
                         ])),
        ]
        with open(path, "w", encoding="utf-8") as handle:
            for passage in passages:
                handle.write(json.dumps(passage) + "\n")
        return passages

    def test_deterministic_rerun_produces_identical_identities_and_mappings(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus = os.path.join(tmp, "combined.jsonl")
            self._write_fixture_corpus(corpus)
            first = MAPPING.audit_corpus(corpus, samples=3)
            second = MAPPING.audit_corpus(corpus, samples=3)
            self.assertEqual(MAPPING.canonical_json(first),
                             MAPPING.canonical_json(second))

            out_a = os.path.join(tmp, "a")
            out_b = os.path.join(tmp, "b")
            MAPPING.write_artifacts(corpus, out_a, generated_at="T", pinned=False)
            MAPPING.write_artifacts(corpus, out_b, generated_at="T", pinned=False)
            for name in ("finding_reference_map.jsonl",
                         "verse_evidence_index.jsonl",
                         "reference_anomalies.jsonl", "manifest.json"):
                with open(os.path.join(out_a, name), "rb") as fa, \
                        open(os.path.join(out_b, name), "rb") as fb:
                    self.assertEqual(fa.read(), fb.read(), name)

    def test_written_artifacts_carry_required_metadata_and_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus = os.path.join(tmp, "combined.jsonl")
            self._write_fixture_corpus(corpus)
            out = os.path.join(tmp, "out")
            manifest = MAPPING.write_artifacts(corpus, out,
                                              generated_at="2026-10-14T00:00:00+00:00",
                                              pinned=False)
            for field in ("schema_version", "mapper_version",
                          "engine_version", "input_research_artifact_sha256",
                          "canonical_coordinates_sha256", "generated_at",
                          "counts", "provenance"):
                self.assertIn(field, manifest)
            self.assertEqual(manifest["counts"]["passages"], 2)
            # screen passage: 3 findings; escalated passage: 2 findings
            self.assertEqual(manifest["counts"]["findings"], 5)
            self.assertEqual(manifest["counts"]["finding_uid_collisions"], 0)
            self.assertEqual(manifest["final_pass_rule"], MAPPING.FINAL_PASS_RULE)

            map_rows = [json.loads(line) for line in
                        _read_lines(os.path.join(
                            out, "finding_reference_map.jsonl"))]
            self.assertEqual(len(map_rows), 5)
            self.assertEqual(len({r["finding_uid"] for r in map_rows}), 5)
            for row in map_rows:
                self.assertEqual(row["schema_version"], MAPPING.SCHEMA_VERSION)

            verse_rows = [json.loads(line) for line in
                          _read_lines(os.path.join(
                              out, "verse_evidence_index.jsonl"))]
            self.assertTrue(verse_rows)
            self.assertTrue(all(r["mapper_version"] == MAPPING.MAPPER_VERSION
                                for r in verse_rows))

    def test_audit_corpus_counts_fixture_correctly(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus = os.path.join(tmp, "combined.jsonl")
            self._write_fixture_corpus(corpus)
            summary = MAPPING.audit_corpus(corpus, samples=5)
            self.assertEqual(summary["passage_records"], 2)
            self.assertEqual(summary["final_verified_findings"], 5)
            self.assertEqual(summary["unique_finding_uids"], 5)
            self.assertEqual(summary["finding_uid_collisions"], 0)
            self.assertEqual(summary["findings_with_no_scripture_refs"], 1)
            self.assertEqual(summary["total_raw_reference_strings"], 6)
            self.assertEqual(summary["passages_with_escalation_pass"], 1)
            self.assertEqual(
                summary["counts_by_research_generation"],
                {"fresh-2026-full-archive": 3,
                 "historical-validated-reuse": 2})
            self.assertEqual(summary["mixed_context_raw_refs"], 0)
            self.assertIn(MAPPING.STATUS_PARTIAL_PARSE, summary["samples"])
            self.assertIn(MAPPING.STATUS_UNRESOLVED, summary["samples"])

    def test_audit_only_creates_no_output_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus = os.path.join(tmp, "combined.jsonl")
            self._write_fixture_corpus(corpus)
            before = set(os.listdir(tmp))
            MAPPING.audit_corpus(corpus, samples=1)
            self.assertEqual(set(os.listdir(tmp)), before)


class StrictResidualConsumptionTests(unittest.TestCase):
    """The residual rule must be ACTUALLY strict: characters and words."""

    def test_prose_words_after_a_reference_are_partial(self):
        for raw in ("John 3:16 now", "John 3:16 then", "John 3:16 about",
                    "John 3:16 written", "John 3:16 found", "John 3:16 to",
                    "John 3:16 from", "John 3:16 of", "John 3:16 the"):
            with self.subTest(raw=raw):
                row = map_refs([raw])
                item = outcome(row)
                self.assertEqual(item["status"], MAPPING.STATUS_PARTIAL_PARSE)
                self.assertEqual(item["canonical_verse_keys"], [])
                self.assertEqual(row["mapped_verse_keys"], [])
                # recognised engine rows are preserved for review
                self.assertTrue(item["engine_rows"])
                self.assertTrue(item["normalized_references"])

    def test_engine_only_cue_words_are_not_treated_as_harmless(self):
        # Words the PARSER uses for citation structure must not make unexplained
        # prose harmless in the mapping layer.
        forbidden = {"now", "then", "about", "written", "found", "to", "from",
                     "of", "with", "for", "as", "the", "a", "an", "in", "read",
                     "notice", "book", "epistle"}
        self.assertFalse(forbidden & set(MAPPING.HARMLESS_RESIDUAL_WORDS))
        for word in sorted(forbidden):
            with self.subTest(word=word):
                self.assertNotIn(word, MAPPING.HARMLESS_RESIDUAL_WORDS)

    def test_harmless_word_vocabulary_is_connectors_only(self):
        self.assertEqual(set(MAPPING.HARMLESS_RESIDUAL_WORDS),
                         set(ENGINE._CITATION_CONNECTORS))

    def test_unlisted_symbol_is_partial(self):
        for symbol in ("\U0001f4a5", "$", "#", "@", "+", "*", "=", "~", "^",
                       "%", "\u00b0"):
            raw = "John 3:16 " + symbol
            with self.subTest(symbol=repr(symbol)):
                row = map_refs([raw])
                item = outcome(row)
                self.assertEqual(item["status"], MAPPING.STATUS_PARTIAL_PARSE)
                self.assertEqual(row["mapped_verse_keys"], [])
                self.assertIn(symbol, item["unexplained_symbols"])

    def test_allowed_citation_punctuation_does_not_cause_false_partial(self):
        expected = {
            "John 3:16.": ["b43:c3:v16"],
            "John 3:16,": ["b43:c3:v16"],
            "(John 3:16)": ["b43:c3:v16"],
            "John 3:16-17": ["b43:c3:v16", "b43:c3:v17"],
            "John 3:16\u201317": ["b43:c3:v16", "b43:c3:v17"],
        }
        for raw, keys in expected.items():
            with self.subTest(raw=raw):
                row = map_refs([raw])
                self.assertIn(outcome(row)["status"],
                              MAPPING.VERSE_MAPPED_STATUSES)
                self.assertEqual(row["mapped_verse_keys"], keys)
                self.assertEqual(outcome(row)["unexplained_tokens"], [])
                self.assertEqual(outcome(row)["unexplained_symbols"], [])

    def test_separators_the_engine_does_not_recognise_are_partial_not_guessed(self):
        # A semicolon does not continue a bare verse list and an em dash is not
        # an engine range separator, so the mapper refuses to guess the
        # coordinate even though the trailing symbol belongs to the harmless
        # allowlist: the digit run is unexplained.
        for raw in ("John 3:16; 17", "John 3:16 \u2014 17"):
            with self.subTest(raw=raw):
                row = map_refs([raw])
                self.assertEqual(outcome(row)["status"],
                                 MAPPING.STATUS_PARTIAL_PARSE)
                self.assertEqual(row["mapped_verse_keys"], [])
                self.assertEqual(outcome(row)["unexplained_tokens"], ["17"])

    def test_connectors_still_accepted(self):
        row = map_refs(["Jude 3 and 19"])
        self.assertEqual(outcome(row)["status"], MAPPING.STATUS_MAPPED_VERSE)
        self.assertEqual(row["mapped_verse_keys"], ["b65:c1:v19", "b65:c1:v3"])
        row = map_refs(["Revelation 16:1-4 ff"])
        self.assertEqual(outcome(row)["status"], MAPPING.STATUS_MAPPED_RANGE)
        self.assertTrue(row["mapped_verse_keys"])

    def test_rejected_raw_strings_keep_their_engine_rows(self):
        row = map_refs(["John 3:16 now"])
        item = outcome(row)
        self.assertEqual(item["status"], MAPPING.STATUS_PARTIAL_PARSE)
        self.assertTrue(item["engine_rows"])
        self.assertEqual(item["engine_rows"][0]["canonical"], "John 3:16")
        self.assertIn("now", item["unexplained_tokens"])


class MixedContextTests(unittest.TestCase):
    """``mixed_context`` must be a NON-MAPPED state with an anomaly row."""

    @staticmethod
    def _mixed_rows(raw):
        return [
            {"canonical": "John 3:16", "reference_key": "b43:c3:v16",
             "granularity": "verse", "canonical_status": "asserted_valid",
             "canonical_issues": [], "resolution_status": "syntactically_parsed",
             "citation_context": "explicit", "raw_match": raw,
             "start_offset": 0, "end_offset": len(raw)},
            {"canonical": "John 4", "reference_key": "b43:c4",
             "granularity": "chapter", "canonical_status": "asserted_valid",
             "canonical_issues": [], "resolution_status": "syntactically_parsed",
             "citation_context": "standalone", "raw_match": raw,
             "start_offset": 0, "end_offset": len(raw)},
        ]

    def test_mixed_context_status_is_non_mapped(self):
        self.assertIn(MAPPING.STATUS_MIXED_CONTEXT, MAPPING.NON_MAPPED_STATUSES)
        self.assertNotIn(MAPPING.STATUS_MIXED_CONTEXT, MAPPING.MAPPED_STATUSES)
        self.assertNotIn(MAPPING.STATUS_MIXED_CONTEXT,
                         MAPPING.VERSE_MAPPED_STATUSES)

    def test_mixed_context_produces_no_verse_but_one_anomaly(self):
        raw = "John 3:16"
        with mock.patch.object(MAPPING.ENGINE, "extract_references",
                               return_value=self._mixed_rows(raw)):
            core = MAPPING.classify_raw_reference(raw)
            self.assertEqual(core["status"], MAPPING.STATUS_MIXED_CONTEXT)
            self.assertEqual(core["verse_keys"], [])
            self.assertEqual(len(core["engine_rows"]), 2)

            row = map_refs([raw])
            self.assertEqual(row["mapped_verse_keys"], [])
            self.assertEqual(row["mapped_verse_count"], 0)
            self.assertFalse(row["has_verse_mapping"])
            self.assertEqual(
                row["status_counts"], {MAPPING.STATUS_MIXED_CONTEXT: 1})
            self.assertEqual(list(MAPPING.verse_evidence_rows(row)), [])
            anomalies = list(MAPPING.anomaly_rows(row))
            self.assertEqual(len(anomalies), 1)
            self.assertEqual(anomalies[0]["status"],
                             MAPPING.STATUS_MIXED_CONTEXT)
            self.assertEqual(anomalies[0]["anomaly_kind"], "raw_reference")
            # no evidence disappears: both engine rows are preserved
            self.assertEqual(len(anomalies[0]["engine_rows"]), 2)

    def test_mixed_context_is_counted_in_audit_and_anomalies(self):
        raw = "John 3:16"
        with tempfile.TemporaryDirectory() as tmp:
            corpus = os.path.join(tmp, "combined.jsonl")
            passage = make_passage(
                screen=make_pass(findings=[make_finding([raw])]))
            with open(corpus, "w", encoding="utf-8") as handle:
                handle.write(json.dumps(passage) + "\n")
            with mock.patch.object(MAPPING.ENGINE, "extract_references",
                                   return_value=self._mixed_rows(raw)):
                summary = MAPPING.audit_corpus(corpus, samples=5)
            self.assertEqual(summary["mixed_context_raw_refs"], 1)
            self.assertEqual(summary["mapped_verse_raw_refs"], 0)
            self.assertEqual(summary["unique_finding_verse_mappings"], 0)
            self.assertIn(MAPPING.STATUS_MIXED_CONTEXT, summary["samples"])


class RangeExpansionFailSafeTests(unittest.TestCase):
    """Ranges must expand fully or not at all -- never clamped, never partial."""

    TABLE = ENGINE.CANONICAL_COORDINATES

    @staticmethod
    def _range_row(book="Romans", book_id=45, chapter=8, verse_start=18,
                   chapter_end=9, verse_end=5):
        return {"canonical_status": "asserted_valid", "granularity": "range",
                "book": book, "book_id": book_id, "chapter": chapter,
                "verse_start": verse_start, "chapter_end": chapter_end,
                "verse_end": verse_end}

    def test_reference_span_still_expands_exactly(self):
        keys = MAPPING.expand_verse_keys(self._range_row(), self.TABLE)
        self.assertEqual(len(keys), 27)
        self.assertEqual(keys[0], "b45:c8:v18")
        self.assertEqual(keys[-1], "b45:c9:v5")
        self.assertEqual(keys.count("b45:c8:v39"), 1)
        self.assertEqual(keys.count("b45:c9:v1"), 1)

    def test_verse_start_zero_is_rejected(self):
        row = self._range_row(verse_start=0)
        self.assertEqual(MAPPING.expand_verse_keys(row, self.TABLE), [])

    def test_verse_start_beyond_chapter_length_is_rejected(self):
        # Romans 8 has 39 verses.
        limit = self.TABLE["Romans"][7]
        row = self._range_row(verse_start=limit + 1)
        self.assertEqual(MAPPING.expand_verse_keys(row, self.TABLE), [])

    def test_verse_end_zero_is_rejected(self):
        row = self._range_row(chapter_end=9, verse_end=0)
        self.assertEqual(MAPPING.expand_verse_keys(row, self.TABLE), [])

    def test_verse_end_beyond_final_chapter_length_is_rejected(self):
        limit = self.TABLE["Romans"][8]
        row = self._range_row(chapter_end=9, verse_end=limit + 1)
        self.assertEqual(MAPPING.expand_verse_keys(row, self.TABLE), [])

    def test_invalid_start_does_not_map_later_chapters(self):
        row = self._range_row(verse_start=99)
        keys = MAPPING.expand_verse_keys(row, self.TABLE)
        self.assertEqual(keys, [])
        self.assertFalse([k for k in keys if k.startswith("b45:c9:")])

    def test_invalid_end_does_not_map_earlier_chapters(self):
        row = self._range_row(chapter_end=9, verse_end=99)
        keys = MAPPING.expand_verse_keys(row, self.TABLE)
        self.assertEqual(keys, [])
        self.assertFalse([k for k in keys if k.startswith("b45:c8:")])

    def test_chapter_out_of_range_is_rejected_without_clamping(self):
        row = self._range_row(chapter=99, verse_start=1, chapter_end=99,
                              verse_end=5)
        self.assertEqual(MAPPING.expand_verse_keys(row, self.TABLE), [])
        row = self._range_row(chapter_end=99, verse_end=5)
        self.assertEqual(MAPPING.expand_verse_keys(row, self.TABLE), [])

    def test_reversed_range_is_rejected(self):
        self.assertEqual(
            MAPPING.expand_verse_keys(self._range_row(verse_start=20,
                                                      verse_end=5,
                                                      chapter_end=None),
                                      self.TABLE), [])
        # reversed across chapters as well
        self.assertEqual(
            MAPPING.expand_verse_keys(self._range_row(chapter=9,
                                                      verse_start=5,
                                                      chapter_end=8,
                                                      verse_end=18),
                                      self.TABLE), [])

    def test_intermediate_chapters_expand_completely(self):
        row = self._range_row(chapter=8, verse_start=39, chapter_end=10,
                              verse_end=1)
        keys = MAPPING.expand_verse_keys(row, self.TABLE)
        romans_ch9_verses = self.TABLE["Romans"][8]
        expected = 1 + romans_ch9_verses + 1
        self.assertEqual(len(keys), expected)
        self.assertIn("b45:c9:v1", keys)
        self.assertIn("b45:c9:v{}".format(romans_ch9_verses), keys)

    def test_no_clamping_helpers_remain(self):
        import inspect
        source = inspect.getsource(MAPPING.expand_verse_keys)
        self.assertNotIn("max(start", source)
        self.assertNotIn("min(end", source)


class ProductionPinTests(unittest.TestCase):
    """Pinned production inputs must fail closed before any file is created."""

    def _write_corpus(self, path):
        passage = make_passage(screen=make_pass(
            findings=[make_finding(["Rev. 5:10"])]))
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(passage) + "\n")

    def test_pins_validate_on_the_real_pinned_checkout(self):
        if not os.path.exists(MAPPING.DEFAULT_RESEARCH_ARTIFACT):
            self.skipTest("combined research artifact not present")
        pinned = MAPPING.validate_production_inputs(
            MAPPING.DEFAULT_RESEARCH_ARTIFACT)
        self.assertEqual(pinned["engine_version"], "1.5.0")
        self.assertEqual(pinned["engine_file_sha256"],
                         MAPPING.EXPECTED_ENGINE_FILE_SHA256)
        self.assertEqual(pinned["canonical_coordinates_sha256"],
                         MAPPING.EXPECTED_COORDINATES_SHA256)
        self.assertEqual(pinned["research_artifact_sha256"],
                         MAPPING.EXPECTED_RESEARCH_SHA256)
        self.assertEqual(pinned["canonical_coordinate_counts"],
                         {"book_count": 66, "chapter_count": 1189,
                          "verse_count": 31102})

    def test_pin_constants_match_the_reviewed_hashes(self):
        self.assertEqual(
            MAPPING.EXPECTED_ENGINE_FILE_SHA256,
            "7e336688d359693b046034a7bf49b827e1edc06da510f3bbb8a9310833b670fa")
        self.assertEqual(
            MAPPING.EXPECTED_COORDINATES_SHA256,
            "a0d2c672f6c06f3307c22027216ae53f98bdf910903ef86c049fbbdeb4e9753f")
        self.assertEqual(
            MAPPING.EXPECTED_RESEARCH_SHA256,
            "a9cc75dcc664e77811f646053b5c0748ad6a14907c7d84e2c2323abc93bda92a")

    def test_write_is_pinned_by_default_and_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus = os.path.join(tmp, "combined.jsonl")
            self._write_corpus(corpus)
            out = os.path.join(tmp, "out")
            with self.assertRaises(MAPPING.ProductionInputError) as ctx:
                MAPPING.write_artifacts(corpus, out)
            self.assertIn("research artifact sha256", str(ctx.exception))
            # nothing was created before validation
            self.assertFalse(os.path.exists(out))

    def test_unpinned_inputs_are_an_explicit_test_only_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus = os.path.join(tmp, "combined.jsonl")
            self._write_corpus(corpus)
            out = os.path.join(tmp, "out")
            manifest = MAPPING.write_artifacts(corpus, out, pinned=False,
                                               generated_at="T")
            self.assertFalse(manifest["inputs_pinned"])
            self.assertFalse(manifest["production_pins"]["pins_enforced"])
            self.assertTrue(os.path.exists(
                os.path.join(out, "finding_reference_map.jsonl")))

    def test_validate_rejects_each_changed_pin(self):
        cases = [
            ({"expected_engine_version": "0.0.0"}, "engine version"),
            ({"expected_engine_sha256": "0" * 64}, "engine file sha256"),
            ({"expected_coordinates_sha256": "0" * 64},
             "canonical coordinates sha256"),
            ({"expected_research_sha256": "0" * 64}, "research artifact sha256"),
        ]
        for kwargs, message in cases:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(MAPPING.ProductionInputError) as ctx:
                    MAPPING.validate_production_inputs(
                        MAPPING.DEFAULT_RESEARCH_ARTIFACT, **kwargs)
                self.assertIn(message, str(ctx.exception))

    def test_cli_write_requires_pins_unless_explicitly_unpinned(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus = os.path.join(tmp, "combined.jsonl")
            self._write_corpus(corpus)
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(MAPPING.ProductionInputError):
                    MAPPING.main(["--write", "--out", os.path.join(tmp, "a"),
                                  "--research", corpus])
            with contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                code = MAPPING.main(["--write", "--out", os.path.join(tmp, "b"),
                                     "--research", corpus, "--unpinned-inputs"])
            self.assertEqual(code, 0)
            self.assertTrue(os.path.exists(
                os.path.join(tmp, "b", "finding_reference_map.jsonl")))

    def test_pinned_write_rejects_coordinate_table_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus = os.path.join(tmp, "combined.jsonl")
            self._write_corpus(corpus)
            out = os.path.join(tmp, "out")
            with self.assertRaises(MAPPING.ProductionInputError) as ctx:
                MAPPING.write_artifacts(corpus, out, table={"Revelation": (22,)},
                                        pinned=True)
            self.assertIn("coordinate table", str(ctx.exception))
            # refused BEFORE any output directory/file was created
            self.assertFalse(os.path.exists(out))

    def test_unpinned_write_still_honours_a_synthetic_coordinate_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus = os.path.join(tmp, "combined.jsonl")
            self._write_corpus(corpus)
            default = MAPPING.write_artifacts(
                corpus, os.path.join(tmp, "default"), pinned=False,
                generated_at="T")
            override = MAPPING.write_artifacts(
                corpus, os.path.join(tmp, "override"), pinned=False,
                generated_at="T", table={"Revelation": (2,)})
            self.assertEqual(default["counts"]["verse_evidence_rows"], 1)
            self.assertEqual(override["counts"]["verse_evidence_rows"], 0)
            self.assertTrue(override["production_pins"]["pins_enforced"] is False)

    def test_pinned_write_rejects_a_partial_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus = os.path.join(tmp, "combined.jsonl")
            self._write_corpus(corpus)
            out = os.path.join(tmp, "out")
            with self.assertRaises(MAPPING.ProductionInputError) as ctx:
                MAPPING.write_artifacts(corpus, out, limit=1, pinned=True)
            self.assertIn("limit", str(ctx.exception))
            self.assertFalse(os.path.exists(out))

    def test_unpinned_write_may_still_use_a_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus = os.path.join(tmp, "combined.jsonl")
            self._write_corpus(corpus)
            manifest = MAPPING.write_artifacts(
                corpus, os.path.join(tmp, "out"), limit=1, pinned=False,
                generated_at="T")
            self.assertEqual(manifest["counts"]["passages"], 1)

    def test_cli_write_limit_requires_explicit_unpinned_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus = os.path.join(tmp, "combined.jsonl")
            self._write_corpus(corpus)
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(MAPPING.ProductionInputError):
                    MAPPING.main(["--write", "--out", os.path.join(tmp, "a"),
                                  "--research", corpus, "--limit", "1"])
            with contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                code = MAPPING.main(["--write", "--out", os.path.join(tmp, "b"),
                                     "--research", corpus, "--limit", "1",
                                     "--unpinned-inputs"])
            self.assertEqual(code, 0)
            self.assertTrue(os.path.exists(
                os.path.join(tmp, "b", "finding_reference_map.jsonl")))

    def test_manifest_records_mapper_file_sha256(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus = os.path.join(tmp, "combined.jsonl")
            self._write_corpus(corpus)
            manifest = MAPPING.write_artifacts(
                corpus, os.path.join(tmp, "out"), pinned=False, generated_at="T")
            self.assertIn("mapper_file_sha256", manifest)
            with open(MAPPING.__file__, "rb") as handle:
                expected = hashlib.sha256(handle.read()).hexdigest()
            self.assertEqual(manifest["mapper_file_sha256"], expected)
            self.assertEqual(len(manifest["mapper_file_sha256"]), 64)


@unittest.skipUnless(
    os.environ.get("GD_RUN_FULL_CORPUS_AUDIT") == "1",
    "set GD_RUN_FULL_CORPUS_AUDIT=1 to run the full 58,498-finding audit")
class FullCorpusAuditTests(unittest.TestCase):
    """End-to-end proof over the real combined artifact (read-only)."""

    def test_full_artifact_reconstructs_58498_unique_findings(self):
        if not os.path.exists(MAPPING.DEFAULT_RESEARCH_ARTIFACT):
            self.skipTest("combined research artifact not present")
        summary = MAPPING.audit_corpus(MAPPING.DEFAULT_RESEARCH_ARTIFACT,
                                       samples=0)
        self.assertEqual(summary["passage_records"], MAPPING.EXPECTED_PASSAGES)
        self.assertEqual(summary["final_verified_findings"],
                         MAPPING.EXPECTED_FINAL_FINDINGS)
        self.assertEqual(summary["unique_finding_uids"],
                         MAPPING.EXPECTED_FINAL_FINDINGS)
        self.assertEqual(summary["finding_uid_collisions"], 0)
        self.assertEqual(summary["mixed_context_raw_refs"], 0)
        self.assertGreater(summary["unique_finding_verse_mappings"], 0)
        self.assertLessEqual(summary["unique_canonical_verses_represented"], 31102)
        self.assertTrue(summary["engine_file_sha256_matches_expected"])
        self.assertTrue(summary["coordinates_artifact_sha256_matches_expected"])
        self.assertTrue(summary["coordinates_counts_match_expected"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
