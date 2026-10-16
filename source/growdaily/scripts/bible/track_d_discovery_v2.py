#!/usr/bin/env python3
"""
Track D: Explicit Authorial Corrections Discovery V2

This script performs a READ-ONLY discovery audit using existing research data
to find Bible wording and capitalization candidates explicitly supported by
Herbert W. Armstrong and/or Gerald Flurry.

Authority policy: Verified direct Scripture corrections taught by Herbert W. Armstrong
or Gerald Flurry are accepted under the owner's standing editorial authority policy.

Key principles:
- Do not infer an approval merely because a phrase appears in an author's writing
- Do not silently resolve disagreements
- Do not modify the Bible
- Do not automatically accept the research speaker field as verified authorship
- Deduplicate exact document copies by SHA-256
- Distinguish: matching findings, distinct passages, distinct documents, teaching occasions

Author: GD Bible Editorial Review Workstream
Date: 2026-10-16
"""

import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

# ============================================================================
# Configuration
# ============================================================================

ARCHIVE_RESEARCH_DIR = Path(os.environ.get("GD_ARCHIVE_ROOT", "/home/liongateos/PCOG-Research-Archive")) / "research"
FINDING_REFERENCE_MAP = ARCHIVE_RESEARCH_DIR / "gd-bible-revision-mapping-v1" / "finding_reference_map.jsonl"
VERSE_EVIDENCE_INDEX = ARCHIVE_RESEARCH_DIR / "gd-bible-revision-mapping-v1" / "verse_evidence_index.jsonl"
TRANSFORMATION_MANIFEST = Path("/home/liongateos/LionGateOS-Bible/source/growdaily/docs/bible/TRANSFORMATION_MANIFEST.json")
OUTPUT_DIR = Path("/tmp/gd-bible-track-d-v2")

# Speaker values that indicate HWA or GF attribution (from confirmed data)
HWA_SPEAKERS = {"HWA", "Mr. Armstrong", "Armstrong", "Herbert W. Armstrong"}
GF_SPEAKERS = {"GF", "Mr. Flurry", "Flurry", "Gerald Flurry"}
ALL_AUTHOR_SPEAKERS = HWA_SPEAKERS | GF_SPEAKERS

# Topics relevant to Track D (corrections, wording, capitalization)
TRACK_D_TOPICS = {"translation", "wording", "capitalization"}

# Correction language patterns for classification
CORRECTION_PATTERNS = [
    r"should read",
    r"should be translated",
    r"ought to be translated",
    r"mistranslat\w*",
    r"mis-translat\w*",
    r"wrongly translated",
    r"incorrectly translated",
    r"erroneous translation",
    r"correct translation",
    r"wrong translation",
    r"NOT\s+[\"']",  # "NOT "X"" or "NOT 'X'" pattern indicating correction
    r"is not\s+[\"']",  # "is not "X"" pattern
    r"does not say",
    r"never says",
    r"inaccurate",
    r"not very clear",
]

CAPITALIZATION_PATTERNS = [
    r"capitali[sz](?:e|es|ed|ing|ation|ations)",
    r"upper[-\s]?case",
    r"lower[-\s]?case",
    r"capital letter",
    r"capitalized",
    r"capitalised",
]

WORDING_PATTERNS = [
    r"wording",
    r"phrase",
    r"phrasing",
    r"reads",
    r"expressed",
    r"rendered",
]

TRANSLATION_PATTERNS = [
    r"translat(?:e|es|ed|ing|ion|ions|or|ors)",
    r"King James",
    r"KJV",
    r"Revised Standard",
    r"RSV",
    r"New International",
    r"NIV",
    r"translation",
]


# ============================================================================
# Data Loading Functions
# ============================================================================

def load_finding_reference_map() -> list[dict[str, Any]]:
    """Load finding_reference_map.jsonl."""
    findings = []
    with open(FINDING_REFERENCE_MAP, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                findings.append(json.loads(line))
    return findings


def load_verse_evidence_index() -> dict[str, list[dict[str, Any]]]:
    """Load verse_evidence_index.jsonl indexed by finding_uid."""
    index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with open(VERSE_EVIDENCE_INDEX, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                entry = json.loads(line)
                finding_uid = entry.get("finding_uid")
                if finding_uid:
                    index[finding_uid].append(entry)
    return dict(index)


def load_transformation_manifest() -> dict[str, Any]:
    """Load TRANSFORMATION_MANIFEST.json."""
    with open(TRANSFORMATION_MANIFEST, "r", encoding="utf-8") as f:
        return json.load(f)


def build_verse_to_rules_mapping(manifest: dict[str, Any]) -> dict[str, list[str]]:
    """Build mapping from canonical verse keys to transformation rule IDs."""
    verse_to_rules: dict[str, list[str]] = defaultdict(list)

    for rule in manifest.get("rules", []):
        rule_id = rule.get("ruleId", "")
        for ref in rule.get("references", []):
            # Normalize reference to canonical verse key format
            verse_key = normalize_reference_to_verse_key(ref)
            if verse_key:
                verse_to_rules[verse_key].append(rule_id)

    return dict(verse_to_rules)


def normalize_reference_to_verse_key(ref: str) -> Optional[str]:
    """
    Normalize a Bible reference string to canonical verse key format.

    Examples:
        "Matthew 1:18" -> "b40:c1:v18"
        "Rom 3:23" -> "b45:c3:v23"
        "1 John 5:7" -> "b60:c5:v7"
    """
    # Book name to ID mapping (partial - covers common books)
    book_names = {
        "Genesis": 1, "Exodus": 2, "Leviticus": 3, "Numbers": 4, "Deuteronomy": 5,
        "Joshua": 6, "Judges": 7, "Ruth": 8, "1 Samuel": 9, "2 Samuel": 10,
        "1 Kings": 11, "2 Kings": 12, "1 Chronicles": 13, "2 Chronicles": 14,
        "Ezra": 15, "Nehemiah": 16, "Esther": 17, "Job": 18, "Psalms": 19, "Psalm": 19,
        "Proverbs": 20, "Ecclesiastes": 21, "Song of Solomon": 22, "Isaiah": 23,
        "Jeremiah": 24, "Lamentations": 25, "Ezekiel": 26, "Daniel": 27, "Hosea": 28,
        "Joel": 29, "Amos": 30, "Obadiah": 31, "Jonah": 32, "Micah": 33, "Nahum": 34,
        "Habakkuk": 35, "Zephaniah": 36, "Haggai": 37, "Zechariah": 38, "Malachi": 39,
        "Matthew": 40, "Mark": 41, "Luke": 42, "John": 43, "Acts": 44, "Romans": 45,
        "1 Corinthians": 46, "2 Corinthians": 47, "Galatians": 48, "Ephesians": 49,
        "Philippians": 50, "Colossians": 51, "1 Thessalonians": 52, "2 Thessalonians": 53,
        "1 Timothy": 54, "2 Timothy": 55, "Titus": 56, "Philemon": 57, "Hebrews": 58,
        "James": 59, "1 Peter": 60, "2 Peter": 61, "1 John": 62, "2 John": 63,
        "3 John": 64, "Jude": 65, "Revelation": 66,
        # Abbreviations
        "Gen": 1, "Ex": 2, "Lev": 3, "Num": 4, "Deut": 5, "Josh": 6, "Judg": 7,
        "Ruth": 8, "1 Sam": 9, "2 Sam": 10, "1 Kgs": 11, "2 Kgs": 12,
        "1 Chr": 13, "2 Chr": 14, "Ezra": 15, "Neh": 16, "Esth": 17, "Job": 18,
        "Ps": 19, "Prov": 20, "Eccl": 21, "Isa": 23, "Jer": 24, "Lam": 25,
        "Ezek": 26, "Dan": 27, "Hos": 28, "Joel": 29, "Amos": 30, "Obad": 31,
        "Jonah": 32, "Mic": 33, "Nah": 34, "Hab": 35, "Zeph": 36, "Hag": 37,
        "Zech": 38, "Mal": 39, "Matt": 40, "Mk": 41, "Lk": 42, "Jn": 43,
        "Acts": 44, "Rom": 45, "1 Cor": 46, "2 Cor": 47, "Gal": 48, "Eph": 49,
        "Phil": 50, "Col": 51, "1 Thess": 52, "2 Thess": 53, "1 Tim": 54,
        "2 Tim": 55, "Titus": 56, "Philem": 57, "Heb": 58, "Jas": 59,
        "1 Pet": 60, "2 Pet": 61, "1 John": 62, "2 John": 63, "3 John": 64,
        "Jude": 65, "Rev": 66,
    }

    # Parse reference
    ref = ref.strip()

    # Try to match book:chapter:verse or Book Chapter:Verse
    match = re.match(r"^(.+?)\s*(\d+):(\d+)(?:-(\d+))?$", ref)
    if match:
        book_name = match.group(1).strip()
        chapter = int(match.group(2))
        verse = int(match.group(3))

        book_id = book_names.get(book_name)
        if book_id is not None:
            return f"b{book_id}:c{chapter}:v{verse}"

    # Try abbreviated forms
    match = re.match(r"^(1?|2|3)?\s*(\w+)\s+(\d+):(\d+)", ref)
    if match:
        ordinal = match.group(1) or ""
        book_abbrev = match.group(2)
        chapter = int(match.group(3))
        verse = int(match.group(4))

        # Handle numbered books
        book_key = f"{ordinal} {book_abbrev}".strip() if ordinal else book_abbrev
        book_id = book_names.get(book_key) or book_names.get(book_abbrev)
        if book_id is not None:
            return f"b{book_id}:c{chapter}:v{verse}"

    return None


# ============================================================================
# Classification Functions
# ============================================================================

def classify_finding(finding: dict[str, Any]) -> str:
    """
    Classify a finding into one of:
    - explicit_correction: Contains explicit correction language
    - wording_explanation: Explains preferred wording
    - capitalization_observation: Discusses capitalization
    - translation_discussion: General translation discussion
    - unresolved_lead: Cannot be classified
    """
    quote = finding.get("quote", "")
    note = finding.get("note", "")
    topic = finding.get("topic", "")

    text = f"{quote} {note}"

    # Check for explicit correction patterns
    for pattern in CORRECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return "explicit_correction"

    # Check for capitalization patterns
    for pattern in CAPITALIZATION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return "capitalization_observation"

    # Check for wording patterns
    for pattern in WORDING_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return "wording_explanation"

    # Check for translation patterns
    for pattern in TRANSLATION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return "translation_discussion"

    # Default based on topic
    if topic == "capitalization":
        return "capitalization_observation"
    if topic == "wording":
        return "wording_explanation"
    if topic == "translation":
        return "translation_discussion"

    return "unresolved_lead"


def assess_attribution_confidence(finding: dict[str, Any], source_text: Optional[str] = None) -> str:
    """
    Assess confidence in speaker attribution.

    Returns:
    - "verified": Speaker field is HWA/GF and context supports it
    - "likely": Speaker field is HWA/GF but context is unclear
    - "uncertain": Speaker field may be inaccurate
    - "unknown": Cannot determine
    """
    speaker = finding.get("speaker", "")

    if speaker not in ALL_AUTHOR_SPEAKERS:
        return "unknown"

    # If speaker is HWA or GF, we have some confidence
    # But we should note that this is based on the research pipeline's attribution
    # which may not always be accurate

    return "likely"


# ============================================================================
# Discovery Functions
# ============================================================================

def extract_authorial_findings(
    findings: list[dict[str, Any]],
    verse_index: dict[str, list[dict[str, Any]]],
    verse_to_rules: dict[str, list[str]]
) -> list[dict[str, Any]]:
    """
    Extract findings with HWA/GF speaker attribution and Track D topics.

    Returns a list of evidence records with:
    - finding_uid
    - author (HWA or GF)
    - topic
    - quote
    - note
    - classification
    - attribution_confidence
    - provenance
    - source_document
    - source_document_sha256
    - mapped_verse_keys
    - related_transformation_rules
    """
    evidence_records = []

    for entry in findings:
        finding = entry.get("finding", {})
        speaker = finding.get("speaker", "")
        topic = finding.get("topic", "")

        # Filter by speaker and topic
        if speaker not in ALL_AUTHOR_SPEAKERS:
            continue
        if topic not in TRACK_D_TOPICS:
            continue

        # Determine author
        author = "HWA" if speaker in HWA_SPEAKERS else "GF"

        # Get finding UID
        finding_uid = entry.get("finding_uid", "")

        # Get verse mappings
        mapped_verse_keys = entry.get("mapped_verse_keys", [])

        # Find related transformation rules
        related_rules = []
        for verse_key in mapped_verse_keys:
            rules = verse_to_rules.get(verse_key, [])
            related_rules.extend(rules)
        related_rules = list(set(related_rules))  # Deduplicate

        # Classify the finding
        classification = classify_finding(finding)

        # Assess attribution confidence
        attribution_confidence = assess_attribution_confidence(finding)

        # Get provenance
        provenance = finding.get("provenance", "unknown")

        # Get source document info
        identity = entry.get("identity", {})
        source_document = identity.get("source_document", "")
        source_document_sha256 = identity.get("source_document_sha256", "")

        evidence_records.append({
            "finding_uid": finding_uid,
            "author": author,
            "speaker_raw": speaker,
            "topic": topic,
            "quote": finding.get("quote", ""),
            "note": finding.get("note", ""),
            "classification": classification,
            "attribution_confidence": attribution_confidence,
            "provenance": provenance,
            "confidence": finding.get("confidence", "unknown"),
            "source_document": source_document,
            "source_document_sha256": source_document_sha256,
            "chunk_id": identity.get("chunk_id", ""),
            "mapped_verse_keys": mapped_verse_keys,
            "related_transformation_rules": related_rules,
        })

    return evidence_records


def deduplicate_by_document_sha(
    records: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    """
    Group records by source_document_sha256 to identify exact duplicates.

    Returns a dict mapping SHA-256 to list of records.
    """
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        sha = record.get("source_document_sha256", "")
        if sha:
            groups[sha].append(record)
    return dict(groups)


def count_distinct_teaching_occasions(
    records: list[dict[str, Any]]
) -> dict[str, int]:
    """
    Count distinct teaching occasions by (source_document_sha256, note) pairs.

    This assumes that the same note in the same document represents the same
    teaching occasion, even if it appears multiple times.
    """
    occasions: set[tuple[str, str]] = set()
    for record in records:
        sha = record.get("source_document_sha256", "")
        note = record.get("note", "")
        if sha and note:
            occasions.add((sha, note))
    return {"count": len(occasions), "occasions": list(occasions)}


# ============================================================================
# Report Generation
# ============================================================================

def generate_summary(
    evidence_records: list[dict[str, Any]],
    document_groups: dict[str, list[dict[str, Any]]]
) -> dict[str, Any]:
    """Generate summary statistics."""

    # Count by author
    hwa_count = sum(1 for r in evidence_records if r["author"] == "HWA")
    gf_count = sum(1 for r in evidence_records if r["author"] == "GF")

    # Count by topic
    topic_counts = defaultdict(int)
    for r in evidence_records:
        topic_counts[r["topic"]] += 1

    # Count by classification
    classification_counts = defaultdict(int)
    for r in evidence_records:
        classification_counts[r["classification"]] += 1

    # Count by attribution confidence
    confidence_counts = defaultdict(int)
    for r in evidence_records:
        confidence_counts[r["attribution_confidence"]] += 1

    # Count by provenance
    provenance_counts = defaultdict(int)
    for r in evidence_records:
        provenance_counts[r["provenance"]] += 1

    # Distinct documents
    distinct_documents = len(document_groups)

    # Documents with multiple paths (duplicates)
    duplicate_documents = sum(1 for sha, recs in document_groups.items()
                             if len(recs) > 1)

    # Distinct teaching occasions
    occasions = count_distinct_teaching_occasions(evidence_records)

    # Findings with verse mappings
    with_verse_mappings = sum(1 for r in evidence_records if r["mapped_verse_keys"])

    # Findings with related transformation rules
    with_related_rules = sum(1 for r in evidence_records if r["related_transformation_rules"])

    return {
        "total_findings": len(evidence_records),
        "by_author": {"HWA": hwa_count, "GF": gf_count},
        "by_topic": dict(topic_counts),
        "by_classification": dict(classification_counts),
        "by_attribution_confidence": dict(confidence_counts),
        "by_provenance": dict(provenance_counts),
        "distinct_documents": distinct_documents,
        "duplicate_documents": duplicate_documents,
        "distinct_teaching_occasions": occasions["count"],
        "findings_with_verse_mappings": with_verse_mappings,
        "findings_with_related_rules": with_related_rules,
    }


def generate_report(summary: dict[str, Any], evidence_records: list[dict[str, Any]]) -> str:
    """Generate a human-readable report."""

    lines = [
        "# Track D Discovery V2 Report",
        "",
        "## Summary",
        "",
        f"- **Total findings**: {summary['total_findings']}",
        f"- **HWA findings**: {summary['by_author']['HWA']}",
        f"- **GF findings**: {summary['by_author']['GF']}",
        f"- **Distinct documents**: {summary['distinct_documents']}",
        f"- **Distinct teaching occasions**: {summary['distinct_teaching_occasions']}",
        "",
        "## By Topic",
        "",
    ]

    for topic, count in summary["by_topic"].items():
        lines.append(f"- **{topic}**: {count}")

    lines.extend([
        "",
        "## By Classification",
        "",
    ])

    for classification, count in summary["by_classification"].items():
        lines.append(f"- **{classification}**: {count}")

    lines.extend([
        "",
        "## By Attribution Confidence",
        "",
    ])

    for confidence, count in summary["by_attribution_confidence"].items():
        lines.append(f"- **{confidence}**: {count}")

    lines.extend([
        "",
        "## By Provenance",
        "",
    ])

    for provenance, count in summary["by_provenance"].items():
        lines.append(f"- **{provenance}**: {count}")

    lines.extend([
        "",
        "## Key Metrics",
        "",
        f"- **Findings with verse mappings**: {summary['findings_with_verse_mappings']}",
        f"- **Findings with related transformation rules**: {summary['findings_with_related_rules']}",
        f"- **Documents with duplicate paths**: {summary['duplicate_documents']}",
        "",
        "## Highest Priority Candidates for Manual Verification",
        "",
        "The following findings are classified as explicit corrections and should be",
        "prioritized for manual verification:",
        "",
    ])

    # Get explicit corrections
    explicit_corrections = [r for r in evidence_records
                           if r["classification"] == "explicit_correction"]

    for i, record in enumerate(explicit_corrections[:10], 1):
        lines.extend([
            f"{i}. **{record['author']}** - {record['topic']}",
            f"   - Quote: {record['quote'][:100]}...",
            f"   - Note: {record['note'][:100] if record['note'] else 'N/A'}",
            f"   - Verses: {record['mapped_verse_keys'][:3] if record['mapped_verse_keys'] else 'None'}",
            f"   - Attribution confidence: {record['attribution_confidence']}",
            "",
        ])

    lines.extend([
        "## Limitations",
        "",
        "1. Speaker attribution is based on the research pipeline's classification, which",
        "   may not always be accurate. Manual verification is recommended.",
        "",
        "2. The 'teaching occasion' count is an estimate based on (document SHA, note) pairs.",
        "   Same teachings across different documents are counted separately.",
        "",
        "3. Findings without verse mappings require manual review for verse identification.",
        "",
        "4. This report does not claim editorial verification or canonical approval.",
        "   All findings require manual review before any editorial action.",
        "",
    ])

    return "\n".join(lines)


# ============================================================================
# Main
# ============================================================================

def main():
    """Main entry point."""

    print("Loading finding_reference_map.jsonl...")
    findings = load_finding_reference_map()
    print(f"  Loaded {len(findings)} findings")

    print("Loading verse_evidence_index.jsonl...")
    verse_index = load_verse_evidence_index()
    print(f"  Loaded {len(verse_index)} finding UIDs")

    print("Loading TRANSFORMATION_MANIFEST.json...")
    manifest = load_transformation_manifest()
    print(f"  Loaded {len(manifest.get('rules', []))} transformation rules")

    print("Building verse to rules mapping...")
    verse_to_rules = build_verse_to_rules_mapping(manifest)
    print(f"  Mapped {len(verse_to_rules)} verse keys to rules")

    print("Extracting authorial findings...")
    evidence_records = extract_authorial_findings(findings, verse_index, verse_to_rules)
    print(f"  Extracted {len(evidence_records)} HWA/GF findings with Track D topics")

    print("Deduplicating by document SHA...")
    document_groups = deduplicate_by_document_sha(evidence_records)
    print(f"  Found {len(document_groups)} distinct documents")

    print("Generating summary...")
    summary = generate_summary(evidence_records, document_groups)

    # Write evidence records
    output_path = OUTPUT_DIR / "track-d-discovery-v2.jsonl"
    print(f"Writing evidence records to {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        for record in evidence_records:
            f.write(json.dumps(record) + "\n")

    # Write summary
    summary_path = OUTPUT_DIR / "track-d-discovery-summary.json"
    print(f"Writing summary to {summary_path}...")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Write report
    report_path = OUTPUT_DIR / "track-d-discovery-report.md"
    print(f"Writing report to {report_path}...")
    report = generate_report(summary, evidence_records)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    # Print summary
    print("\n=== Summary ===")
    print(f"Total findings: {summary['total_findings']}")
    print(f"  HWA: {summary['by_author']['HWA']}")
    print(f"  GF: {summary['by_author']['GF']}")
    print(f"\nBy topic:")
    for topic, count in summary["by_topic"].items():
        print(f"  {topic}: {count}")
    print(f"\nBy classification:")
    for classification, count in summary["by_classification"].items():
        print(f"  {classification}: {count}")
    print(f"\nDistinct documents: {summary['distinct_documents']}")
    print(f"Distinct teaching occasions: {summary['distinct_teaching_occasions']}")
    print(f"\nOutput files:")
    print(f"  {output_path}")
    print(f"  {summary_path}")
    print(f"  {report_path}")


if __name__ == "__main__":
    main()
