import json
import sqlite3
from pathlib import Path

SOURCE = Path("source/growdaily/assets/bible/kjv_modified.json")
OUTPUT = Path("editions/esword/liongateos-custom-kjv.bblx")

bible = json.loads(SOURCE.read_text(encoding="utf-8"))

if len(bible) != 66:
    raise SystemExit(f"ERROR: expected 66 books, found {len(bible)}")

rows = []
for book_number, book in enumerate(bible, start=1):
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

print("Wrote:", OUTPUT)
print("Rows:", count)
print("Details:", details)
print("John 3:16:", sample)
print("SQLite integrity:", integrity)
print("Size:", OUTPUT.stat().st_size, "bytes")
