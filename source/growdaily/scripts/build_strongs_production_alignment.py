#!/usr/bin/env python3
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROTOTYPE_DIR = ROOT / "source/growdaily/scripts/strongs/prototypes"

EBIBLE_PROTOTYPE = PROTOTYPE_DIR / "gd-ebible-alignment-compare-v2.py"
CROSSWIRE_PROTOTYPE = PROTOTYPE_DIR / "gd-crosswire-three-verse-fallback-v2.py"

EXPECTED_EBIBLE_PROTOTYPE_SHA = (
    "666d14d83dd05b2f0e453ae7549fc804136290cb8e4401fc9b7056872e9c85e6"
)
EXPECTED_CROSSWIRE_PROTOTYPE_SHA = (
    "4596148d1f56984fcf797b9a399d37c9fd09844a4f31b4398a212b9449293dba"
)
EXPECTED_EBIBLE_ARCHIVE_SHA = (
    "0e0359e9e488582a72c86800f227839ecb16dada7bb5ba316509d374c59e559a"
)
EXPECTED_CROSSWIRE_OSIS_SHA = (
    "4bcbfe45722fca396adbeac9c81025bbb173cb1e30296da90864f0400cb0e3f5"
)

EXPECTED_FALLBACK_REFS = {
    "Mark|9|43",
    "Luke|6|41",
    "Luke|17|36",
}
EXPECTED_CROSSWIRE_MARKERS = 66
EXPECTED_EBIBLE_MARKERS = 348884
EXPECTED_TOTAL_MARKERS = 348950
EXPECTED_VERSES = 31102

SOURCE_LABEL = (
    "eBible.org eng-kjv USFM; CrossWire KJV for "
    "Mark 9:43, Luke 6:41, Luke 17:36"
)


def sha256_path(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require_sha(path, expected, label):
    if not path.is_file():
        raise SystemExit(f"{label}_MISSING={path}")
    actual = sha256_path(path)
    print(f"{label}_SHA256={actual}")
    if actual != expected:
        raise SystemExit(f"{label}_CHECKSUM=FAIL")
    print(f"{label}_CHECKSUM=PASS")


def patched_copy(source, destination, replacements):
    text = source.read_text(encoding="utf-8")
    for old, new in replacements:
        count = text.count(old)
        if count != 1:
            raise RuntimeError(
                f"expected exactly one config anchor {old!r}, found {count}"
            )
        text = text.replace(old, new, 1)
    destination.write_text(text, encoding="utf-8")


def marker_count(verses):
    return sum(
        1
        for segments in verses.values()
        for segment in segments
        if segment[1] is not None
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Build the production Schema 2.0 KJV Strong's alignment from "
            "pinned eBible USFM plus exactly three pinned CrossWire fallback verses."
        )
    )
    parser.add_argument(
        "--ebible-dir",
        type=Path,
        default=Path("/tmp/gd-ebible-kjv-usfm"),
    )
    parser.add_argument(
        "--ebible-zip",
        type=Path,
        default=Path("/tmp/gd-ebible-kjv-usfm.zip"),
    )
    parser.add_argument(
        "--crosswire-osis",
        type=Path,
        default=Path("/tmp/gd-crosswire-kjv-audit/kjv.osis.xml"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/tmp/gd-strongs-production-rebuild"),
    )
    args = parser.parse_args()

    print("=== VERIFY FROZEN ALGORITHM PROTOTYPES ===")
    require_sha(
        EBIBLE_PROTOTYPE,
        EXPECTED_EBIBLE_PROTOTYPE_SHA,
        "EBIBLE_PROTOTYPE",
    )
    require_sha(
        CROSSWIRE_PROTOTYPE,
        EXPECTED_CROSSWIRE_PROTOTYPE_SHA,
        "CROSSWIRE_PROTOTYPE",
    )

    print()
    print("=== VERIFY PINNED SOURCE INPUTS ===")
    require_sha(
        args.ebible_zip,
        EXPECTED_EBIBLE_ARCHIVE_SHA,
        "EBIBLE_ARCHIVE",
    )
    require_sha(
        args.crosswire_osis,
        EXPECTED_CROSSWIRE_OSIS_SHA,
        "CROSSWIRE_OSIS",
    )
    if not args.ebible_dir.is_dir():
        raise SystemExit(f"EBIBLE_SOURCE_DIR_MISSING={args.ebible_dir}")

    with tempfile.TemporaryDirectory(prefix="gd-strongs-build-") as tmp:
        tmp = Path(tmp)
        ebible_out = tmp / "ebible"
        crosswire_out = tmp / "crosswire.json"
        ebible_runner = tmp / "ebible_runner.py"
        crosswire_runner = tmp / "crosswire_runner.py"

        root_literal = repr(str(ROOT))
        ebible_dir_literal = repr(str(args.ebible_dir.resolve()))
        ebible_zip_literal = repr(str(args.ebible_zip.resolve()))
        ebible_out_literal = repr(str(ebible_out))
        crosswire_osis_literal = repr(str(args.crosswire_osis.resolve()))
        crosswire_out_literal = repr(str(crosswire_out))

        patched_copy(
            EBIBLE_PROTOTYPE,
            ebible_runner,
            [
                (
                    'ROOT = Path("/home/liongateos/LionGateOS-Bible")',
                    f"ROOT = Path({root_literal})",
                ),
                (
                    'SRC = Path("/tmp/gd-ebible-kjv-usfm")',
                    f"SRC = Path({ebible_dir_literal})",
                ),
                (
                    'ZIP = Path("/tmp/gd-ebible-kjv-usfm.zip")',
                    f"ZIP = Path({ebible_zip_literal})",
                ),
                (
                    'OUT = Path("/tmp/gd-ebible-alignment-compare")',
                    f"OUT = Path({ebible_out_literal})",
                ),
            ],
        )

        patched_copy(
            CROSSWIRE_PROTOTYPE,
            crosswire_runner,
            [
                (
                    'ROOT = Path("/home/liongateos/LionGateOS-Bible")',
                    f"ROOT = Path({root_literal})",
                ),
                (
                    'OSIS = Path("/tmp/gd-crosswire-kjv-audit/kjv.osis.xml")',
                    f"OSIS = Path({crosswire_osis_literal})",
                ),
                (
                    'OUT = Path("/tmp/gd-crosswire-three-verse-fallback.json")',
                    f"OUT = Path({crosswire_out_literal})",
                ),
            ],
        )

        print()
        print("=== BUILD EBIBLE PRIMARY ALIGNMENT ===")
        subprocess.run([sys.executable, str(ebible_runner)], check=True)

        print()
        print("=== BUILD CROSSWIRE RESIDUAL FALLBACK ===")
        subprocess.run([sys.executable, str(crosswire_runner)], check=True)

        ebible_manifest = json.loads(
            (ebible_out / "manifest.json").read_text(encoding="utf-8")
        )
        crosswire = json.loads(
            crosswire_out.read_text(encoding="utf-8")
        )

        ebible_totals = ebible_manifest["totals"]
        if ebible_totals["canonicalVerses"] != EXPECTED_VERSES:
            raise SystemExit("EBIBLE_CANONICAL_COUNT=FAIL")
        if ebible_totals["alignedVerses"] != 31099:
            raise SystemExit("EBIBLE_ALIGNED_COUNT=FAIL")
        if ebible_totals["mappedStrongMarkers"] != EXPECTED_EBIBLE_MARKERS:
            raise SystemExit("EBIBLE_MARKER_COUNT=FAIL")

        fallback_refs = set(crosswire["verses"])
        if fallback_refs != EXPECTED_FALLBACK_REFS:
            raise SystemExit(
                f"CROSSWIRE_FALLBACK_REFS=FAIL:{sorted(fallback_refs)}"
            )

        fallback_markers = sum(
            1
            for item in crosswire["verses"].values()
            for segment in item["segments"]
            if segment[1] is not None
        )
        if fallback_markers != EXPECTED_CROSSWIRE_MARKERS:
            raise SystemExit(
                f"CROSSWIRE_MARKER_COUNT=FAIL:{fallback_markers}"
            )

        if args.output_dir.exists():
            shutil.rmtree(args.output_dir)
        args.output_dir.mkdir(parents=True)

        manifest_books = []
        total_markers = 0
        total_verses = 0

        for source_book in ebible_manifest["books"]:
            book_name = source_book["book"]
            filename = source_book["file"]
            payload = json.loads(
                (ebible_out / filename).read_text(encoding="utf-8")
            )
            verses = payload["verses"]

            for ref, fallback in crosswire["verses"].items():
                if ref.startswith(book_name + "|"):
                    if ref in verses:
                        raise SystemExit(
                            f"FALLBACK_COLLISION={ref}"
                        )
                    verses[ref] = fallback["segments"]

            expected_book_verses = source_book["canonicalVerses"]
            if len(verses) != expected_book_verses:
                raise SystemExit(
                    f"BOOK_VERSE_COUNT=FAIL:{book_name}:"
                    f"{len(verses)}!={expected_book_verses}"
                )

            production = {
                "schemaVersion": "2.0",
                "translationId": "kjv",
                "book": book_name,
                "verses": verses,
            }
            text = json.dumps(
                production,
                ensure_ascii=False,
                indent=2,
            ) + "\n"
            out_path = args.output_dir / filename
            out_path.write_text(text, encoding="utf-8")

            book_markers = marker_count(verses)
            total_markers += book_markers
            total_verses += len(verses)

            manifest_books.append({
                "book": book_name,
                "file": filename,
                "checksum": hashlib.sha256(
                    text.encode("utf-8")
                ).hexdigest(),
                "rawEntries": expected_book_verses,
                "uniqueSourceRefs": expected_book_verses,
                "malformedRefs": 0,
                "canonicalVerses": expected_book_verses,
                "aligned": expected_book_verses,
                "fallback": 0,
                "missing": 0,
                "size": len(text.encode("utf-8")),
            })

        if total_verses != EXPECTED_VERSES:
            raise SystemExit(
                f"PRODUCTION_VERSE_COUNT=FAIL:{total_verses}"
            )
        if total_markers != EXPECTED_TOTAL_MARKERS:
            raise SystemExit(
                f"PRODUCTION_MARKER_COUNT=FAIL:{total_markers}"
            )

        manifest = {
            "schemaVersion": "2.0",
            "translationId": "kjv",
            "source": SOURCE_LABEL,
            "targetAsset": "assets/bible/en_kjv.json",
            "books": manifest_books,
            "totals": {
                "books": 66,
                "rawSourceEntries": EXPECTED_VERSES,
                "uniqueSourceRefs": EXPECTED_VERSES,
                "malformedRefs": 0,
                "canonicalVerses": EXPECTED_VERSES,
                "alignedVerses": EXPECTED_VERSES,
                "fallbackVerses": 0,
                "missingVerses": 0,
            },
        }
        (args.output_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    print()
    print("=== PRODUCTION STRONG'S BUILD RESULTS ===")
    print(f"OUTPUT={args.output_dir}")
    print(f"VERSES={total_verses}")
    print(f"EBIBLE_MARKERS={EXPECTED_EBIBLE_MARKERS}")
    print(f"CROSSWIRE_MARKERS={fallback_markers}")
    print(f"TOTAL_MARKERS={total_markers}")
    print("FALLBACK_VERSES=0")
    print("KAISERLIK_REQUIRED=NO")
    print("PRODUCTION_STRONGS_GENERATOR=PASS")


if __name__ == "__main__":
    main()
