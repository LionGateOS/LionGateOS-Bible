#!/usr/bin/env python3
"""
Tests for Track D Discovery V2

Covers:
- Attribution uncertainty
- Duplicate documents
- Multiple corrections in one document
- Incorrect verse matches
- Incomplete provenance
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from track_d_discovery_v2 import (
    normalize_reference_to_verse_key,
    classify_finding,
    assess_attribution_confidence,
    build_verse_to_rules_mapping,
    HWA_SPEAKERS,
    GF_SPEAKERS,
    ALL_AUTHOR_SPEAKERS,
    TRACK_D_TOPICS,
)


# ============================================================================
# Test: Attribution Uncertainty
# ============================================================================

def test_attribution_confidence_hwa():
    """Test that HWA speakers get 'likely' confidence."""
    finding = {"speaker": "HWA", "quote": "test", "note": "test"}
    assert assess_attribution_confidence(finding) == "likely"


def test_attribution_confidence_gf():
    """Test that GF speakers get 'likely' confidence."""
    finding = {"speaker": "GF", "quote": "test", "note": "test"}
    assert assess_attribution_confidence(finding) == "likely"


def test_attribution_confidence_mister_armstrong():
    """Test that 'Mr. Armstrong' gets 'likely' confidence."""
    finding = {"speaker": "Mr. Armstrong", "quote": "test", "note": "test"}
    assert assess_attribution_confidence(finding) == "likely"


def test_attribution_confidence_mister_flurry():
    """Test that 'Mr. Flurry' gets 'likely' confidence."""
    finding = {"speaker": "Mr. Flurry", "quote": "test", "note": "test"}
    assert assess_attribution_confidence(finding) == "likely"


def test_attribution_confidence_unknown():
    """Test that unknown speakers get 'unknown' confidence."""
    finding = {"speaker": "unknown", "quote": "test", "note": "test"}
    assert assess_attribution_confidence(finding) == "unknown"


def test_attribution_confidence_other():
    """Test that 'other' speakers get 'unknown' confidence."""
    finding = {"speaker": "other", "quote": "test", "note": "test"}
    assert assess_attribution_confidence(finding) == "unknown"


def test_attribution_confidence_jesus():
    """Test that biblical speakers get 'unknown' confidence."""
    finding = {"speaker": "Jesus", "quote": "test", "note": "test"}
    assert assess_attribution_confidence(finding) == "unknown"


# ============================================================================
# Test: Duplicate Documents
# ============================================================================

def test_deduplicate_by_document_sha():
    """Test that documents with same SHA are grouped together."""
    from track_d_discovery_v2 import deduplicate_by_document_sha

    records = [
        {"source_document_sha256": "abc123", "quote": "test1"},
        {"source_document_sha256": "abc123", "quote": "test2"},
        {"source_document_sha256": "def456", "quote": "test3"},
    ]

    groups = deduplicate_by_document_sha(records)

    assert len(groups) == 2
    assert len(groups["abc123"]) == 2
    assert len(groups["def456"]) == 1


def test_deduplicate_empty_sha():
    """Test that records with empty SHA are excluded."""
    from track_d_discovery_v2 import deduplicate_by_document_sha

    records = [
        {"source_document_sha256": "", "quote": "test1"},
        {"source_document_sha256": "abc123", "quote": "test2"},
    ]

    groups = deduplicate_by_document_sha(records)

    assert len(groups) == 1
    assert "abc123" in groups


# ============================================================================
# Test: Multiple Corrections in One Document
# ============================================================================

def test_multiple_corrections_same_document():
    """Test that multiple corrections in same document are tracked separately."""
    from track_d_discovery_v2 import count_distinct_teaching_occasions

    records = [
        {
            "source_document_sha256": "abc123",
            "note": "First correction about verse X",
            "quote": "quote1",
        },
        {
            "source_document_sha256": "abc123",
            "note": "Second correction about verse Y",
            "quote": "quote2",
        },
        {
            "source_document_sha256": "abc123",
            "note": "First correction about verse X",  # Same note = same occasion
            "quote": "quote3",
        },
    ]

    result = count_distinct_teaching_occasions(records)

    # Should have 2 distinct occasions (note1 and note2)
    assert result["count"] == 2


# ============================================================================
# Test: Verse Reference Normalization
# ============================================================================

def test_normalize_reference_matthew():
    """Test normalization of Matthew reference."""
    result = normalize_reference_to_verse_key("Matthew 1:18")
    assert result == "b40:c1:v18"


def test_normalize_reference_romans():
    """Test normalization of Romans reference."""
    result = normalize_reference_to_verse_key("Romans 3:23")
    assert result == "b45:c3:v23"


def test_normalize_reference_1_john():
    """Test normalization of 1 John reference."""
    result = normalize_reference_to_verse_key("1 John 5:7")
    assert result == "b62:c5:v7"


def test_normalize_reference_abbrev():
    """Test normalization of abbreviated reference."""
    result = normalize_reference_to_verse_key("Matt 1:1")
    assert result == "b40:c1:v1"


def test_normalize_reference_invalid():
    """Test that invalid references return None."""
    result = normalize_reference_to_verse_key("Invalid Reference")
    assert result is None


def test_normalize_reference_range():
    """Test that verse ranges are handled (returns first verse)."""
    result = normalize_reference_to_verse_key("Matthew 1:18-21")
    # Returns first verse in range
    assert result == "b40:c1:v18"


# ============================================================================
# Test: Classification
# ============================================================================

def test_classify_explicit_correction_should_read():
    """Test classification of 'should read' pattern."""
    finding = {
        "quote": "This should read 'holy spirit'",
        "note": "",
        "topic": "translation",
    }
    assert classify_finding(finding) == "explicit_correction"


def test_classify_explicit_correction_should_be_translated():
    """Test classification of 'should be translated' pattern."""
    finding = {
        "quote": "This should be translated as 'LORD'",
        "note": "",
        "topic": "translation",
    }
    assert classify_finding(finding) == "explicit_correction"


def test_classify_explicit_correction_not_pattern():
    """Test classification of 'NOT' pattern."""
    finding = {
        "quote": "It says 'wife', NOT \"WIFE\"",
        "note": "",
        "topic": "wording",
    }
    assert classify_finding(finding) == "explicit_correction"


def test_classify_capitalization_observation():
    """Test classification of capitalization discussion."""
    finding = {
        "quote": "The term should be capitalized",
        "note": "",
        "topic": "capitalization",
    }
    assert classify_finding(finding) == "capitalization_observation"


def test_classify_wording_explanation():
    """Test classification of wording explanation."""
    finding = {
        "quote": "The wording here is important",
        "note": "",
        "topic": "wording",
    }
    assert classify_finding(finding) == "wording_explanation"


def test_classify_translation_discussion():
    """Test classification of translation discussion."""
    finding = {
        "quote": "The King James Version is accurate here",
        "note": "",
        "topic": "translation",
    }
    assert classify_finding(finding) == "translation_discussion"


def test_classify_unresolved_lead():
    """Test classification of unresolved finding."""
    finding = {
        "quote": "Some general text",
        "note": "",
        "topic": "terminology",  # Not a Track D topic
    }
    assert classify_finding(finding) == "unresolved_lead"


# ============================================================================
# Test: Incorrect Verse Matches
# ============================================================================

def test_verse_to_rules_mapping():
    """Test that verse to rules mapping works correctly."""
    manifest = {
        "rules": [
            {
                "ruleId": "R001",
                "references": ["Matthew 1:18", "Matthew 1:20"],
            },
            {
                "ruleId": "R002",
                "references": ["Romans 3:23"],
            },
        ]
    }

    mapping = build_verse_to_rules_mapping(manifest)

    assert "b40:c1:v18" in mapping
    assert "R001" in mapping["b40:c1:v18"]
    assert "b40:c1:v20" in mapping
    assert "R001" in mapping["b40:c1:v20"]
    assert "b45:c3:v23" in mapping
    assert "R002" in mapping["b45:c3:v23"]


def test_verse_to_rules_no_match():
    """Test that unmapped verses return empty list."""
    manifest = {
        "rules": [
            {
                "ruleId": "R001",
                "references": ["Matthew 1:18"],
            },
        ]
    }

    mapping = build_verse_to_rules_mapping(manifest)

    # This verse is not in the mapping
    assert "b45:c3:v23" not in mapping


# ============================================================================
# Test: Incomplete Provenance
# ============================================================================

def test_findings_with_provenance():
    """Test that findings with various provenance values are handled."""
    from track_d_discovery_v2 import extract_authorial_findings

    findings = [
        {
            "finding_uid": "uid1",
            "finding": {
                "speaker": "HWA",
                "topic": "translation",
                "quote": "test",
                "note": "test",
                "provenance": "in_chunk_exact",
                "confidence": "high",
            },
            "identity": {
                "source_document": "doc1",
                "source_document_sha256": "sha1",
                "chunk_id": "c001",
            },
            "mapped_verse_keys": ["b40:c1:v18"],
        },
        {
            "finding_uid": "uid2",
            "finding": {
                "speaker": "HWA",
                "topic": "translation",
                "quote": "test",
                "note": "test",
                "provenance": "document_only",  # Less reliable
                "confidence": "medium",
            },
            "identity": {
                "source_document": "doc2",
                "source_document_sha256": "sha2",
                "chunk_id": "c002",
            },
            "mapped_verse_keys": [],
        },
    ]

    verse_index = {}
    verse_to_rules = {}

    records = extract_authorial_findings(findings, verse_index, verse_to_rules)

    assert len(records) == 2
    assert records[0]["provenance"] == "in_chunk_exact"
    assert records[1]["provenance"] == "document_only"


def test_findings_missing_provenance():
    """Test that findings without provenance get 'unknown'."""
    from track_d_discovery_v2 import extract_authorial_findings

    findings = [
        {
            "finding_uid": "uid1",
            "finding": {
                "speaker": "HWA",
                "topic": "translation",
                "quote": "test",
                "note": "test",
                # No provenance field
                "confidence": "high",
            },
            "identity": {
                "source_document": "doc1",
                "source_document_sha256": "sha1",
                "chunk_id": "c001",
            },
            "mapped_verse_keys": [],
        },
    ]

    verse_index = {}
    verse_to_rules = {}

    records = extract_authorial_findings(findings, verse_index, verse_to_rules)

    assert len(records) == 1
    assert records[0]["provenance"] == "unknown"


# ============================================================================
# Test: Speaker/Topic Filtering
# ============================================================================

def test_filter_hwa_speakers():
    """Test that all HWA speaker variants are recognized."""
    for speaker in HWA_SPEAKERS:
        finding = {"speaker": speaker, "quote": "test", "note": "test"}
        assert assess_attribution_confidence(finding) == "likely"


def test_filter_gf_speakers():
    """Test that all GF speaker variants are recognized."""
    for speaker in GF_SPEAKERS:
        finding = {"speaker": speaker, "quote": "test", "note": "test"}
        assert assess_attribution_confidence(finding) == "likely"


def test_filter_track_d_topics():
    """Test that Track D topics are correctly defined."""
    assert "translation" in TRACK_D_TOPICS
    assert "wording" in TRACK_D_TOPICS
    assert "capitalization" in TRACK_D_TOPICS
    assert "terminology" not in TRACK_D_TOPICS
    assert "scripture" not in TRACK_D_TOPICS


# ============================================================================
# Run Tests
# ============================================================================

def run_tests():
    """Run all tests and report results."""
    test_functions = [
        # Attribution uncertainty
        test_attribution_confidence_hwa,
        test_attribution_confidence_gf,
        test_attribution_confidence_mister_armstrong,
        test_attribution_confidence_mister_flurry,
        test_attribution_confidence_unknown,
        test_attribution_confidence_other,
        test_attribution_confidence_jesus,
        # Duplicate documents
        test_deduplicate_by_document_sha,
        test_deduplicate_empty_sha,
        # Multiple corrections in one document
        test_multiple_corrections_same_document,
        # Verse reference normalization
        test_normalize_reference_matthew,
        test_normalize_reference_romans,
        test_normalize_reference_1_john,
        test_normalize_reference_abbrev,
        test_normalize_reference_invalid,
        test_normalize_reference_range,
        # Classification
        test_classify_explicit_correction_should_read,
        test_classify_explicit_correction_should_be_translated,
        test_classify_explicit_correction_not_pattern,
        test_classify_capitalization_observation,
        test_classify_wording_explanation,
        test_classify_translation_discussion,
        test_classify_unresolved_lead,
        # Incorrect verse matches
        test_verse_to_rules_mapping,
        test_verse_to_rules_no_match,
        # Incomplete provenance
        test_findings_with_provenance,
        test_findings_missing_provenance,
        # Speaker/topic filtering
        test_filter_hwa_speakers,
        test_filter_gf_speakers,
        test_filter_track_d_topics,
    ]

    passed = 0
    failed = 0

    for test_func in test_functions:
        try:
            test_func()
            passed += 1
            print(f"  PASS: {test_func.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL: {test_func.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"  ERROR: {test_func.__name__}: {e}")

    print(f"\n{passed}/{passed + failed} tests passed")
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
