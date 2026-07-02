#!/usr/bin/env python3
import hashlib
import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

if len(sys.argv) != 6:
    raise SystemExit(
        "Usage: build_rv1909.py USFX BOOK_NAMES KJV AUDIT_JSON OUTPUT"
    )

usfx_path = Path(sys.argv[1])
names_path = Path(sys.argv[2])
kjv_path = Path(sys.argv[3])
audit_path = Path(sys.argv[4])
output_path = Path(sys.argv[5])

def local_name(tag):
    return tag.rsplit("}", 1)[-1]

def clean_text(value):
    value = unicodedata.normalize("NFC", value)
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"\s+([,.;:?!])", r"\1", value)
    value = re.sub(r"([¿¡])\s+", r"\1", value)
    return value

skip_tags = {
    "f", "fe", "fm", "fr", "fk", "fq", "fqa",
    "fl", "fp", "ft", "fv", "fdc",
    "x", "xo", "xk", "xq", "xt", "xdc",
    "fig",
}

audit = json.loads(audit_path.read_text(encoding="utf-8"))

expected_empty = {
    (
        entry["book_number"],
        entry["book_code"],
        entry["chapter"],
        entry["verse"],
    )
    for entry in audit["coordinate_differences"]["usfx_not_sql"]
}

names_root = ET.parse(names_path).getroot()

name_entries = [
    (
        element.attrib["code"],
        (
            element.attrib.get("long")
            or element.attrib.get("short")
            or element.attrib.get("abbr")
        ).strip(),
    )
    for element in names_root.findall("book")
]

if len(name_entries) != 66:
    raise RuntimeError(
        f"Expected 66 Spanish book names; found {len(name_entries)}"
    )

spanish_names = dict(name_entries)
expected_codes = [code for code, _ in name_entries]

with kjv_path.open("r", encoding="utf-8") as handle:
    kjv_books = json.load(handle)

if len(kjv_books) != 66:
    raise RuntimeError(
        f"Expected 66 KJV books; found {len(kjv_books)}"
    )

root = ET.parse(usfx_path).getroot()

source_books = [
    element
    for element in list(root)
    if local_name(element.tag) == "book"
]

source_codes = [
    element.attrib.get("id", "").strip()
    for element in source_books
]

if source_codes != expected_codes:
    raise RuntimeError(
        "USFX book order does not match BookNames.xml"
    )

all_markers = []
empty_markers = []
output_books = []

for book_number, book in enumerate(source_books, start=1):
    code = source_codes[book_number - 1]

    state = {
        "chapter": None,
        "verse": None,
        "parts": [],
    }

    chapters = {}

    def flush():
        verse = state["verse"]

        if verse is None:
            return

        chapter_number = state["chapter"]
        text = clean_text("".join(state["parts"]))

        record = {
            "book_number": book_number,
            "book_code": code,
            "chapter": chapter_number,
            "verse": verse,
            "text": text,
        }

        all_markers.append(record)

        chapter = chapters.setdefault(chapter_number, {})

        if verse in chapter:
            raise RuntimeError(
                f"Duplicate marker: {code} {chapter_number}:{verse}"
            )

        chapter[verse] = text

        if not text:
            empty_markers.append(record)

        state["verse"] = None
        state["parts"] = []

    def walk(element):
        tag = local_name(element.tag)

        if tag == "c":
            flush()
            state["chapter"] = int(element.attrib["id"])

        elif tag == "v":
            flush()

            if state["chapter"] is None:
                raise RuntimeError(
                    f"{code}: verse marker before chapter"
                )

            state["verse"] = int(element.attrib["id"])
            state["parts"] = []

        elif tag == "ve":
            flush()
            return

        elif tag in skip_tags:
            return

        elif state["verse"] is not None and element.text:
            state["parts"].append(element.text)

        for child in list(element):
            walk(child)

            if state["verse"] is not None and child.tail:
                state["parts"].append(child.tail)

    walk(book)
    flush()

    chapter_numbers = sorted(chapters)

    if chapter_numbers != list(
        range(1, len(chapter_numbers) + 1)
    ):
        raise RuntimeError(
            f"Non-contiguous chapters in {code}"
        )

    chapter_arrays = []

    for chapter_number in chapter_numbers:
        marker_map = chapters[chapter_number]
        marker_numbers = sorted(marker_map)

        if marker_numbers != list(
            range(1, max(marker_numbers) + 1)
        ):
            raise RuntimeError(
                f"Non-contiguous markers in {code} {chapter_number}"
            )

        nonempty_numbers = [
            number
            for number in marker_numbers
            if marker_map[number]
        ]

        if not nonempty_numbers:
            raise RuntimeError(
                f"No verse text in {code} {chapter_number}"
            )

        last_real_verse = max(nonempty_numbers)

        if nonempty_numbers != list(
            range(1, last_real_verse + 1)
        ):
            raise RuntimeError(
                f"Internal empty marker in {code} {chapter_number}"
            )

        trailing_numbers = list(
            range(last_real_verse + 1, max(marker_numbers) + 1)
        )

        if any(marker_map[number] for number in trailing_numbers):
            raise RuntimeError(
                f"Non-empty verse after empty marker in "
                f"{code} {chapter_number}"
            )

        chapter_arrays.append([
            marker_map[number]
            for number in range(1, last_real_verse + 1)
        ])

    output_books.append({
        "abbrev": kjv_books[book_number - 1]["abbrev"],
        "chapters": chapter_arrays,
        "name": spanish_names[code],
    })

actual_empty = {
    (
        entry["book_number"],
        entry["book_code"],
        entry["chapter"],
        entry["verse"],
    )
    for entry in empty_markers
}

if actual_empty != expected_empty:
    raise RuntimeError(
        "Actual empty markers do not match the audited set"
    )

marker_count = len(all_markers)

chapter_count = sum(
    len(book["chapters"])
    for book in output_books
)

verse_count = sum(
    len(chapter)
    for book in output_books
    for chapter in book["chapters"]
)

if marker_count != 31102:
    raise RuntimeError(
        f"Expected 31,102 markers; found {marker_count}"
    )

if len(empty_markers) != 18:
    raise RuntimeError(
        f"Expected 18 empty placeholders; found {len(empty_markers)}"
    )

if chapter_count != 1189:
    raise RuntimeError(
        f"Expected 1,189 chapters; found {chapter_count}"
    )

if verse_count != 31084:
    raise RuntimeError(
        f"Expected 31,084 real verses; found {verse_count}"
    )

if output_books[0]["name"] != "Génesis":
    raise RuntimeError("First book is not Génesis")

if output_books[-1]["name"] != "Apocalipsis":
    raise RuntimeError("Last book is not Apocalipsis")

if (
    output_books[0]["chapters"][0][0]
    != "EN el principio crió Dios los cielos y la tierra."
):
    raise RuntimeError("Genesis 1:1 does not match the source")

output_path.parent.mkdir(parents=True, exist_ok=True)

with output_path.open(
    "w",
    encoding="utf-8",
    newline="\n",
) as handle:
    json.dump(
        output_books,
        handle,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    handle.write("\n")

digest = hashlib.sha256(
    output_path.read_bytes()
).hexdigest()

print("PASS: RV1909 books: 66")
print("PASS: RV1909 chapters: 1189")
print("PASS: RV1909 USFX markers: 31102")
print("PASS: audited empty placeholders: 18")
print("PASS: real Spanish verse texts: 31084")
print("RV1909 SHA256:", digest)
