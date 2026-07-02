#!/usr/bin/env python3
"""
Repair the Standard KJV (en_kjv.json) by reprocessing the pre-cleaning backup.

The original en_kjv.json (thiagobodruk 1769 KJV source) used braces {} to mark
italicized translator-added words AND publisher editorial notes. A prior
cleaning script deleted ALL brace content, losing 21,530 canonical KJV words.

This script applies the correct cleaning:
  - Italicized words (e.g., {and}, {was}, {it was}): UNWRAP (remove braces, keep text)
  - Editorial notes (e.g., {grass: Heb. tender grass}): REMOVE (delete braces and content)
  - Guillemet blocks (e.g., « by Phebe servant...»): REMOVE (publisher apparatus)

The result is a clean, authentic KJV text with:
  - All canonical translator-added words preserved (without braces)
  - All publisher editorial apparatus removed
  - No braces or guillemet in any verse
  - 66 books, 1189 chapters, 31100 verses

Usage:
    python3 scripts/bible/repair_en_kjv.py
"""
import copy
import json
import re
from pathlib import Path

ROOT = Path("/home/liongateos/growdaily")
BACKUP = ROOT / "assets/bible/en_kjv.json.before-clean-20260607-211743"
OUTPUT = ROOT / "assets/bible/en_kjv.json"

BRACE_BLOCK_RE = re.compile(r"\{([^{}]*)\}")
GUILLEMET_BLOCK_RE = re.compile(r"\s*«[^»]*»")
SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,.;:?!])")
MULTISPACE_RE = re.compile(r"\s{2,}")

EDITORIAL_BRACE_MARKERS = (
    "heb.", "gr.", "chald.", "syr.", "alex.", "sept.", "vulg.",
    "or,", "that is,", "i.e.", "i. e.",
)
EDITORIAL_BRACE_PREFIXES = (
    "written from ", "written to ",
    "the first epistle", "the second epistle", "the epistle",
)


def is_editorial_brace_block(inner):
    """Classify a brace block's content as editorial apparatus or canonical text."""
    normalized = " ".join(inner.split())
    lower = normalized.lower()
    if not normalized:
        return False
    if ":" in normalized:
        return True
    if "..." in normalized:
        return True
    if any(marker in lower for marker in EDITORIAL_BRACE_MARKERS):
        return True
    if any(lower.startswith(prefix) for prefix in EDITORIAL_BRACE_PREFIXES):
        return True
    return False


def strip_inline_brace_blocks(text):
    """
    Clean a verse: unwrap italicized words, remove editorial apparatus.
    """
    def repl(match):
        inner = " ".join(match.group(1).split())
        if is_editorial_brace_block(inner):
            return ""
        return inner

    cleaned = text
    while True:
        next_cleaned = BRACE_BLOCK_RE.sub(repl, cleaned)
        if next_cleaned == cleaned:
            break
        cleaned = next_cleaned

    cleaned = GUILLEMET_BLOCK_RE.sub("", cleaned)
    cleaned = cleaned.replace("{", "").replace("}", "")
    cleaned = cleaned.replace("«", "").replace("»", "")
    cleaned = MULTISPACE_RE.sub(" ", cleaned)
    cleaned = SPACE_BEFORE_PUNCT_RE.sub(r"\1", cleaned)
    return cleaned.strip()


def structure_counts(data):
    book_count = len(data)
    chapter_count = sum(len(book["chapters"]) for book in data)
    verse_count = sum(len(ch) for book in data for ch in book["chapters"])
    return {"books": book_count, "chapters": chapter_count, "verses": verse_count}


def main():
    if not BACKUP.exists():
        raise SystemExit(f"FAIL: backup file not found: {BACKUP}")

    original = json.loads(BACKUP.read_text(encoding="utf-8"))

    if not isinstance(original, list) or len(original) != 66:
        raise SystemExit(f"FAIL: backup is not a 66-book list (got {type(original).__name__}, len={len(original) if isinstance(original, list) else 'N/A'})")

    original_counts = structure_counts(original)
    print(f"Input (backup): {original_counts['books']} books, {original_counts['chapters']} chapters, {original_counts['verses']} verses")

    # Count verses with braces/guillemet before cleaning
    brace_verses = 0
    guillemet_verses = 0
    for book in original:
        for chapter in book["chapters"]:
            for verse in chapter:
                if "{" in verse or "}" in verse:
                    brace_verses += 1
                if "«" in verse or "»" in verse:
                    guillemet_verses += 1
    print(f"Verses with braces before cleaning: {brace_verses}")
    print(f"Verses with guillemet before cleaning: {guillemet_verses}")

    # Deep copy and clean
    repaired = copy.deepcopy(original)
    for bi, book in enumerate(repaired):
        for ci, chapter in enumerate(book["chapters"]):
            for vi, verse in enumerate(chapter):
                repaired[bi]["chapters"][ci][vi] = strip_inline_brace_blocks(verse)

    # Verify structure preserved
    repaired_counts = structure_counts(repaired)
    print(f"Output (repaired): {repaired_counts['books']} books, {repaired_counts['chapters']} chapters, {repaired_counts['verses']} verses")

    # Verify no braces/guillemet remain
    remaining_braces = 0
    remaining_guillemet = 0
    for book in repaired:
        for chapter in book["chapters"]:
            for verse in chapter:
                if "{" in verse or "}" in verse:
                    remaining_braces += 1
                if "«" in verse or "»" in verse:
                    remaining_guillemet += 1
    print(f"Remaining braces: {remaining_braces}")
    print(f"Remaining guillemet: {remaining_guillemet}")

    # Verify Genesis 1:12
    gen_1_12 = repaired[0]["chapters"][0][11]
    expected = "And the earth brought forth grass, and herb yielding seed after his kind, and the tree yielding fruit, whose seed was in itself, after his kind: and God saw that it was good."
    print(f"\nGenesis 1:12: {gen_1_12}")
    print(f"Matches authentic KJV: {gen_1_12 == expected}")

    # Write output
    OUTPUT.write_text(json.dumps(repaired, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nRepaired en_kjv.json written to: {OUTPUT}")

    # Summary
    passed = (
        repaired_counts["books"] == 66
        and repaired_counts["chapters"] == 1189
        and repaired_counts["verses"] == 31100
        and remaining_braces == 0
        and remaining_guillemet == 0
        and gen_1_12 == expected
    )
    print(f"\nRESULT: {'PASS' if passed else 'FAIL'}")


if __name__ == "__main__":
    main()