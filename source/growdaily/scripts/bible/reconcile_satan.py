#!/usr/bin/env python3
"""
Phase 2: Verse-level reconciliation of "Satan" between Standard KJV and Custom KJV.

Produces a machine-readable JSON report with per-verse classification.

Usage:
    python3 scripts/bible/reconcile_satan.py
"""
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path("/home/liongateos/growdaily")
STANDARD = ROOT / "assets/bible/en_kjv.json"
CUSTOM = ROOT / "assets/bible/kjv_modified.json"
REPORT = ROOT / "__tests__/__fixtures__/satan_reconciliation.json"

BOOK_NAMES = [
    "Genesis","Exodus","Leviticus","Numbers","Deuteronomy","Joshua","Judges","Ruth","1 Samuel","2 Samuel",
    "1 Kings","2 Kings","1 Chronicles","2 Chronicles","Ezra","Nehemiah","Esther","Job","Psalms","Proverbs",
    "Ecclesiastes","Song of Solomon","Isaiah","Jeremiah","Lamentations","Ezekiel","Daniel","Hosea","Joel","Amos",
    "Obadiah","Jonah","Micah","Nahum","Habakkuk","Zephaniah","Haggai","Zechariah","Malachi","Matthew",
    "Mark","Luke","John","Acts","Romans","1 Corinthians","2 Corinthians","Galatians","Ephesians","Philippians",
    "Colossians","1 Thessalonians","2 Thessalonians","1 Timothy","2 Timothy","Titus","Philemon","Hebrews","James",
    "1 Peter","2 Peter","1 John","2 John","3 John","Jude","Revelation"
]


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def tokenize(text):
    """
    Deterministic canonical tokenizer.

    Splits on whitespace, strips leading/trailing punctuation, preserves
    internal apostrophes and hyphens. Lowercases for comparison.
    """
    raw_tokens = text.split()
    tokens = []
    for t in raw_tokens:
        # Strip leading/trailing punctuation but keep internal apostrophes/hyphens
        t = t.strip(".,;:!?()[]{}\"'“”‘’«»—–-")
        if t:
            # Normalize unicode (NFC) for consistent comparison
            t = unicodedata.normalize("NFC", t)
            tokens.append(t)
    return tokens


def find_satan_positions(tokens):
    """
    Find positions where the word 'Satan' (case-sensitive, whole-word) appears.
    Handles possessives: 'Satan's' counts as a 'Satan' occurrence.
    Returns list of (index, token) tuples.
    """
    positions = []
    for i, tok in enumerate(tokens):
        # Strip any remaining trailing punctuation for matching
        clean = tok.strip(".,;:!?()[]{}\"'""''«»—–-")
        # Match "Satan" or "Satan's" — the regex (?<![A-Za-z])Satan(?![A-Za-z])
        # treats the apostrophe in "Satan's" as a word boundary.
        if clean == "Satan" or clean == "Satan's":
            positions.append((i, tok))
    return positions


def classify(standard_text, custom_text, std_tokens, cus_tokens, satan_positions):
    """
    Classify each Satan occurrence in the standard text against the custom text.
    """
    results = []
    for pos, std_token in satan_positions:
        ref_label = pos  # position index

        # Get the token at the same position in custom
        if pos < len(cus_tokens):
            cus_token = cus_tokens[pos]
        else:
            cus_token = None

        # Classify
        if cus_token is None:
            classification = "removed"
            cus_display = "<MISSING>"
        elif cus_token == "Satan":
            classification = "unchanged"
            cus_display = cus_token
        elif cus_token.lower() == "satan" or unicodedata.normalize("NFC", cus_token).lower() == "satan":
            classification = "lowercased"
            cus_display = cus_token
        elif cus_token == std_token:
            classification = "unchanged"
            cus_display = cus_token
        else:
            classification = "replaced"
            cus_display = cus_token

        results.append({
            "position": pos,
            "standard_token": std_token,
            "custom_token": cus_display,
            "classification": classification,
        })

    return results


def main():
    standard = load(STANDARD)
    custom = load(CUSTOM)

    # Structure validation
    std_books = len(standard)
    cus_books = len(custom)
    std_verses = sum(len(ch) for b in standard for ch in b.get("chapters", []))
    cus_verses = sum(len(ch) for b in custom for ch in b.get("chapters", []))

    structure = {
        "standard_books": std_books,
        "custom_books": cus_books,
        "standard_verses": std_verses,
        "custom_verses": cus_verses,
        "structure_match": std_books == cus_books and std_verses == cus_verses,
    }

    # Count Satan in each (whole-word, case-sensitive)
    std_satan_count = 0
    cus_satan_count = 0
    cus_satan_lower_count = 0  # ꜱatan or satan (any case variation)

    verse_results = []
    satan_verses = []

    for bi, (sbook, cbook) in enumerate(zip(standard, custom)):
        s_chapters = sbook.get("chapters", [])
        c_chapters = cbook.get("chapters", [])
        book_name = BOOK_NAMES[bi] if bi < len(BOOK_NAMES) else f"Book {bi+1}"
        s_abbrev = sbook.get("abbrev", "?")
        c_abbrev = cbook.get("abbrev", "?")

        for ci, (schap, cchap) in enumerate(zip(s_chapters, c_chapters)):
            chapter_num = ci + 1
            if len(schap) != len(cchap):
                verse_results.append({
                    "book": book_name,
                    "chapter": chapter_num,
                    "issue": "verse_count_mismatch",
                    "standard_verses": len(schap),
                    "custom_verses": len(cchap),
                })
                continue

            for vi, (sverse, cverse) in enumerate(zip(schap, cchap)):
                verse_num = vi + 1
                ref = f"{book_name} {chapter_num}:{verse_num}"

                # Check for Satan in standard
                s_tokens = tokenize(sverse)
                c_tokens = tokenize(cverse)

                s_satan_pos = find_satan_positions(s_tokens)

                if s_satan_pos:
                    std_satan_count += len(s_satan_pos)
                    satan_verses.append({
                        "book": book_name,
                        "abbrev": s_abbrev,
                        "chapter": chapter_num,
                        "verse": verse_num,
                        "ref": ref,
                        "standard_text": sverse,
                        "custom_text": cverse,
                        "standard_token_count": len(s_tokens),
                        "custom_token_count": len(c_tokens),
                        "token_count_match": len(s_tokens) == len(c_tokens),
                        "satan_positions": classify(sverse, cverse, s_tokens, c_tokens, s_satan_pos),
                    })

                # Count Satan in custom (case-sensitive, whole word)
                c_satan = find_satan_positions(c_tokens)
                cus_satan_count += len(c_satan)

                # Count lowercase satan variants in custom
                for tok in c_tokens:
                    clean = tok.strip(".,;:!?()[]{}\"'“”‘’«»—–-")
                    normalized = unicodedata.normalize("NFC", clean).lower()
                    if normalized == "satan" and clean != "Satan":
                        cus_satan_lower_count += 1

    # Per-verse token mismatch check (only for Satan verses)
    token_mismatches = []
    for v in satan_verses:
        if not v["token_count_match"]:
            token_mismatches.append({
                "ref": v["ref"],
                "standard_token_count": v["standard_token_count"],
                "custom_token_count": v["custom_token_count"],
            })

    # Count case-insensitive "satan" in each (handles possessives too)
    std_satan_ci = 0
    cus_satan_ci = 0
    for bi, (sbook, cbook) in enumerate(zip(standard, custom)):
        for schap, cchap in zip(sbook.get("chapters", []), cbook.get("chapters", [])):
            for sverse, cverse in zip(schap, cchap):
                for tok in tokenize(sverse):
                    clean = tok.strip(".,;:!?()[]{}\"'""''«»—–-")
                    normalized = unicodedata.normalize("NFC", clean).lower()
                    # Match "satan" or "satan's"
                    if normalized == "satan" or normalized == "satan's":
                        std_satan_ci += 1
                for tok in tokenize(cverse):
                    clean = tok.strip(".,;:!?()[]{}\"'""''«»—–-")
                    normalized = unicodedata.normalize("NFC", clean).lower()
                    if normalized == "satan" or normalized == "satan's":
                        cus_satan_ci += 1

    report = {
        "standard_asset": str(STANDARD),
        "custom_asset": str(CUSTOM),
        "structure": structure,
        "standard_satan_count_case_sensitive": std_satan_count,
        "custom_satan_count_case_sensitive": cus_satan_count,
        "custom_satan_lowercase_variants": cus_satan_lower_count,
        "standard_satan_count_case_insensitive": std_satan_ci,
        "custom_satan_count_case_insensitive": cus_satan_ci,
        "satan_verse_count": len(satan_verses),
        "token_mismatches_in_satan_verses": token_mismatches,
        "verse_details": satan_verses,
    }

    # Ensure report directory exists
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Summary output
    print("=== Satan Reconciliation Report ===")
    print(f"Standard asset: {STANDARD}")
    print(f"Custom asset:  {CUSTOM}")
    print(f"Structure match: {structure['structure_match']}")
    print(f"Standard verses: {std_verses}")
    print(f"Custom verses:   {cus_verses}")
    print()
    print(f"Standard 'Satan' (case-sensitive): {std_satan_count}")
    print(f"Custom   'Satan' (case-sensitive): {cus_satan_count}")
    print(f"Custom lowercase satan variants:   {cus_satan_lower_count}")
    print(f"Standard 'satan' (case-insensitive): {std_satan_ci}")
    print(f"Custom   'satan' (case-insensitive): {cus_satan_ci}")
    print(f"Satan verses: {len(satan_verses)}")
    print(f"Token mismatches in Satan verses: {len(token_mismatches)}")
    print()

    # Classification breakdown
    classifications = {}
    for v in satan_verses:
        for p in v["satan_positions"]:
            c = p["classification"]
            classifications[c] = classifications.get(c, 0) + 1
    print("Classification breakdown:")
    for c, n in sorted(classifications.items()):
        print(f"  {c}: {n}")

    print()
    print("Sample verses (first 5):")
    for v in satan_verses[:5]:
        print(f"  {v['ref']}: {v['satan_positions']}")
        print(f"    Standard: {v['standard_text'][:100]}...")
        print(f"    Custom:   {v['custom_text'][:100]}...")

    print()
    print(f"Report written to: {REPORT}")


if __name__ == "__main__":
    main()