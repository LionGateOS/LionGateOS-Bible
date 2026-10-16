#!/usr/bin/env python3
"""
Track D: Explicit Authorial Corrections Discovery Audit

This script performs a READ-ONLY discovery audit to find Bible wording and
capitalization candidates that are explicitly supported by Herbert W. Armstrong
and/or Gerald Flurry using the existing archive-search/research machinery.

Authority policy: Verified direct Scripture corrections taught by Herbert W. Armstrong
or Gerald Flurry are accepted under the owner's standing editorial authority policy.

Key principles:
- Do not infer an approval merely because a phrase appears in an author's writing
- Do not silently resolve disagreements
- Do not modify the Bible
- Search for authorial correction language: "should read", "should be translated",
  "correct translation", "wrong translation", "mistranslated", "capitalization", etc.
- Count authorial support: report separate counts for Armstrong, Flurry, and total
- Do NOT describe the count as the number of times an author "approved the rule."
  It is a search-derived occurrence count.

Author: GD Bible Editorial Review Workstream
Date: 2026-10-15
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

# Paths
ARCHIVE_INDEX_DIR = Path(os.environ.get("GD_ARCHIVE_ROOT", "/home/liongateos/PCOG-Research-Archive")) / "research" / "full-archive-index-21469-v1"
REVISION_MAPPING_DIR = Path(os.environ.get("GD_ARCHIVE_ROOT", "/home/liongateos/PCOG-Research-Archive")) / "research" / "gd-bible-revision-mapping-v1"
TRANSFORMATION_MANIFEST = Path("/home/liongateos/LionGateOS-Bible/source/growdaily/docs/bible/TRANSFORMATION_MANIFEST.json")
OUTPUT_DIR = Path("/tmp/gd-bible-track-d-discovery")

# Correction language signals (Tier A)
CORRECTION_SIGNALS = {
    "correction_language",  # "should read", "should be translated", "mistranslat*", etc.
    "textual_criticism",    # Textual criticism discussions
    "wording_discussion",   # Wording discussions
}

# Speaker attribution signals (Tier D)
SPEAKER_SIGNALS = {
    "hwa_name",     # Herbert W. Armstrong name mentions
    "flurry_name",  # Gerald Flurry name mentions
}

# Capitalization signals
CAPITALIZATION_SIGNALS = {
    "capitalization",
    "mixed_capitalization",
    "divine_name_caps",
    "gospel_caps",
    "church_caps",
    "kingdom_caps",
    "word_caps",
    "bride_caps",
}


def load_top_candidates() -> dict[str, Any]:
    """Load the top candidates from the full archive index."""
    candidates_path = ARCHIVE_INDEX_DIR / "top_candidates.json"
    print(f"Loading top candidates from {candidates_path}...")
    with open(candidates_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_transformation_manifest() -> dict[str, Any]:
    """Load the transformation manifest for cross-reference."""
    print(f"Loading transformation manifest from {TRANSFORMATION_MANIFEST}...")
    with open(TRANSFORMATION_MANIFEST, "r", encoding="utf-8") as f:
        return json.load(f)


def has_signal(candidate: dict[str, Any], signal_name: str) -> bool:
    """Check if a candidate has a specific signal."""
    signals = {s["signal"] for s in candidate.get("signals", [])}
    return signal_name in signals


def has_any_signal(candidate: dict[str, Any], signal_names: set[str]) -> bool:
    """Check if a candidate has any of the specified signals."""
    signals = {s["signal"] for s in candidate.get("signals", [])}
    return bool(signals & signal_names)


def get_signal_hits(candidate: dict[str, Any], signal_name: str) -> int:
    """Get the hit count for a specific signal."""
    for sig in candidate.get("signals", []):
        if sig["signal"] == signal_name:
            return sig.get("hits", 0)
    return 0


def extract_authorial_corrections(candidates_data: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extract candidates with both correction_language AND speaker attribution.
    
    This identifies explicit authorial corrections where the author uses
    correction language (should read, mistranslated, etc.) in connection with
    their name being mentioned.
    """
    candidates = candidates_data.get("candidates", [])
    corrections = []
    
    for candidate in candidates:
        # Must have correction language AND speaker attribution
        has_correction = has_any_signal(candidate, CORRECTION_SIGNALS)
        has_speaker = has_any_signal(candidate, SPEAKER_SIGNALS)
        
        if has_correction and has_speaker:
            # Extract author attribution
            authors = []
            if has_signal(candidate, "hwa_name"):
                authors.append("armstrong")
            if has_signal(candidate, "flurry_name"):
                authors.append("flurry")
            
            # Extract correction signals present
            correction_signals = [s["signal"] for s in candidate.get("signals", [])
                                 if s["signal"] in CORRECTION_SIGNALS]
            
            # Extract capitalization signals if present
            cap_signals = [s["signal"] for s in candidate.get("signals", [])
                          if s["signal"] in CAPITALIZATION_SIGNALS]
            
            corrections.append({
                "chunk_id": candidate.get("chunk_id"),
                "path": candidate.get("path"),
                "collection": candidate.get("collection"),
                "sha256": candidate.get("sha256"),
                "score": candidate.get("score"),
                "priority": candidate.get("priority"),
                "authors": authors,
                "correction_signals": correction_signals,
                "capitalization_signals": cap_signals,
                "topics": candidate.get("topics", []),
                "tiers": candidate.get("tiers", []),
                "matches": candidate.get("matches", []),
                "armstrong_hits": get_signal_hits(candidate, "hwa_name"),
                "flurry_hits": get_signal_hits(candidate, "flurry_name"),
                "correction_language_hits": get_signal_hits(candidate, "correction_language"),
            })
    
    return corrections


def load_high_definite_findings() -> list[dict[str, Any]]:
    """Load high-definite findings from the fresh research."""
    findings_path = ARCHIVE_INDEX_DIR / "high-definite-fresh-v1.jsonl"
    print(f"Loading high-definite findings from {findings_path}...")
    findings = []
    with open(findings_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                findings.append(json.loads(line))
    return findings


def filter_authorial_corrections_from_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Filter high-definite findings for authorial corrections.
    
    This looks for findings that have:
    - correction_language or textual_criticism signals
    - hwa_name or flurry_name signals
    """
    authorial = []
    
    for finding in findings:
        signals = {m.get("signal") for m in finding.get("matches", [])}
        
        has_correction = bool(signals & CORRECTION_SIGNALS)
        has_speaker = bool(signals & SPEAKER_SIGNALS)
        
        if has_correction and has_speaker:
            authors = []
            if "hwa_name" in signals:
                authors.append("armstrong")
            if "flurry_name" in signals:
                authors.append("flurry")
            
            authorial.append({
                "chunk_id": finding.get("chunk_id"),
                "char_start": finding.get("char_start"),
                "char_end": finding.get("char_end"),
                "collection": finding.get("collection"),
                "authors": authors,
                "signals": list(signals),
                "matches": finding.get("matches", []),
            })
    
    return authorial


def load_verse_evidence_index() -> dict[str, list[dict[str, Any]]]:
    """
    Load the verse evidence index for mapping findings to verses.
    
    Returns a dict mapping verse keys to lists of findings.
    """
    index_path = REVISION_MAPPING_DIR / "verse_evidence_index.jsonl"
    print(f"Loading verse evidence index from {index_path}...")
    
    verse_index: dict[str, list[dict[str, Any]]] = {}
    
    with open(index_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                entry = json.loads(line)
                verse_key = entry.get("verse_key")
                if verse_key:
                    if verse_key not in verse_index:
                        verse_index[verse_key] = []
                    verse_index[verse_key].append(entry)
    
    return verse_index


def cross_reference_with_manifest(
    corrections: list[dict[str, Any]],
    manifest: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Cross-reference discovered corrections with existing transformations.
    
    This identifies whether discovered authorial corrections correspond to
    existing GD transformations.
    """
    # Build verse -> transformation mapping
    verse_to_transform: dict[str, dict[str, Any]] = {}
    for transform in manifest.get("transformations", []):
        verse_key = transform.get("verse_key")
        if verse_key:
            verse_to_transform[verse_key] = transform
    
    # Check each correction for verse mappings
    results = []
    for correction in corrections:
        # Extract scripture references from matches
        refs = []
        for match in correction.get("matches", []):
            snippet = match.get("snippet", "")
            matched_text = match.get("matched_text", "")
            # Look for scripture references in the snippet
            if any(ref in snippet.lower() or ref in matched_text.lower() 
                   for ref in ["corinthians", "ephesians", "hebrews", "john", "revelation",
                               "matthew", "mark", "luke", "acts", "romans", "thessalonians",
                               "timothy", "titus", "philemon", "galatians", "colossians",
                               "pete", "jude", "isai", "psalm", "genesis", "exodus",
                               "deuteronom", "leviticus", "numbers"]):
                refs.append({
                    "snippet": snippet[:200],
                    "matched_text": matched_text,
                })
        
        results.append({
            **correction,
            "potential_scripture_refs": refs,
        })
    
    return results


def generate_discovery_report(
    top_candidates_corrections: list[dict[str, Any]],
    findings_corrections: list[dict[str, Any]],
    manifest: dict[str, Any]
) -> dict[str, Any]:
    """Generate the Track D discovery audit report."""
    
    # Count authorial support
    armstrong_count = sum(1 for c in top_candidates_corrections if "armstrong" in c["authors"])
    flurry_count = sum(1 for c in top_candidates_corrections if "flurry" in c["authors"])
    
    # Count hits (occurrences, not "approvals")
    armstrong_hits = sum(c["armstrong_hits"] for c in top_candidates_corrections)
    flurry_hits = sum(c["flurry_hits"] for c in top_candidates_corrections)
    
    # Cross-reference with manifest
    cross_ref_results = cross_reference_with_manifest(top_candidates_corrections, manifest)
    
    report = {
        "title": "Track D: Explicit Authorial Corrections Discovery Audit",
        "description": "READ-ONLY discovery audit for Bible wording and capitalization candidates "
                      "explicitly supported by Herbert W. Armstrong and/or Gerald Flurry",
        "authority_policy": "Verified direct Scripture corrections taught by Herbert W. Armstrong "
                           "or Gerald Flurry are accepted under the owner's standing editorial "
                           "authority policy",
        "methodology": {
            "approach": "Search-derived occurrence count using existing archive-search machinery",
            "correction_signals": list(CORRECTION_SIGNALS),
            "speaker_signals": list(SPEAKER_SIGNALS),
            "capitalization_signals": list(CAPITALIZATION_SIGNALS),
            "note": "Do NOT describe counts as author 'approvals.' These are search-derived "
                   "occurrence counts.",
        },
        "summary": {
            "total_candidates_with_authorial_correction": len(top_candidates_corrections),
            "armstrong_occurrence_count": armstrong_count,
            "flurry_occurrence_count": flurry_count,
            "armstrong_name_hits": armstrong_hits,
            "flurry_name_hits": flurry_hits,
            "total_high_definite_authorial_findings": len(findings_corrections),
        },
        "sections": {
            "A_explicit_corrections": {
                "description": "Explicit authorial corrections with 'should read', 'mistranslated', etc.",
                "candidates": cross_ref_results[:20],  # Top 20 by score
            },
            "B_wording_explanations": {
                "description": "Author explanations of correct wording/translation",
                "candidates": [c for c in cross_ref_results 
                              if "wording_discussion" in c.get("correction_signals", [])][:10],
            },
            "C_capitalization_observations": {
                "description": "Author observations on capitalization",
                "candidates": [c for c in cross_ref_results 
                              if c.get("capitalization_signals")][:10],
            },
            "D_existing_transformations_with_support": {
                "description": "Existing GD transformations with authorial support",
                "note": "Requires verse-level mapping to TRANSFORMATION_MANIFEST.json",
                "pending": "verse_mapping_required",
            },
            "E_candidates_requiring_verification": {
                "description": "Candidates requiring external verification",
                "candidates": cross_ref_results[20:50],  # Next tier
            },
            "F_occurrence_count_methodology": {
                "description": "Methodology for counting authorial support",
                "methodology": "Search-derived occurrence count from archive documents",
                "armstrong_count": armstrong_count,
                "flurry_count": flurry_count,
                "armstrong_hits": armstrong_hits,
                "flurry_hits": flurry_hits,
                "note": "Counts represent occurrences in search results, not author approvals",
            },
        },
        "all_candidates": cross_ref_results,
    }
    
    return report


def main():
    print("=" * 70)
    print("Track D: Explicit Authorial Corrections Discovery Audit")
    print("=" * 70)
    
    # Load data
    candidates_data = load_top_candidates()
    manifest = load_transformation_manifest()
    
    # Extract authorial corrections from top candidates
    print("\nExtracting authorial corrections from top candidates...")
    top_candidates_corrections = extract_authorial_corrections(candidates_data)
    print(f"Found {len(top_candidates_corrections)} candidates with correction + speaker signals")
    
    # Load and filter high-definite findings
    print("\nLoading high-definite findings...")
    high_definite = load_high_definite_findings()
    print(f"Loaded {len(high_definite)} high-definite findings")
    
    print("\nFiltering for authorial corrections...")
    findings_corrections = filter_authorial_corrections_from_findings(high_definite)
    print(f"Found {len(findings_corrections)} high-definite authorial correction findings")
    
    # Generate report
    print("\nGenerating discovery report...")
    report = generate_discovery_report(
        top_candidates_corrections,
        findings_corrections,
        manifest
    )
    
    # Save report
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = OUTPUT_DIR / "track_d_discovery_audit.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to {report_path}")
    
    # Print summary
    print("\n" + "=" * 70)
    print("DISCOVERY SUMMARY")
    print("=" * 70)
    print(f"Total candidates with authorial correction: {report['summary']['total_candidates_with_authorial_correction']}")
    print(f"Armstrong occurrence count: {report['summary']['armstrong_occurrence_count']}")
    print(f"Flurry occurrence count: {report['summary']['flurry_occurrence_count']}")
    print(f"Armstrong name hits: {report['summary']['armstrong_name_hits']}")
    print(f"Flurry name hits: {report['summary']['flurry_name_hits']}")
    print(f"Total high-definite authorial findings: {report['summary']['total_high_definite_authorial_findings']}")
    
    # Print top 5 candidates
    print("\n" + "=" * 70)
    print("TOP 5 CANDIDATES")
    print("=" * 70)
    for i, candidate in enumerate(report["sections"]["A_explicit_corrections"]["candidates"][:5], 1):
        print(f"\n{i}. {candidate['path']}")
        print(f"   Authors: {', '.join(candidate['authors'])}")
        print(f"   Correction signals: {', '.join(candidate['correction_signals'])}")
        print(f"   Score: {candidate['score']}")
        if candidate.get("potential_scripture_refs"):
            print(f"   Potential refs: {len(candidate['potential_scripture_refs'])}")


if __name__ == "__main__":
    main()
