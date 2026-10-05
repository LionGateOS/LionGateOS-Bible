import json
import sqlite3
import shutil
from pathlib import Path

SOURCE = Path("source/growdaily/assets/bible/kjv_modified.json")
SPEECH_MAP = Path(
    "source/growdaily/assets/red_letters/jesus_speech_map_custom.json"
)
JESUS_COLOR_NAME = "Royal Purple"
JESUS_COLOR_HEX = "#9B00FF"
OUTPUT = Path("editions/esword/GD.bblx")
MOBILE_OUTPUT = Path("editions/esword/GD.bbli")
METADATA_OUTPUT = Path("editions/esword/liongateos-custom-kjv.metadata.json")

DIVISIONS = [
    {
        "id": "torah",
        "label": "Torah",
        "aliases": ["Law", "Books of Moses", "Pentateuch"],
        "book_numbers": list(range(1, 6)),
    },
    {
        "id": "history",
        "label": "History",
        "aliases": ["Historical Books"],
        "book_numbers": list(range(6, 18)),
    },
    {
        "id": "wisdom",
        "label": "Wisdom",
        "aliases": ["Poetry", "Wisdom and Poetry"],
        "book_numbers": list(range(18, 23)),
    },
    {
        "id": "major_prophets",
        "label": "Major Prophets",
        "aliases": ["Greater Prophets"],
        "book_numbers": list(range(23, 28)),
    },
    {
        "id": "minor_prophets",
        "label": "Minor Prophets",
        "aliases": ["The Twelve"],
        "book_numbers": list(range(28, 40)),
    },
    {
        "id": "gospels_acts",
        "label": "Gospels and Acts",
        "aliases": ["Gospels", "Gospels + Acts"],
        "book_numbers": list(range(40, 45)),
    },
    {
        "id": "letters_revelation",
        "label": "Letters and Revelation",
        "aliases": ["Epistles and Revelation", "Letters", "Epistles"],
        "book_numbers": list(range(45, 67)),
    },
]

bible = json.loads(SOURCE.read_text(encoding="utf-8"))
speech_map = json.loads(SPEECH_MAP.read_text(encoding="utf-8"))

if not isinstance(speech_map, dict):
    raise SystemExit("ERROR: Jesus-speech map must be an object")

if len(speech_map) != 2055:
    raise SystemExit(
        f"ERROR: expected 2,055 Jesus-speech verses, found {len(speech_map)}"
    )

if len(bible) != 66:
    raise SystemExit(f"ERROR: expected 66 books, found {len(bible)}")

rows = []
book_metadata = []
used_speech_refs = set()
purple_segment_count = 0

for book_number, book in enumerate(bible, start=1):
    book_metadata.append(
        {
            "book_number": book_number,
            "name": book["name"],
            "abbrev": book.get("abbrev"),
        }
    )
    for chapter_number, chapter in enumerate(book["chapters"], start=1):
        for verse_number, scripture in enumerate(chapter, start=1):
            if not isinstance(scripture, str) or not scripture.strip():
                raise SystemExit(
                    f"ERROR: invalid scripture at "
                    f"{book['name']} {chapter_number}:{verse_number}"
                )
            ref = f"{book['name']}|{chapter_number}|{verse_number}"
            rendered_scripture = scripture

            if ref in speech_map:
                segments = speech_map[ref]

                if not isinstance(segments, list) or not segments:
                    raise SystemExit(
                        f"ERROR: invalid Jesus-speech segments at {ref}"
                    )

                reconstructed = ""
                rendered_parts = []
                has_purple = False

                for segment in segments:
                    if (
                        not isinstance(segment, dict)
                        or not isinstance(segment.get("text"), str)
                        or not isinstance(segment.get("red"), bool)
                    ):
                        raise SystemExit(
                            f"ERROR: malformed Jesus-speech segment at {ref}"
                        )

                    segment_text = segment["text"]
                    reconstructed += segment_text

                    if segment["red"]:
                        has_purple = True
                        purple_segment_count += 1
                        rendered_parts.append(
                            f'<span style="color:{JESUS_COLOR_HEX}">'
                            f"{segment_text}</span>"
                        )
                    else:
                        rendered_parts.append(segment_text)

                if reconstructed != scripture:
                    raise SystemExit(
                        f"ERROR: Jesus-speech map text mismatch at {ref}"
                    )

                if not has_purple and ref != "Matthew|23|7":
                    raise SystemExit(
                        f"ERROR: Jesus-speech entry has no speech span at {ref}"
                    )

                rendered_scripture = "".join(rendered_parts)
                used_speech_refs.add(ref)

            rows.append(
                (
                    book_number,
                    chapter_number,
                    verse_number,
                    rendered_scripture,
                )
            )

unused_speech_refs = set(speech_map) - used_speech_refs
if unused_speech_refs:
    preview = sorted(unused_speech_refs)[:10]
    raise SystemExit(
        f"ERROR: unused Jesus-speech refs: {preview}"
    )

if len(used_speech_refs) != 2055:
    raise SystemExit(
        f"ERROR: expected 2,055 rendered speech verses, "
        f"found {len(used_speech_refs)}"
    )

if len(rows) != 31102:
    raise SystemExit(f"ERROR: expected 31,102 verses, found {len(rows)}")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
if OUTPUT.exists():
    OUTPUT.unlink()

db = sqlite3.connect(OUTPUT)

db.executescript("""
CREATE TABLE Details (
    Title NVARCHAR(100),
    Abbreviation NVARCHAR(50),
    Information TEXT,
    Version INT,
    OldTestament BOOL,
    NewTestament BOOL,
    Apocrypha BOOL,
    Strongs BOOL,
    RightToLeft BOOL
);

CREATE TABLE Bible (
    Book INT,
    Chapter INT,
    Verse INT,
    Scripture BLOB_TEXT
);

CREATE UNIQUE INDEX bible_reference
ON Bible(Book, Chapter, Verse);
""")

db.execute(
    "INSERT INTO Details VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
    (
        "Grow Daily - Custom King James Version",
        "GD",
        (
            "<p>GD stands for Grow Daily. A custom King James Version "
            "edition with the words of Jesus displayed in Royal Purple.</p>"
        ),
        4,
        1,
        1,
        0,
        0,
        0,
    ),
)

db.executemany(
    "INSERT INTO Bible(Book, Chapter, Verse, Scripture) "
    "VALUES (?, ?, ?, ?)",
    rows,
)

db.commit()

count = db.execute("SELECT COUNT(*) FROM Bible").fetchone()[0]
sample = db.execute(
    "SELECT Book, Chapter, Verse, typeof(Scripture), Scripture "
    "FROM Bible WHERE Book=43 AND Chapter=3 AND Verse=16"
).fetchone()
integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
details = db.execute("SELECT * FROM Details").fetchone()

db.close()

# e-Sword HD mobile Bible modules use the same verified SQLite Bible schema.
# Generate the .bbli from the completed, integrity-checked desktop database so
# both deliverables contain exactly the same canonical Scripture content.
shutil.copyfile(OUTPUT, MOBILE_OUTPUT)

division_by_book = {}
for division in DIVISIONS:
    for book_number in division["book_numbers"]:
        division_by_book[book_number] = {
            "id": division["id"],
            "label": division["label"],
            "aliases": division["aliases"],
        }

metadata = {
    "title": "Grow Daily - Custom King James Version",
    "abbreviation": "GD",
    "words_of_jesus": {
        "enabled": True,
        "color_name": JESUS_COLOR_NAME,
        "color_hex": JESUS_COLOR_HEX,
        "speech_map": str(SPEECH_MAP),
        "mapped_verse_count": len(used_speech_refs),
        "speech_segment_count": purple_segment_count,
    },
    "canonical_structure": {
        "book_count": len(bible),
        "verse_count": len(rows),
        "coordinates_unchanged": True,
        "note": (
            "Seven divisions are presentation and search metadata only. "
            "Canonical 66-book verse coordinates remain unchanged."
        ),
    },
    "deliverables": {
        "desktop_esword_bblx": str(OUTPUT),
        "mobile_esword_bbli": str(MOBILE_OUTPUT),
        "ios_esword_status": "verified_ipad_esword_hd_import",
    },
    "presentation_metadata": {
        "division_count": len(DIVISIONS),
        "divisions": [
            {
                **division,
                "books": [
                    book_metadata[book_number - 1]["name"]
                    for book_number in division["book_numbers"]
                ],
            }
            for division in DIVISIONS
        ],
        "books": [
            {
                **book,
                "division": division_by_book[book["book_number"]],
            }
            for book in book_metadata
        ],
    },
}

METADATA_OUTPUT.write_text(
    json.dumps(metadata, indent=2, ensure_ascii=True) + "\n",
    encoding="utf-8",
)

print("Wrote:", OUTPUT)
print("Mobile:", MOBILE_OUTPUT)
print("Metadata:", METADATA_OUTPUT)
print("Rows:", count)
print("Details:", details)
print("Jesus-speech verses:", len(used_speech_refs))
print("Royal Purple speech segments:", purple_segment_count)
print("Royal Purple:", JESUS_COLOR_HEX)
print("John 3:16:", sample)
print("SQLite integrity:", integrity)
print("Size:", OUTPUT.stat().st_size, "bytes")
