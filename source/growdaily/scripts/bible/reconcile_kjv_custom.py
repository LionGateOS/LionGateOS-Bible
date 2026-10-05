#!/usr/bin/env python3
"""
Full-Bible reconciliation between Standard KJV and Custom KJV.

Compares all 31,102 verses token-by-token using a deterministic canonical
tokenizer. Classifies every difference as:
  - approved_substitution: same token count, different tokens at known positions
  - missing_token: custom has fewer tokens than standard
  - added_token: custom has more tokens than standard
  - reordered_token: same tokens but in different order
  - unapproved_replacement: different text at a position not in the approved list
  - reference_mismatch: book/chapter/verse structure differs

The audit FAILS on every category except approved_substitution.

Usage:
    python3 scripts/bible/reconcile_kjv_custom.py
    python3 scripts/bible/reconcile_kjv_custom.py --report /tmp/reconciliation.json
"""
import json
import hashlib
import re
import sys
import unicodedata
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
STANDARD = ROOT / "assets/bible/en_kjv.json"
CUSTOM = ROOT / "assets/bible/kjv_modified.json"
RUNTIME_MANIFEST = ROOT / "assets/bible/kjv_custom_runtime_manifest.json"
DEFAULT_REPORT = ROOT / "__tests__/__fixtures__/kjv_custom_reconciliation.json"

BOOK_NAMES = [
    "Genesis","Exodus","Leviticus","Numbers","Deuteronomy","Joshua","Judges","Ruth","1 Samuel","2 Samuel",
    "1 Kings","2 Kings","1 Chronicles","2 Chronicles","Ezra","Nehemiah","Esther","Job","Psalms","Proverbs",
    "Ecclesiastes","Song of Solomon","Isaiah","Jeremiah","Lamentations","Ezekiel","Daniel","Hosea","Joel","Amos",
    "Obadiah","Jonah","Micah","Nahum","Habakkuk","Zephaniah","Haggai","Zechariah","Malachi","Matthew",
    "Mark","Luke","John","Acts","Romans","1 Corinthians","2 Corinthians","Galatians","Ephesians","Philippians",
    "Colossians","1 Thessalonians","2 Thessalonians","1 Timothy","2 Timothy","Titus","Philemon","Hebrews","James",
    "1 Peter","2 Peter","1 John","2 John","3 John","Jude","Revelation"
]

# ── Approved substitution contract ──────────────────────────────────────────
# Each entry: (standard_token_lower, custom_token_lower)
# These are 1:1 token replacements that preserve token count and position.
# Multi-word phrases like "Holy Ghost" → "Holy Spirit" are token-preserving
# (2 tokens → 2 tokens, same positions).
APPROVED_SUBSTITUTIONS = {
    # Ghost → Spirit (Holy Ghost → Holy Spirit, and standalone Ghost → Spirit)
    ("ghost", "spirit"),
    # Adoption → Sonship
    ("adoption", "sonship"),
    # Scapegoat → Azazel
    ("scapegoat", "azazel"),
    # Easter → Passover
    ("easter", "passover"),
    # Conversation → Conduct
    ("conversation", "conduct"),
    # "gave up the ghost" → "gave up his/her/my/His/their spirit"
    # These replace the article "the" with a possessive pronoun (1:1 token swap).
    # Capitalization variants (His, He) are included as lowercase.
    ("the", "his"),
    ("the", "her"),
    ("the", "my"),
    ("the", "their"),
    # R014: "a" → "an" before vowel-initial "Azazel" in Leviticus 16:10 only
    ("a", "an"),
    # Capitalization-only change (he → He in Luke 23:46)
    ("he", "he"),
}

# Verses where the standard asset contains editorial apparatus (guillemet
# blocks «...» and stray braces) that the generator correctly strips.
# These are NOT canonical KJV text — they are publisher notes about epistle
# authorship, delivery, and city of origin. The generator's
# strip_inline_brace_blocks() correctly removes them.
# For reconciliation purposes, these verses must be compared after stripping
# the editorial content from the standard text.

EDITORIAL_GUILLEMET_RE = re.compile(r"\s*«[^»]*»")
EDITORIAL_BRACE_RE = re.compile(r"\{[^}]*\}")
STRAY_BRACE_RE = re.compile(r"[\{\}]")

def strip_editorial(text):
    """Remove editorial apparatus (guillemet blocks, brace blocks, stray braces)
    from standard KJV text before comparison. This matches the generator's
    strip_inline_brace_blocks() behavior."""
    cleaned = text
    # Remove guillemet blocks
    cleaned = EDITORIAL_GUILLEMET_RE.sub("", cleaned)
    # Remove brace blocks (editorial markers)
    cleaned = EDITORIAL_BRACE_RE.sub("", cleaned)
    # Remove stray braces
    cleaned = STRAY_BRACE_RE.sub("", cleaned)
    # Collapse multiple spaces
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    # Fix space before punctuation
    cleaned = re.sub(r"\s+([,.;:?!])", r"\1", cleaned)
    return cleaned.strip()

def tokenize(text):
    """
    Deterministic canonical tokenizer.

    Splits on whitespace, strips leading/trailing punctuation, preserves
    internal apostrophes and hyphens. Normalizes to NFC for consistent
    Unicode comparison.
    """
    tokens = []
    for t in text.split():
        t = t.strip(".,;:!?()[]{}\"'""''«»—–-")
        if t:
            t = unicodedata.normalize("NFC", t)
            tokens.append(t)
    return tokens

def is_approved_substitution(std_token, cus_token):
    """Check if a token difference is an approved 1:1 substitution."""
    if std_token == cus_token:
        return True
    return (std_token.lower(), cus_token.lower()) in APPROVED_SUBSTITUTIONS

def reconcile_verse(std_text, cus_text, strip_editorial_from_std=True):
    """
    Reconcile a single verse. Returns classification dict.
    """
    # Strip editorial from standard if requested
    comparison_std = strip_editorial(std_text) if strip_editorial_from_std else std_text

    std_tokens = tokenize(comparison_std)
    cus_tokens = tokenize(cus_text)

    result = {
        "std_token_count": len(std_tokens),
        "cus_token_count": len(cus_tokens),
        "token_count_match": len(std_tokens) == len(cus_tokens),
        "missing_tokens": [],
        "added_tokens": [],
        "unapproved_replacements": [],
        "approved_substitutions": [],
        "reordered_tokens": [],
    }

    if len(std_tokens) != len(cus_tokens):
        # Token count mismatch — identify missing or added tokens
        if len(cus_tokens) < len(std_tokens):
            # Find which positions are missing
            # Try alignment: for each std position, check if cus matches
            # Simple approach: find the longest common subsequence
            result["missing_tokens"] = find_missing(std_tokens, cus_tokens)
        else:
            result["added_tokens"] = find_added(std_tokens, cus_tokens)
        return result

    # Same token count — check for substitutions and reordering
    std_lower = [t.lower() for t in std_tokens]
    cus_lower = [t.lower() for t in cus_tokens]

    # Check for reordering (same multiset but different order)
    if sorted(std_lower) != sorted(cus_lower):
        # Different token sets — must be substitutions
        for i, (s, c) in enumerate(zip(std_tokens, cus_tokens)):
            if s != c:
                if is_approved_substitution(s, c):
                    result["approved_substitutions"].append({
                        "position": i,
                        "std_token": s,
                        "cus_token": c,
                    })
                else:
                    result["unapproved_replacements"].append({
                        "position": i,
                        "std_token": s,
                        "cus_token": c,
                    })
    else:
        # Same multiset — check for reordering
        if std_lower != cus_lower:
            # Find reordered positions
            for i, (s, c) in enumerate(zip(std_tokens, cus_tokens)):
                if s != c:
                    result["reordered_tokens"].append({
                        "position": i,
                        "std_token": s,
                        "cus_token": c,
                    })

    return result

def find_missing(std_tokens, cus_tokens):
    """Find positions where standard tokens are missing from custom."""
    missing = []
    # Use a simple alignment: walk both token lists, finding where cus skips
    j = 0
    for i, s in enumerate(std_tokens):
        if j < len(cus_tokens) and s.lower() == cus_tokens[j].lower():
            j += 1
        elif j < len(cus_tokens) and is_approved_substitution(s, cus_tokens[j]):
            j += 1
        else:
            # Check if this token appears later in cus (shifted)
            found = False
            for k in range(j, min(j + 3, len(cus_tokens))):
                if s.lower() == cus_tokens[k].lower() or is_approved_substitution(s, cus_tokens[k]):
                    found = True
                    break
            if not found:
                missing.append({
                    "position": i,
                    "std_token": s,
                })
    return missing

def find_added(std_tokens, cus_tokens):
    """Find positions where custom has extra tokens not in standard."""
    added = []
    j = 0
    for i, c in enumerate(cus_tokens):
        if j < len(std_tokens) and c.lower() == std_tokens[j].lower():
            j += 1
        elif j < len(std_tokens) and is_approved_substitution(std_tokens[j], c):
            j += 1
        else:
            found = False
            for k in range(j, min(j + 3, len(std_tokens))):
                if c.lower() == std_tokens[k].lower() or is_approved_substitution(std_tokens[k], c):
                    found = True
                    break
            if not found:
                added.append({
                    "position": i,
                    "cus_token": c,
                })
    return added

def main():
    report_path = Path(sys.argv[sys.argv.index("--report") + 1]) if "--report" in sys.argv else DEFAULT_REPORT

    standard = json.loads(STANDARD.read_text("utf-8"))
    custom = json.loads(CUSTOM.read_text("utf-8"))
    manifest = json.loads(RUNTIME_MANIFEST.read_text("utf-8"))

    manifest_entries = manifest.get("changedVerses", [])
    manifest_by_ref = {}
    duplicate_manifest_refs = []

    for entry in manifest_entries:
        ref = entry.get("ref")
        if not ref:
            duplicate_manifest_refs.append("<missing-ref>")
            continue
        if ref in manifest_by_ref:
            duplicate_manifest_refs.append(ref)
            continue
        manifest_by_ref[ref] = entry

    # Structure validation
    std_books = len(standard)
    cus_books = len(custom)
    std_verses = sum(len(ch) for b in standard for ch in b.get("chapters", []))
    cus_verses = sum(len(ch) for b in custom for ch in b.get("chapters", []))

    total_verses = 0
    verses_with_differences = 0
    total_approved = 0
    total_missing = 0
    total_added = 0
    total_reordered = 0
    total_unapproved = 0
    total_reference_issues = 0
    manifest_approved_verses = 0

    affected_refs = []
    verse_reports = []
    root_causes = Counter()
    seen_refs = set()

    # The runtime manifest is the authoritative approval contract for every
    # intentional Standard -> Custom verse difference.
    if duplicate_manifest_refs:
        total_reference_issues += len(duplicate_manifest_refs)
        root_causes["duplicate_manifest_ref"] += len(duplicate_manifest_refs)
        affected_refs.extend(
            f"manifest duplicate ref: {ref}" for ref in duplicate_manifest_refs
        )

    if manifest.get("totalVerses") != cus_verses:
        total_reference_issues += 1
        root_causes["manifest_total_mismatch"] += 1
        affected_refs.append(
            f"manifest totalVerses={manifest.get('totalVerses')} custom={cus_verses}"
        )

    manifest_sha = manifest.get("customAssetSha256")
    actual_sha = hashlib.sha256(CUSTOM.read_bytes()).hexdigest()
    if manifest_sha != actual_sha:
        total_reference_issues += 1
        root_causes["manifest_custom_sha_mismatch"] += 1
        affected_refs.append(
            f"manifest custom SHA mismatch: manifest={manifest_sha} actual={actual_sha}"
        )

    for bi, (sbook, cbook) in enumerate(zip(standard, custom)):
        s_chapters = sbook.get("chapters", [])
        c_chapters = cbook.get("chapters", [])
        book_name = BOOK_NAMES[bi] if bi < len(BOOK_NAMES) else f"Book {bi+1}"

        if len(s_chapters) != len(c_chapters):
            total_reference_issues += 1
            affected_refs.append(f"{book_name}: chapter count mismatch")
            root_causes["chapter_count_mismatch"] += 1
            continue

        for ci, (schap, cchap) in enumerate(zip(s_chapters, c_chapters)):
            chapter_num = ci + 1

            if len(schap) != len(cchap):
                total_reference_issues += 1
                affected_refs.append(f"{book_name} {chapter_num}: verse count mismatch")
                root_causes["verse_count_mismatch"] += 1
                continue

            for vi, (sverse, cverse) in enumerate(zip(schap, cchap)):
                verse_num = vi + 1
                ref = f"{book_name} {chapter_num}:{verse_num}"
                total_verses += 1
                seen_refs.add(ref)

                approved_entry = manifest_by_ref.get(ref)

                # No textual difference is valid only when the approval manifest
                # also does not claim this verse as intentionally changed.
                if sverse == cverse:
                    if approved_entry is not None:
                        verses_with_differences += 1
                        total_reference_issues += 1
                        affected_refs.append(ref)
                        root_causes["stale_manifest_entry"] += 1
                        verse_reports.append({
                            "ref": ref,
                            "std_text": sverse,
                            "cus_text": cverse,
                            "contract_issue": "manifest lists verse as changed but runtime texts are identical",
                        })
                    continue

                # An intentional change is approved only if BOTH locked texts in
                # the runtime manifest match the current assets exactly.
                if (
                    approved_entry is not None
                    and approved_entry.get("standard") == sverse
                    and approved_entry.get("custom") == cverse
                ):
                    manifest_approved_verses += 1

                    # Preserve the historical diagnostic count for the subset of
                    # token substitutions recognized by the old tokenizer rules.
                    rec = reconcile_verse(sverse, cverse)
                    total_approved += len(rec["approved_substitutions"])
                    continue

                # Any changed verse not exactly authorized by the manifest is a
                # contract violation. Keep the existing token diagnostics so the
                # report still explains missing/added/reordered/replaced content.
                rec = reconcile_verse(sverse, cverse)

                verses_with_differences += 1
                affected_refs.append(ref)

                missing_count = len(rec["missing_tokens"])
                added_count = len(rec["added_tokens"])
                reordered_count = len(rec["reordered_tokens"])
                unapproved_count = len(rec["unapproved_replacements"])

                total_missing += missing_count
                total_added += added_count
                total_reordered += reordered_count
                total_unapproved += unapproved_count

                if missing_count:
                    root_causes["missing_token"] += 1
                if added_count:
                    root_causes["added_token"] += 1
                if reordered_count:
                    root_causes["reordered_token"] += 1
                if unapproved_count:
                    root_causes["unapproved_replacement"] += 1

                if approved_entry is None:
                    root_causes["change_missing_from_manifest"] += 1
                    contract_issue = "changed verse is not present in approval manifest"
                else:
                    root_causes["manifest_text_mismatch"] += 1
                    contract_issue = "runtime verse text does not match locked manifest text"

                # Guarantee that a manifest-contract violation fails even when
                # legacy token diagnostics happen to classify every token as
                # acceptable.
                if not (
                    missing_count
                    or added_count
                    or reordered_count
                    or unapproved_count
                ):
                    total_unapproved += 1

                verse_reports.append({
                    "ref": ref,
                    "std_text": sverse,
                    "cus_text": cverse,
                    "contract_issue": contract_issue,
                    "reconciliation": rec,
                })

    unseen_manifest_refs = sorted(set(manifest_by_ref) - seen_refs)
    for ref in unseen_manifest_refs:
        total_reference_issues += 1
        affected_refs.append(ref)
        root_causes["manifest_ref_not_in_runtime"] += 1
        verse_reports.append({
            "ref": ref,
            "contract_issue": "approval manifest reference does not exist in runtime Bible structure",
        })

    if manifest_approved_verses != len(manifest_by_ref):
        # Specific stale/missing/mismatched entries above already add detailed
        # failures; this records the overall approval-contract mismatch.
        root_causes["manifest_approved_count_mismatch"] += 1

    report = {
        "standard_asset": str(STANDARD),
        "custom_asset": str(CUSTOM),
        "approval_manifest": str(RUNTIME_MANIFEST),
        "structure": {
            "standard_books": std_books,
            "custom_books": cus_books,
            "standard_verses": std_verses,
            "custom_verses": cus_verses,
            "structure_match": std_books == cus_books and std_verses == cus_verses,
        },
        "approval_contract": {
            "manifest_entries": len(manifest_by_ref),
            "validated_changed_verses": manifest_approved_verses,
            "custom_asset_sha256": actual_sha,
            "manifest_sha_matches": manifest_sha == actual_sha,
        },
        "totals": {
            "total_verses_checked": total_verses,
            "verses_with_differences": verses_with_differences,
            "total_approved_substitutions": total_approved,
            "total_missing_tokens": total_missing,
            "total_added_tokens": total_added,
            "total_reordered_tokens": total_reordered,
            "total_unapproved_replacements": total_unapproved,
            "total_reference_issues": total_reference_issues,
        },
        "affected_refs": affected_refs,
        "root_causes": dict(root_causes),
        "verse_details": verse_reports,
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        "utf-8",
    )

    print("=== Full-Bible KJV Custom Reconciliation ===")
    print(f"Standard: {STANDARD}")
    print(f"Custom:   {CUSTOM}")
    print(f"Approval: {RUNTIME_MANIFEST}")
    print(f"Structure match: {report['structure']['structure_match']}")
    print(f"Standard books={std_books}, verses={std_verses}")
    print(f"Custom books={cus_books}, verses={cus_verses}")
    print()
    print("=== Approval Contract ===")
    print(f"Manifest changed verses:        {len(manifest_by_ref)}")
    print(f"Validated changed verses:       {manifest_approved_verses}")
    print(f"Manifest SHA matches custom:    {manifest_sha == actual_sha}")
    print()
    print("=== Totals ===")
    print(f"Total verses checked:           {total_verses}")
    print(f"Verses with violations:         {verses_with_differences}")
    print(f"Legacy approved substitutions:  {total_approved}")
    print(f"Total missing tokens:           {total_missing}")
    print(f"Total added tokens:             {total_added}")
    print(f"Total reordered tokens:         {total_reordered}")
    print(f"Total unapproved replacements:  {total_unapproved}")
    print(f"Total reference issues:         {total_reference_issues}")
    print()

    if affected_refs:
        print("=== Affected References ===")
        for ref in affected_refs:
            print(f"  {ref}")
        print()

    if root_causes:
        print("=== Root Causes ===")
        for cause, count in sorted(root_causes.items()):
            print(f"  {cause}: {count}")
        print()

    print(f"Report: {report_path}")

    passed = (
        report["structure"]["structure_match"]
        and manifest_approved_verses == len(manifest_by_ref)
        and len(manifest_by_ref) == manifest.get("changedVerseCount")
        and manifest_sha == actual_sha
        and verses_with_differences == 0
        and total_missing == 0
        and total_added == 0
        and total_reordered == 0
        and total_unapproved == 0
        and total_reference_issues == 0
    )

    print("RESULT: " + ("PASS" if passed else "FAIL"))
    return 0 if passed else 1

if __name__ == "__main__":
    main()