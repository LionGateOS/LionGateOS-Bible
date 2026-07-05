import json
import sqlite3
from pathlib import Path

SOURCE = Path("source/growdaily/assets/bible/kjv_modified.json")
OUTPUT = Path("editions/esword/liongateos-custom-kjv.bblx")
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

if len(bible) != 66:
    raise SystemExit(f"ERROR: expected 66 books, found {len(bible)}")

rows = []
book_metadata = []
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
            rows.append(
                (book_number, chapter_number, verse_number, scripture)
            )

if len(rows) != 31100:
    raise SystemExit(f"ERROR: expected 31,100 verses, found {len(rows)}")

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
        "LionGateOS Custom King James Version",
        "LGOS-KJV",
        (
            "<p>Generated from the verified LionGateOS Custom "
            "King James Version source.</p>"
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

division_by_book = {}
for division in DIVISIONS:
    for book_number in division["book_numbers"]:
        division_by_book[book_number] = {
            "id": division["id"],
            "label": division["label"],
            "aliases": division["aliases"],
        }

metadata = {
    "title": "LionGateOS Custom King James Version",
    "abbreviation": "LGOS-KJV",
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
        "ios_esword_status": "blocked_pending_official_conversion_path",
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
print("Metadata:", METADATA_OUTPUT)
print("Rows:", count)
print("Details:", details)
print("John 3:16:", sample)
print("SQLite integrity:", integrity)
print("Size:", OUTPUT.stat().st_size, "bytes")
