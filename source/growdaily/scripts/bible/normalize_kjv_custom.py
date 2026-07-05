import copy
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "assets/bible/en_kjv.json"
OUTPUT = ROOT / "assets/bible/kjv_modified.json"
REPORT = ROOT / "docs/bible/KJV_CUSTOM_REVISION_VERIFICATION.txt"

BOOK_NAMES = [
    "Genesis","Exodus","Leviticus","Numbers","Deuteronomy","Joshua","Judges","Ruth","1 Samuel","2 Samuel",
    "1 Kings","2 Kings","1 Chronicles","2 Chronicles","Ezra","Nehemiah","Esther","Job","Psalms","Proverbs",
    "Ecclesiastes","Song of Solomon","Isaiah","Jeremiah","Lamentations","Ezekiel","Daniel","Hosea","Joel","Amos",
    "Obadiah","Jonah","Micah","Nahum","Habakkuk","Zephaniah","Haggai","Zechariah","Malachi","Matthew",
    "Mark","Luke","John","Acts","Romans","1 Corinthians","2 Corinthians","Galatians","Ephesians","Philippians",
    "Colossians","1 Thessalonians","2 Thessalonians","1 Timothy","2 Timothy","Titus","Philemon","Hebrews","James",
    "1 Peter","2 Peter","1 John","2 John","3 John","Jude","Revelation"
]

GHOST_PHRASES = [
    "gave up the ghost",
    "yielded up the ghost",
    "give up the ghost",
    "given up the ghost",
    "giveth up the ghost",
    "giving up of the ghost",
]

GHOST_REPLACEMENTS_BY_REF = {
    ("gn", 25, 8): [("gave up the ghost", "gave up his spirit")],
    ("gn", 25, 17): [("gave up the ghost", "gave up his spirit")],
    ("gn", 35, 29): [("gave up the ghost", "gave up his spirit")],
    ("gn", 49, 33): [("yielded up the ghost", "yielded up his spirit")],

    ("job", 3, 11): [("give up the ghost", "give up my spirit")],
    ("job", 10, 18): [("given up the ghost", "given up my spirit")],
    ("job", 11, 20): [("giving up of the ghost", "giving up of the spirit")],
    ("job", 13, 19): [("give up the ghost", "give up my spirit")],
    ("job", 14, 10): [("giveth up the ghost", "giveth up his spirit")],

    ("jr", 15, 9): [("given up the ghost", "given up her spirit")],
    ("lm", 1, 19): [("gave up the ghost", "gave up their spirit")],

    ("mt", 27, 50): [("yielded up the ghost", "yielded up His Spirit")],
    ("mk", 15, 37): [("gave up the ghost", "gave up His Spirit")],
    ("mk", 15, 39): [("gave up the ghost", "gave up His Spirit")],
    ("lk", 23, 46): [(
        "And when Jesus had cried with a loud voice, he said, Father, into thy hands I commend my spirit: and having said thus, he gave up the ghost.",
        "And when Jesus had cried with a loud voice, he said, Father, into thy hands I commend my spirit: and having said thus, He gave up His Spirit."
    )],
    ("jo", 19, 30): [("gave up the ghost", "gave up His Spirit")],

    ("act", 5, 5): [("gave up the ghost", "gave up his spirit")],
    ("act", 5, 10): [("yielded up the ghost", "yielded up her spirit")],
    ("act", 12, 23): [("gave up the ghost", "gave up his spirit")],
}

VERSE_REPLACEMENTS_BY_REF = {
    ("gn", 1, 2): [
        ("And the earth was without form,", "And the earth became without form,"),
    ],
    ("zc", 7, 12): [
        ("hath sent in his spirit by the former prophets", "hath sent by his spirit by the former prophets"),
    ],
    ("lk", 14, 26): [
        ("hate not", "love less than"),
    ],
    ("gl", 5, 22): [
        (
            "But the fruit of the Spirit is love, joy, peace, longsuffering, gentleness, goodness, faith,",
            "But the fruit of the Spirit is love, joy, peace, patience and mercy, kindness, goodness and generosity, faith,",
        ),
    ],
    ("gl", 5, 23): [
        (
            "Meekness, temperance: against such there is no law.",
            "Meekness and humility, self-control: against such there is no law.",
        ),
    ],
}

BRACE_BLOCK_RE = re.compile(r"\{([^{}]*)\}")
GUILLEMET_BLOCK_RE = re.compile(r"\s*«[^»]*»")
SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,.;:?!])")
MULTISPACE_RE = re.compile(r"\s{2,}")

EDITORIAL_BRACE_MARKERS = (
    "heb.",
    "gr.",
    "chald.",
    "syr.",
    "alex.",
    "sept.",
    "vulg.",
    "or,",
    "that is,",
    "i.e.",
    "i. e.",
)

EDITORIAL_BRACE_PREFIXES = (
    "written from ",
    "written to ",
    "the first epistle",
    "the second epistle",
    "the epistle",
)

def load_json(path):
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))

def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def exact_word_replace(text, old, new):
    return re.sub(rf"(?<![A-Za-z]){re.escape(old)}(?![A-Za-z])", new, text)

def count_word(text, word):
    return len(re.findall(rf"(?<![A-Za-z]){re.escape(word)}(?![A-Za-z])", text))

def count_all(data):
    text = json.dumps(data, ensure_ascii=False)
    return {
        "Holy Ghost": text.count("Holy Ghost"),
        "Ghost": count_word(text, "Ghost"),
        "ghost": count_word(text, "ghost"),
        "Satan": count_word(text, "Satan"),
        "adoption": count_word(text, "adoption"),
        "Adoption": count_word(text, "Adoption"),
        "scapegoat": count_word(text, "scapegoat"),
        "Easter": count_word(text, "Easter"),
        "conversation": count_word(text, "conversation"),
        "Conversation": count_word(text, "Conversation"),
    }

def structure_counts(data):
    book_count = len(data)
    chapter_count = 0
    verse_count = 0
    for book in data:
        chapter_count += len(book["chapters"])
        for chapter in book["chapters"]:
            verse_count += len(chapter)
    return {
        "books": book_count,
        "chapters": chapter_count,
        "verses": verse_count,
    }

def brace_verse_count(data):
    count = 0
    for book in data:
        for chapter in book["chapters"]:
            for verse in chapter:
                if "{" in verse or "}" in verse:
                    count += 1
    return count

def is_editorial_brace_block(inner):
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

def collect_targets(data):
    targets = {
        "ghost": [],
        "adoption": [],
        "scapegoat": [],
        "easter": [],
        "conversation": [],
    }

    for bi, book in enumerate(data):
        abbrev = book["abbrev"]
        for ci, chapter in enumerate(book["chapters"]):
            chapter_num = ci + 1
            for vi, verse in enumerate(chapter):
                verse_num = vi + 1
                ref = f"{BOOK_NAMES[bi]} {chapter_num}:{verse_num}"

                if any(phrase in verse for phrase in GHOST_PHRASES):
                    targets["ghost"].append((bi, ci, vi, ref, verse))

                if count_word(verse, "adoption") or count_word(verse, "Adoption"):
                    targets["adoption"].append((bi, ci, vi, ref, verse))

                if abbrev == "lv" and chapter_num == 16 and count_word(verse, "scapegoat"):
                    targets["scapegoat"].append((bi, ci, vi, ref, verse))

                if abbrev == "act" and chapter_num == 12 and verse_num == 4:
                    targets["easter"].append((bi, ci, vi, ref, verse))

                if count_word(verse, "conversation") or count_word(verse, "Conversation"):
                    targets["conversation"].append((bi, ci, vi, ref, verse))

    return targets

def transform_verse(text, abbrev, chapter_num, verse_num):
    key = (abbrev, chapter_num, verse_num)

    text = text.replace("Holy Ghost", "Holy Spirit")
    text = exact_word_replace(text, "Ghost", "Spirit")

    for old, new in GHOST_REPLACEMENTS_BY_REF.get(key, []):
        text = text.replace(old, new)

    # NOTE: "Satan" is a proper name in the KJV and must NOT be altered.
    # A previous version replaced it with "ꜱatan" (U+A731) - that was rejected
    # by the project owner because it breaks case-insensitive search and
    # removes the canonical proper name. Do not reintroduce this replacement.

    text = exact_word_replace(text, "Adoption", "Sonship")
    text = exact_word_replace(text, "adoption", "sonship")

    # Scapegoat → Azazel: use exact_word_replace (1:1 token swap) to preserve
    # articles ("the", "a") and maintain token count alignment with the KJV.
    # The previous version used phrase-level replacements like
    # "to be the scapegoat" → "to be Azazel" which deleted the article "the",
    # reducing token count. The 1:1 word replacement fixes that.
    if abbrev == "lv" and chapter_num == 16:
        text = exact_word_replace(text, "scapegoat", "Azazel")
        # R014: "a Azazel" → "an Azazel" in Leviticus 16:10 only.
        # "scapegoat" begins with a consonant ("a scapegoat" is correct KJV),
        # but "Azazel" begins with a vowel, requiring "an Azazel" for grammar.
        # This is a 1:1 token swap ("a" → "an") that preserves token count.
        if key == ("lv", 16, 10):
            text = text.replace("for a Azazel", "for an Azazel")

    if key == ("act", 12, 4):
        text = text.replace("after Easter", "after Passover")
        text = text.replace("{Easter: Gr. Passover}", "{Gr. Passover}")

    text = exact_word_replace(text, "Conversation", "Conduct")
    text = exact_word_replace(text, "conversation", "conduct")

    for old, new in VERSE_REPLACEMENTS_BY_REF.get(key, []):
        text = text.replace(old, new)

    return strip_inline_brace_blocks(text)

def add_samples(report, title, targets, modified):
    report.append("")
    report.append(title)
    for i, (bi, ci, vi, ref, before) in enumerate(targets, start=1):
        after = modified[bi]["chapters"][ci][vi]
        report.append(f"{i}. {ref}")
        report.append(f"   Before: {before}")
        report.append(f"   After:  {after}")

def main():
    original = load_json(INPUT)

    if not isinstance(original, list):
        raise SystemExit("FAIL: input is not a list")
    if len(original) != 66:
        raise SystemExit(f"FAIL: input book count is {len(original)}, expected 66")

    for book in original:
        if not isinstance(book, dict) or "abbrev" not in book or "chapters" not in book:
            raise SystemExit("FAIL: invalid book structure")

    targets = collect_targets(original)
    original_counts = count_all(original)
    original_structure = structure_counts(original)

    modified = copy.deepcopy(original)

    for bi, book in enumerate(modified):
        abbrev = book["abbrev"]
        for ci, chapter in enumerate(book["chapters"]):
            for vi, verse in enumerate(chapter):
                modified[bi]["chapters"][ci][vi] = transform_verse(
                    verse,
                    abbrev,
                    ci + 1,
                    vi + 1,
                )

    save_json(OUTPUT, modified)
    remaining = count_all(modified)
    modified_structure = structure_counts(modified)
    remaining_brace_verses = brace_verse_count(modified)

    luke_after = modified[41]["chapters"][22][45]
    luke_expected = "And when Jesus had cried with a loud voice, he said, Father, into thy hands I commend my spirit: and having said thus, He gave up His Spirit."
    acts_12_4_after = modified[43]["chapters"][11][3]
    luke_23_46_after = modified[41]["chapters"][22][45]
    lev_16_8_after = modified[2]["chapters"][15][7]
    gen_1_sample = modified[0]["chapters"][0][:31]

    passed = (
        len(modified) == 66
        and modified_structure["chapters"] == 1189
        and modified_structure["verses"] == 31100
        and remaining_brace_verses == 0
        and remaining["Holy Ghost"] == 0
        and remaining["Ghost"] == 0
        and remaining["ghost"] == 0
        # "Satan" is a proper name and must be PRESERVED (not removed).
        # The rejected normalization replaced it with "ꜱatan" (U+A731).
        and remaining["Satan"] == original_counts["Satan"]
        and remaining["adoption"] == 0
        and remaining["Adoption"] == 0
        and remaining["scapegoat"] == 0
        and remaining["Easter"] == 0
        and remaining["conversation"] == 0
        and remaining["Conversation"] == 0
        and len(targets["ghost"]) == 19
        and len(targets["adoption"]) == 5
        and len(targets["scapegoat"]) == 3
        and len(targets["easter"]) == 1
        and len(targets["conversation"]) == 20
        and original_counts["scapegoat"] == 4
        and (original_counts["conversation"] + original_counts["Conversation"]) == 20
        and luke_after == luke_expected
        and "Passover" in acts_12_4_after
        and "Easter" not in acts_12_4_after
        and "Azazel" in lev_16_8_after
        and all("{" not in verse and "}" not in verse for verse in gen_1_sample)
    )

    report = []
    report.append("=== GrowDaily KJV Custom Revision Verification v3 ===")
    report.append(f"Input file: {INPUT}")
    report.append(f"Output file: {OUTPUT}")
    report.append(f"Input book count: {original_structure['books']}")
    report.append(f"Input chapter count: {original_structure['chapters']}")
    report.append(f"Input verse count: {original_structure['verses']}")
    report.append(f"Output book count: {modified_structure['books']}")
    report.append(f"Output chapter count: {modified_structure['chapters']}")
    report.append(f"Output verse count: {modified_structure['verses']}")
    report.append(f"Output still has exactly 66 books: {modified_structure['books'] == 66}")
    report.append(f"Output still has exactly 1189 chapters: {modified_structure['chapters'] == 1189}")
    report.append(f"Output still has exactly 31100 verses: {modified_structure['verses'] == 31100}")
    report.append(f"Verses still containing braces after cleanup: {remaining_brace_verses}")
    report.append("")
    report.append("Original counts:")
    for key, value in original_counts.items():
        report.append(f"  {key}: {value}")
    report.append("")
    report.append("Remaining counts after modification:")
    for key, value in remaining.items():
        report.append(f"  {key}: {value}")
    report.append("")
    report.append("Target groups:")
    report.append(f"  Ghost verses: {len(targets['ghost'])}")
    report.append(f"  Adoption verses: {len(targets['adoption'])}")
    report.append(f"  Scapegoat verses: {len(targets['scapegoat'])} with {original_counts['scapegoat']} original occurrences")
    report.append(f"  Easter verses: {len(targets['easter'])}")
    report.append(f"  Conversation verses: {len(targets['conversation'])} with {original_counts['conversation'] + original_counts['Conversation']} original occurrences")
    report.append(f"  Luke 23:46 exact: {luke_after == luke_expected}")
    report.append(f"  Acts 12:4 has Passover and not Easter: {'Passover' in acts_12_4_after and 'Easter' not in acts_12_4_after}")
    report.append(f"  Leviticus 16:8 has Azazel: {'Azazel' in lev_16_8_after}")
    report.append(f"  Genesis 1 sample verses contain no braces: {all('{' not in verse and '}' not in verse for verse in gen_1_sample)}")

    add_samples(report, "Ghost verse samples", targets["ghost"], modified)
    add_samples(report, "Adoption verse samples", targets["adoption"], modified)
    add_samples(report, "Scapegoat verse samples", targets["scapegoat"], modified)
    add_samples(report, "Easter verse sample", targets["easter"], modified)
    add_samples(report, "Conversation verse samples", targets["conversation"], modified)

    report.append("")
    report.append("=== SUMMARY ===")
    report.append("RESULT: " + ("PASS" if passed else "FAIL"))

    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")

    print("=== SUMMARY ===")
    print(f"Input book count: {original_structure['books']}")
    print(f"Input chapter count: {original_structure['chapters']}")
    print(f"Input verse count: {original_structure['verses']}")
    print(f"Output book count: {modified_structure['books']}")
    print(f"Output chapter count: {modified_structure['chapters']}")
    print(f"Output verse count: {modified_structure['verses']}")
    print(f"Output still has exactly 66 books: {modified_structure['books'] == 66}")
    print(f"Output still has exactly 1189 chapters: {modified_structure['chapters'] == 1189}")
    print(f"Output still has exactly 31100 verses: {modified_structure['verses'] == 31100}")
    print(f"Verses still containing braces after cleanup: {remaining_brace_verses}")
    print(f"Ghost verses found: {len(targets['ghost'])}")
    print(f"Adoption verses found: {len(targets['adoption'])}")
    print(f"Scapegoat verses found: {len(targets['scapegoat'])}")
    print(f"Scapegoat original occurrences: {original_counts['scapegoat']}")
    print(f"Easter verses found: {len(targets['easter'])}")
    print(f"Conversation verses found: {len(targets['conversation'])}")
    print(f"Conversation original occurrences: {original_counts['conversation'] + original_counts['Conversation']}")
    print(f"Remaining target counts: {remaining}")
    print(f"Luke 23:46 exact: {luke_after == luke_expected}")
    print(f"Acts 12:4 has Passover and not Easter: {'Passover' in acts_12_4_after and 'Easter' not in acts_12_4_after}")
    print(f"Leviticus 16:8 has Azazel: {'Azazel' in lev_16_8_after}")
    print("RESULT:", "PASS" if passed else "FAIL")
    print(f"Output file: {OUTPUT}")
    print(f"Detailed report: {REPORT}")

if __name__ == "__main__":
    main()
