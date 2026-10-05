import json
import re
import shutil
import sqlite3
import subprocess
import tempfile
from pathlib import Path

SOURCE = Path(
    "source/growdaily/assets/bible/kjv_modified.json"
)
SPEECH_MAP = Path(
    "source/growdaily/assets/red_letters/"
    "jesus_speech_map_custom.json"
)
PROJECTION_BUILDER = Path(
    "scripts/build_gdplus_projection.js"
)

BASE_GD = Path("editions/esword/GD.bblx")
OUTPUT = Path("editions/esword/GD+.bblx")
MOBILE = Path("editions/esword/GD+.bbli")
METADATA = Path("editions/esword/GD+.metadata.json")

TITLE = (
    "Grow Daily - Custom King James Version "
    "with Strong's Numbers"
)
ABBREVIATION = "GD+"
PURPLE = "#00E5FF"
STRONGS_COLOR = None

EXPECTED_VERSES = 31102
EXPECTED_PROJECTED = 31102
EXPECTED_FALLBACK = 0
EXPECTED_CHANGED = 335
EXPECTED_CHANGED_PROJECTED = 335
EXPECTED_MARKERS = 348902
EXPECTED_SPEECH = 2055

if not BASE_GD.exists():
    raise SystemExit("ERROR: editions/esword/GD.bblx missing")

bible = json.loads(
    SOURCE.read_text(encoding="utf-8")
)
speech_map = json.loads(
    SPEECH_MAP.read_text(encoding="utf-8")
)

if len(bible) != 66:
    raise SystemExit("ERROR: Bible must contain 66 books")

if len(speech_map) != EXPECTED_SPEECH:
    raise SystemExit(
        f"ERROR: expected {EXPECTED_SPEECH} speech verses"
    )


def speech_intervals(ref, scripture):
    segments = speech_map.get(ref)

    if not segments:
        return []

    rebuilt = "".join(
        segment["text"]
        for segment in segments
    )

    if rebuilt != scripture:
        raise SystemExit(
            f"ERROR: speech map mismatch at {ref}"
        )

    intervals = []
    cursor = 0

    for segment in segments:
        end = cursor + len(segment["text"])

        if segment["red"]:
            intervals.append((cursor, end))

        cursor = end

    return intervals


def render_piece(text, start, intervals):
    if not text:
        return ""

    end = start + len(text)
    cuts = {start, end}

    for left, right in intervals:
        if start < left < end:
            cuts.add(left)
        if start < right < end:
            cuts.add(right)

    cuts = sorted(cuts)
    result = []

    for left, right in zip(cuts, cuts[1:]):
        piece = text[
            left - start:
            right - start
        ]

        purple = any(
            left >= speech_left
            and right <= speech_right
            for speech_left, speech_right
            in intervals
        )

        if purple:
            result.append(
                f'<span style="color:{PURPLE}">' 
                f"{piece}</span>"
            )
        else:
            result.append(piece)

    return "".join(result)


def render_verse(ref, scripture, segments):
    intervals = speech_intervals(
        ref,
        scripture,
    )

    if segments is None:
        return (
            render_piece(
                scripture,
                0,
                intervals,
            ),
            0,
        )

    rebuilt = "".join(
        segment[0]
        for segment in segments
    )

    if rebuilt != scripture:
        raise SystemExit(
            f"ERROR: Strong's projection mismatch at {ref}"
        )

    result = []
    cursor = 0
    marker_count = 0
    purple_open = False

    for surface, strongs_id in segments:
        start = cursor
        end = start + len(surface)

        cuts = {start, end}

        for left, right in intervals:
            if start < left < end:
                cuts.add(left)
            if start < right < end:
                cuts.add(right)

        cuts = sorted(cuts)

        for left, right in zip(
            cuts,
            cuts[1:],
        ):
            piece = scripture[left:right]

            is_purple = any(
                left >= speech_left
                and right <= speech_right
                for speech_left, speech_right
                in intervals
            )

            if is_purple and not purple_open:
                result.append(
                    f'<span style="color:{PURPLE}">' 
                )
                purple_open = True

            elif not is_purple and purple_open:
                result.append("</span>")
                purple_open = False

            result.append(piece)


        cursor = end

        if strongs_id:
            if not re.fullmatch(
                r"[HG]\d+",
                strongs_id,
            ):
                raise SystemExit(
                    f"ERROR: invalid Strong's ID at {ref}"
                )

            normalized_id = (
                strongs_id[0] +
                str(int(strongs_id[1:]))
            )

            if purple_open:
                result.append("</span>")
                purple_open = False
                reopen_purple = True
            else:
                reopen_purple = False

            result.append(
                f"<num>{normalized_id}</num>"
            )

            if reopen_purple:
                result.append(
                    f'<span style="color:{PURPLE}">'
                )
                purple_open = True
            marker_count += 1

    if purple_open:
        result.append("</span>")

    if cursor != len(scripture):
        raise SystemExit(
            f"ERROR: render length mismatch at {ref}"
        )

    return "".join(result), marker_count


with tempfile.TemporaryDirectory(
    prefix="gdplus-"
) as tmp:
    projection_path = (
        Path(tmp) / "projection.json"
    )

    subprocess.run(
        [
            "node",
            str(PROJECTION_BUILDER),
            str(projection_path),
        ],
        check=True,
    )

    projection = json.loads(
        projection_path.read_text(
            encoding="utf-8"
        )
    )

stats = projection["stats"]
projected = projection["verses"]

expected_stats = {
    "canonicalVerses": EXPECTED_VERSES,
    "projectedVerses": EXPECTED_PROJECTED,
    "plainFallbackVerses": EXPECTED_FALLBACK,
    "changedCustomVerses": EXPECTED_CHANGED,
    "changedProjectedVerses": EXPECTED_CHANGED_PROJECTED,
    "strongsMarkers": EXPECTED_MARKERS,
    "failures": 0,
}

if stats != expected_stats:
    raise SystemExit(
        f"ERROR: projection totals changed: {stats}"
    )

shutil.copyfile(BASE_GD, OUTPUT)

db = sqlite3.connect(OUTPUT)

db.execute(
    """
    UPDATE Details
    SET Title=?,
        Abbreviation=?,
        Information=?,
        Strongs=1
    """,
    (
        TITLE,
        ABBREVIATION,
        (
            "<p>A custom King James Version edition "
            "with the words of Jesus displayed in "
            "Aqua and Strong's numbers "
            "integrated for study.</p>"
        ),
    ),
)

verse_count = 0
projected_count = 0
fallback_count = 0
marker_count = 0
speech_count = 0

for book_no, book in enumerate(
    bible,
    start=1,
):
    for chapter_no, chapter in enumerate(
        book["chapters"],
        start=1,
    ):
        for verse_no, scripture in enumerate(
            chapter,
            start=1,
        ):
            verse_count += 1

            ref = (
                f"{book['name']}|"
                f"{chapter_no}|{verse_no}"
            )

            segments = projected.get(ref)

            if segments is None:
                fallback_count += 1
            else:
                projected_count += 1

            if ref in speech_map:
                speech_count += 1

            rendered, markers = render_verse(
                ref,
                scripture,
                segments,
            )

            marker_count += markers

            changed = db.execute(
                """
                UPDATE Bible
                SET Scripture=?
                WHERE Book=?
                  AND Chapter=?
                  AND Verse=?
                """,
                (
                    rendered,
                    book_no,
                    chapter_no,
                    verse_no,
                ),
            )

            if changed.rowcount != 1:
                raise SystemExit(
                    f"ERROR: missing row at {ref}"
                )

db.commit()

integrity = db.execute(
    "PRAGMA integrity_check"
).fetchone()[0]

details = db.execute(
    "SELECT * FROM Details"
).fetchone()

row_count = db.execute(
    "SELECT COUNT(*) FROM Bible"
).fetchone()[0]

john_1_39 = db.execute(
    """
    SELECT Scripture
    FROM Bible
    WHERE Book=43
      AND Chapter=1
      AND Verse=39
    """
).fetchone()[0]

db.close()

assert verse_count == EXPECTED_VERSES
assert row_count == EXPECTED_VERSES
assert projected_count == EXPECTED_PROJECTED
assert fallback_count == EXPECTED_FALLBACK
assert marker_count == EXPECTED_MARKERS
assert speech_count == EXPECTED_SPEECH
assert integrity == "ok"
assert details[0] == TITLE
assert details[1] == ABBREVIATION
assert details[7] == 1
assert PURPLE in john_1_39
assert "<num" in john_1_39 and "G" in john_1_39

shutil.copyfile(OUTPUT, MOBILE)

metadata = {
    "title": TITLE,
    "abbreviation": ABBREVIATION,
    "description": (
        "A custom King James Version edition with "
        "the words of Jesus displayed in Aqua "
        "and Strong's numbers integrated for study."
    ),
    "canonical_structure": {
        "book_count": 66,
        "verse_count": EXPECTED_VERSES,
        "coordinates_unchanged": True,
    },
    "words_of_jesus": {
        "enabled": True,
        "color_name": "Aqua",
        "color_hex": PURPLE,
        "mapped_verse_count": EXPECTED_SPEECH,
    },
    "strongs": {
        "enabled": True,
        "source_alignment_schema": "2.0",
        "projected_verse_count": EXPECTED_PROJECTED,
        "plain_fallback_verse_count": EXPECTED_FALLBACK,
        "strongs_marker_count": EXPECTED_MARKERS,
        "changed_custom_verse_count": EXPECTED_CHANGED,
        "changed_projected_verse_count":
            EXPECTED_CHANGED_PROJECTED,
    },
    "deliverables": {
        "desktop_esword_bblx": str(OUTPUT),
        "mobile_esword_bbli": str(MOBILE),
    },
}

METADATA.write_text(
    json.dumps(
        metadata,
        indent=2,
        ensure_ascii=True,
    ) + "\n",
    encoding="utf-8",
)

print("Wrote:", OUTPUT)
print("Mobile:", MOBILE)
print("Metadata:", METADATA)
print("Rows:", row_count)
print("Projected verses:", projected_count)
print("Plain fallbacks:", fallback_count)
print("Strong's markers:", marker_count)
print("Aqua speech verses:", speech_count)
print("SQLite integrity:", integrity)
print("GDPLUS_BUILD=PASS")
