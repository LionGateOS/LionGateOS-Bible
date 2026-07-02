import json
import sqlite3
from pathlib import Path
from datetime import date

source = Path("source/growdaily/assets/bible/kjv_modified.json")
output = Path("editions/esword/liongateos-custom-kjv.bblx")

bible = json.loads(source.read_text(encoding="utf-8"))
rows = []

for book in bible:
    for chapter_number, chapter in enumerate(book["chapters"], start=1):
        for verse_number, text in enumerate(chapter, start=1):
            rows.append({
                "book": book["name"],
                "chapter": chapter_number,
                "verse": verse_number,
                "text": text,
            })

books = {
    name: index + 1
    for index, name in enumerate(dict.fromkeys(row["book"] for row in rows))
}

if output.exists():
    output.unlink()

db = sqlite3.connect(output)

db.executescript("""
CREATE TABLE Details (
    Description TEXT,
    Abbreviation TEXT,
    Comments TEXT,
    Version TEXT,
    VersionDate TEXT,
    PublishDate TEXT,
    RightToLeft BOOL,
    OT BOOL,
    NT BOOL,
    Strong BOOL
);

CREATE TABLE Bible (
    Book INTEGER,
    Chapter INTEGER,
    Verse INTEGER,
    Scripture TEXT
);
""")

today = date.today().isoformat()

db.execute(
    "INSERT INTO Details VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
    (
        "LionGateOS Custom King James Version",
        "LGOS-KJV",
        "Generated from the verified LionGateOS Custom KJV source.",
        "0.1.0-test",
        today,
        today,
        0,
        1,
        1,
        0,
    ),
)

db.executemany(
    "INSERT INTO Bible VALUES (?, ?, ?, ?)",
    [
        (
            books[row["book"]],
            row["chapter"],
            row["verse"],
            row["text"],
        )
        for row in rows
    ],
)

db.execute(
    "CREATE UNIQUE INDEX bible_reference ON Bible(Book, Chapter, Verse)"
)

db.commit()

count = db.execute("SELECT COUNT(*) FROM Bible").fetchone()[0]
sample = db.execute(
    "SELECT Book, Chapter, Verse, Scripture "
    "FROM Bible WHERE Book=43 AND Chapter=3 AND Verse=16"
).fetchone()

integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
db.close()

print("Wrote:", output)
print("Rows:", count)
print("John 3:16:", sample)
print("SQLite integrity:", integrity)
print("Size:", output.stat().st_size, "bytes")
