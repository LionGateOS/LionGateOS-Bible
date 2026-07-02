import json
import re
import sys
from pathlib import Path

ROOT = Path("/home/liongateos/growdaily")
ORIGINAL = ROOT / "assets/bible/en_kjv.json"
MODIFIED = ROOT / "assets/bible/kjv_modified.json"
REPORT = ROOT / "docs/bible/KJV_CUSTOM_REVISION_AUDIT.md"

BOOK_NAMES = [
    "Genesis","Exodus","Leviticus","Numbers","Deuteronomy","Joshua","Judges","Ruth","1 Samuel","2 Samuel",
    "1 Kings","2 Kings","1 Chronicles","2 Chronicles","Ezra","Nehemiah","Esther","Job","Psalms","Proverbs",
    "Ecclesiastes","Song of Solomon","Isaiah","Jeremiah","Lamentations","Ezekiel","Daniel","Hosea","Joel","Amos",
    "Obadiah","Jonah","Micah","Nahum","Habakkuk","Zephaniah","Haggai","Zechariah","Malachi","Matthew",
    "Mark","Luke","John","Acts","Romans","1 Corinthians","2 Corinthians","Galatians","Ephesians","Philippians",
    "Colossians","1 Thessalonians","2 Thessalonians","1 Timothy","2 Timothy","Titus","Philemon","Hebrews","James",
    "1 Peter","2 Peter","1 John","2 John","3 John","Jude","Revelation"
]

TARGET_WORDS = [
    "Holy Ghost",
    "Ghost",
    "ghost",
    # NOTE: "Satan" is a canonical KJV proper name and is intentionally PRESERVED.
    # It must NOT be listed as a target word to eliminate.
    "Adoption",
    "adoption",
    "scapegoat",
    "Easter",
    "Conversation",
    "conversation",
]

CONFIRM_WORDS = [
    "Holy Spirit",
    "His Spirit",
    "his spirit",
    "her spirit",
    "their spirit",
    "my spirit",
    # NOTE: "ꜱatan" replacement was rejected and removed. Satan is preserved as-is.
    "Sonship",
    "sonship",
    "Azazel",
    "Passover",
    "Conduct",
    "conduct",
]

def load(path):
    if not path.exists():
        raise SystemExit(f"Missing file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))

def exact_count(text, word):
    if " " in word:
        return text.count(word)
    return len(re.findall(rf"(?<![A-Za-z]){re.escape(word)}(?![A-Za-z])", text))

def counts(data, words):
    text = json.dumps(data, ensure_ascii=False)
    return {word: exact_count(text, word) for word in words}

def iter_verses(data):
    for bi, book in enumerate(data):
        abbrev = book.get("abbrev", "?")
        chapters = book.get("chapters", [])
        for ci, chapter in enumerate(chapters, start=1):
            for vi, verse in enumerate(chapter, start=1):
                book_name = BOOK_NAMES[bi] if bi < len(BOOK_NAMES) else f"Book {bi+1}"
                yield bi, ci, vi, abbrev, f"{book_name} {ci}:{vi}", verse

def find_remaining_targets(data):
    hits = []
    for bi, ci, vi, abbrev, ref, verse in iter_verses(data):
        found = []
        for word in TARGET_WORDS:
            if exact_count(verse, word):
                found.append(word)
        if found:
            hits.append((ref, abbrev, found, verse))
    return hits

def structure_issues(original, modified):
    issues = []

    if not isinstance(original, list):
        issues.append("Original is not a top-level list.")
    if not isinstance(modified, list):
        issues.append("Modified is not a top-level list.")
    if not isinstance(original, list) or not isinstance(modified, list):
        return issues

    if len(original) != 66:
        issues.append(f"Original book count is {len(original)}, expected 66.")
    if len(modified) != 66:
        issues.append(f"Modified book count is {len(modified)}, expected 66.")

    for bi, (ob, mb) in enumerate(zip(original, modified)):
        book_name = BOOK_NAMES[bi] if bi < len(BOOK_NAMES) else f"Book {bi+1}"
        if ob.get("abbrev") != mb.get("abbrev"):
            issues.append(f"{book_name}: abbrev changed from {ob.get('abbrev')} to {mb.get('abbrev')}.")
        if len(ob.get("chapters", [])) != len(mb.get("chapters", [])):
            issues.append(f"{book_name}: chapter count changed.")
            continue
        for ci, (oc, mc) in enumerate(zip(ob.get("chapters", []), mb.get("chapters", [])), start=1):
            if len(oc) != len(mc):
                issues.append(f"{book_name} {ci}: verse count changed from {len(oc)} to {len(mc)}.")

    return issues

def check_critical_verses(modified):
    checks = []

    def verse(book_idx, chapter, verse_num):
        return modified[book_idx]["chapters"][chapter - 1][verse_num - 1]

    luke = verse(41, 23, 46)
    luke_expected = "And when Jesus had cried with a loud voice, he said, Father, into thy hands I commend my spirit: and having said thus, He gave up His Spirit."
    checks.append(("Luke 23:46 exact wording", luke == luke_expected, luke))

    acts = verse(43, 12, 4)
    checks.append(("Acts 12:4 has Passover", "Passover" in acts and "Easter" not in acts, acts))

    lev = modified[2]["chapters"][15]
    lev_text = json.dumps(lev, ensure_ascii=False)
    checks.append(("Leviticus 16 has no scapegoat", "scapegoat" not in lev_text, lev_text))

    return checks

def scan_code_refs():
    patterns = re.compile(r"strong|strongs|concordance|en_kjv|kjv_modified|bibleStore|redLetters|translation", re.I)
    refs = []

    for base in ["logic", "screens", "assets"]:
        folder = ROOT / base
        if not folder.exists():
            continue

        for path in folder.rglob("*"):
            if not path.is_file():
                continue

            rel = path.relative_to(ROOT)

            if "node_modules" in rel.parts:
                continue

            if "strong" in str(rel).lower():
                refs.append(f"{rel}: file/path name contains strong")

            if path.suffix.lower() not in [".js", ".jsx", ".ts", ".tsx"]:
                continue

            try:
                lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            except Exception:
                continue

            for idx, line in enumerate(lines, start=1):
                if patterns.search(line):
                    refs.append(f"{rel}:{idx}: {line.strip()}")

    return refs[:300]

def main():
    original = load(ORIGINAL)
    modified = load(MODIFIED)

    original_counts = counts(original, TARGET_WORDS + CONFIRM_WORDS)
    modified_counts = counts(modified, TARGET_WORDS + CONFIRM_WORDS)

    issues = structure_issues(original, modified)
    remaining = find_remaining_targets(modified)
    critical = check_critical_verses(modified)
    code_refs = scan_code_refs()

    passed = (
        not issues
        and not remaining
        and all(ok for _, ok, _ in critical)
        and len(modified) == 66
    )

    report = []
    report.append("# GrowDaily Custom KJV Full Audit")
    report.append("")
    report.append("## Result")
    report.append("")
    report.append("**PASS**" if passed else "**FAIL**")
    report.append("")
    report.append("## Files")
    report.append("")
    report.append(f"- Original: `{ORIGINAL}`")
    report.append(f"- Modified: `{MODIFIED}`")
    report.append("")
    report.append("## Structure Check")
    report.append("")
    if issues:
        for issue in issues:
            report.append(f"- FAIL: {issue}")
    else:
        report.append("- PASS: Top-level JSON remains a 66-book list.")
        report.append("- PASS: Book abbreviations match.")
        report.append("- PASS: Chapter and verse counts match.")
    report.append("")
    report.append("## Target Word Counts")
    report.append("")
    report.append("| Word | Original | Modified |")
    report.append("|---|---:|---:|")
    for word in TARGET_WORDS:
        report.append(f"| `{word}` | {original_counts[word]} | {modified_counts[word]} |")
    report.append("")
    report.append("## Confirmed Replacement Word Counts")
    report.append("")
    report.append("| Word | Original | Modified |")
    report.append("|---|---:|---:|")
    for word in CONFIRM_WORDS:
        report.append(f"| `{word}` | {original_counts[word]} | {modified_counts[word]} |")
    report.append("")
    report.append("## Remaining Target Hits")
    report.append("")
    if remaining:
        for ref, abbrev, found, verse in remaining:
            report.append(f"- FAIL: {ref} `{abbrev}` still contains {found}: {verse}")
    else:
        report.append("- PASS: No remaining target terms found anywhere in modified Bible JSON.")
    report.append("")
    report.append("## Critical Verse Checks")
    report.append("")
    for label, ok, sample in critical:
        report.append(f"- {'PASS' if ok else 'FAIL'}: {label}")
        if not ok:
            report.append(f"  - Sample: {sample}")
    report.append("")
    report.append("## Strong's / Bible Code Reference Scan")
    report.append("")
    report.append("This does not modify app code. It lists places that must be checked before switching the app to `kjv_modified.json`.")
    report.append("")
    if code_refs:
        for ref in code_refs:
            report.append(f"- `{ref}`")
    else:
        report.append("- No Strong's/Bible references found by scan.")
    report.append("")
    report.append("## Strong's Safety Note")
    report.append("")
    report.append("- The modified JSON preserves the same 66-book/chapter/verse structure.")
    report.append("- The app must not be switched to `kjv_modified.json` until Strong's lookup is confirmed to use stable references or a compatibility layer is added.")
    report.append("- If Strong's depends on exact visible KJV words, changed words such as `Satan`, `adoption`, `scapegoat`, `Easter`, `conversation`, and `ghost` need alias support.")
    report.append("")

    REPORT.write_text("\n".join(report), encoding="utf-8")

    print("=== GrowDaily Custom KJV Full Audit ===")
    print("RESULT:", "PASS" if passed else "FAIL")
    print("Structure issues:", len(issues))
    print("Remaining target hits:", len(remaining))
    print("Critical checks passed:", sum(1 for _, ok, _ in critical if ok), "/", len(critical))
    print("Report:", REPORT)
    print("")
    print("Target counts in modified:")
    for word in TARGET_WORDS:
        print(f"{word}: {modified_counts[word]}")
    print("")
    print("Strong's/code references found:", len(code_refs))

    if not passed:
        sys.exit(1)

if __name__ == "__main__":
    main()
