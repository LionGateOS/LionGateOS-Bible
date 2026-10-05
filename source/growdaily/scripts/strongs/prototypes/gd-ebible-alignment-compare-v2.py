import hashlib
import json
import re
import shutil
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path("/home/liongateos/LionGateOS-Bible")
SRC = Path("/tmp/gd-ebible-kjv-usfm")
ZIP = Path("/tmp/gd-ebible-kjv-usfm.zip")
OUT = Path("/tmp/gd-ebible-alignment-compare")

SOURCE_MANIFEST = ROOT / "source/growdaily/docs/bible/EBIBLE_KJV_STRONGS_SOURCE_MANIFEST.json"
CANONICAL_PATH = ROOT / "source/growdaily/assets/bible/en_kjv.json"
EXPECTED_ARCHIVE_SHA = "0e0359e9e488582a72c86800f227839ecb16dada7bb5ba316509d374c59e559a"

TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:[-'’][A-Za-z0-9]+)*")
WORD_RE = re.compile(r'\\\+?w\s+([^|\\]+?)\|([^\\]*?)\\\+?w\*')
NOTE_RE = re.compile(r'\\f\s.*?\\f\*', re.DOTALL)
XREF_RE = re.compile(r'\\x\s.*?\\x\*', re.DOTALL)
USFM_MARKER_RE = re.compile(r'\\[+A-Za-z0-9_-]+\*?')
ALIASES = {("abidah", "abida"), ("instructers", "instructors")}

def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def norm_token(value):
    return value.lower().replace("’", "'").replace("-", "").replace("'", "")

def equivalent(a, b):
    return a == b or (a, b) in ALIASES

def tokenize(text):
    return [{
        "text": m.group(0),
        "norm": norm_token(m.group(0)),
        "start": m.start(),
        "end": m.end(),
        "strong": None,
    } for m in TOKEN_RE.finditer(text)]

def clean_plain_usfm(value):
    return USFM_MARKER_RE.sub("", value).replace("~", " ")

def parse_usfm_visible(raw):
    raw = NOTE_RE.sub("", raw)
    raw = XREF_RE.sub("", raw)
    pieces = []
    strong_spans = []
    cursor = 0
    out_len = 0

    for m in WORD_RE.finditer(raw):
        before = clean_plain_usfm(raw[cursor:m.start()])
        pieces.append(before)
        out_len += len(before)

        word, attrs = m.group(1), m.group(2)
        start = out_len
        pieces.append(word)
        out_len += len(word)
        end = out_len

        sm = re.search(r'strong="([GH]\d+)"', attrs)
        if sm:
            strong_spans.append({
                "start": start,
                "end": end,
                "strong": sm.group(1),
                "surface": word,
            })

        cursor = m.end()

    pieces.append(clean_plain_usfm(raw[cursor:]))
    visible = "".join(pieces)

    return {
        "visible": visible,
        "strongSpans": strong_spans,
        "strongAttributes": len(strong_spans),
        "multiTokenWordMarkers": sum(
            1
            for span in strong_spans
            if len(re.findall(r"\S+", span["surface"])) > 1
        ),
    }


def parse_usfm_book(path):
    chapter = None
    verses = {}
    current_ref = None
    current_parts = []

    def flush():
        nonlocal current_ref, current_parts
        if current_ref is not None:
            if current_ref in verses:
                raise RuntimeError(f"duplicate verse {current_ref} in {path.name}")
            verses[current_ref] = " ".join(p for p in current_parts if p)
        current_ref = None
        current_parts = []

    for line in path.read_text(encoding="utf-8", errors="strict").splitlines():
        cm = re.match(r'^\\c\s+(\d+)', line)
        if cm:
            flush()
            chapter = int(cm.group(1))
            continue

        vm = re.match(r'^\\v\s+(\d+)\s*(.*)$', line)
        if vm:
            flush()
            if chapter is None:
                raise RuntimeError(f"verse before chapter in {path.name}")
            current_ref = (chapter, int(vm.group(1)))
            current_parts = [vm.group(2)]
            continue

        if current_ref is None:
            continue
        if not line.startswith("\\"):
            current_parts.append(line)
            continue
        if re.match(r'^\\(?:\+?w|add|nd|wj|qt|qs)\b', line):
            current_parts.append(line)

    flush()
    return verses

def flatten_canonical(data, books):
    if len(data) != 66 or len(books) != 66:
        raise RuntimeError("expected exactly 66 canonical books")
    result = {}
    for bi, book in enumerate(data):
        name = books[bi]["book"]
        for ci, chapter in enumerate(book.get("chapters", []), start=1):
            for vi, verse in enumerate(chapter, start=1):
                text = verse if isinstance(verse, str) else verse.get("text", "")
                result[(name, ci, vi)] = text.replace("{", "").replace("}", "")
    return result

def _norm_char(ch):
    replacements = {
        "æ": "ae",
        "Æ": "ae",
        "œ": "oe",
        "Œ": "oe",
    }
    if ch in replacements:
        return replacements[ch]
    if ch.isalnum():
        return ch.lower()
    return ""


def normalize_text_with_map(text):
    normalized = []
    boundaries = [0]
    norm_to_original = []

    for index, ch in enumerate(text):
        piece = _norm_char(ch)
        for out_ch in piece:
            normalized.append(out_ch)
            norm_to_original.append((index, index + 1))
        boundaries.append(len(normalized))

    return "".join(normalized), boundaries, norm_to_original


EXPLICIT_SPAN_EQUIVALENTS = {
    ("Abidah", "H0028"): "Abida",
    ("instructers", "G3807"): "instructors",
}


def map_strong_spans(source_visible, source_spans, canonical_text):
    source_norm, source_bounds, _ = normalize_text_with_map(source_visible)
    canonical_norm, _, canonical_chars = normalize_text_with_map(canonical_text)

    matcher = SequenceMatcher(
        None,
        source_norm,
        canonical_norm,
        autojunk=False,
    )

    char_map = {}
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            char_map[block.a + offset] = block.b + offset

    mapped = []
    unresolved = []

    for index, span in enumerate(source_spans):
        source_start = source_bounds[span["start"]]
        source_end = source_bounds[span["end"]]
        source_positions = list(range(source_start, source_end))

        if not source_positions:
            unresolved.append({
                "index": index,
                "strong": span["strong"],
                "surface": span["surface"],
                "reason": "no_normalized_characters",
            })
            continue

        missing = [
            position
            for position in source_positions
            if position not in char_map
        ]

        if missing:
            equivalent_surface = EXPLICIT_SPAN_EQUIVALENTS.get(
                (span["surface"], span["strong"])
            )

            if equivalent_surface is not None:
                equivalent_norm, _, _ = normalize_text_with_map(
                    equivalent_surface
                )

                starts = []
                search_from = 0

                while True:
                    found = canonical_norm.find(
                        equivalent_norm,
                        search_from,
                    )

                    if found < 0:
                        break

                    starts.append(found)
                    search_from = found + 1

                if len(starts) == 1:
                    target_start = starts[0]
                    target_end = (
                        target_start
                        + len(equivalent_norm)
                    )

                    canonical_start = canonical_chars[
                        target_start
                    ][0]

                    canonical_end = canonical_chars[
                        target_end - 1
                    ][1]

                    mapped.append({
                        "sourceIndex": index,
                        "start": canonical_start,
                        "end": canonical_end,
                        "strong": span["strong"],
                        "sourceSurface": span["surface"],
                        "explicitEquivalent": equivalent_surface,
                    })

                    continue

            unresolved.append({
                "index": index,
                "strong": span["strong"],
                "surface": span["surface"],
                "reason": "unmapped_source_characters",
                "missingNormalizedCharacters": len(missing),
            })
            continue

        target_positions = [
            char_map[position]
            for position in source_positions
        ]

        expected = list(
            range(
                target_positions[0],
                target_positions[0] + len(target_positions),
            )
        )

        if target_positions != expected:
            unresolved.append({
                "index": index,
                "strong": span["strong"],
                "surface": span["surface"],
                "reason": "non_contiguous_canonical_mapping",
            })
            continue

        canonical_start = canonical_chars[target_positions[0]][0]
        canonical_end = canonical_chars[target_positions[-1]][1]

        mapped.append({
            "sourceIndex": index,
            "start": canonical_start,
            "end": canonical_end,
            "strong": span["strong"],
            "sourceSurface": span["surface"],
        })

    previous_start = -1
    previous_end = -1

    for item in mapped:
        if item["start"] < previous_start:
            return None, unresolved, "non_monotonic_span_mapping"

        if item["start"] < previous_end and item["end"] != previous_end:
            return None, unresolved, "overlapping_span_mapping"

        previous_start = item["start"]
        previous_end = max(previous_end, item["end"])

    return mapped, unresolved, None


def build_segments(canonical_text, mapped_spans):
    segments = []
    cursor = 0

    for item in mapped_spans:
        start = item["start"]
        end = item["end"]
        sid = item["strong"]

        if start < cursor:
            if end == cursor:
                segments.append(["", sid])
                continue
            raise RuntimeError(
                "canonical Strong's span overlaps prior mapped span"
            )

        if end < start:
            raise RuntimeError("canonical Strong's span has negative length")

        segments.append([
            canonical_text[cursor:end],
            sid,
        ])
        cursor = end

    if cursor < len(canonical_text):
        segments.append([
            canonical_text[cursor:],
            None,
        ])

    if "".join(segment[0] for segment in segments) != canonical_text:
        raise RuntimeError("canonical reconstruction failure")

    return segments


source_manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
canonical_data = json.loads(CANONICAL_PATH.read_text(encoding="utf-8"))
books = source_manifest["files"]

print("=== VERIFY PINNED EBIBLE SOURCE ===")
archive_sha = sha256_file(ZIP)
print("ARCHIVE_SHA256=", archive_sha)
if archive_sha != EXPECTED_ARCHIVE_SHA:
    raise SystemExit("ARCHIVE_CHECKSUM=FAIL")
print("ARCHIVE_CHECKSUM=PASS")

for item in books:
    path = SRC / item["filename"]
    if not path.is_file():
        raise SystemExit(f"MISSING_SOURCE_FILE={path}")
    if sha256_file(path) != item["sha256"]:
        raise SystemExit("SOURCE_FILE_CHECKSUM_FAIL=" + item["filename"])

print("CANONICAL_SOURCE_FILE_CHECKSUMS=PASS")
print("SOURCE_FILES_VERIFIED=", len(books))

canonical = flatten_canonical(canonical_data, books)
if len(canonical) != 31102:
    raise SystemExit("CANONICAL_COUNT_FAIL=" + str(len(canonical)))
print("CANONICAL_VERSES=31102")

if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)

totals = {
    "books": 66,
    "canonicalVerses": 0,
    "sourceVerseCoordinates": 0,
    "sourceStrongAttributes": 0,
    "mappedStrongMarkers": 0,
    "alignedVerses": 0,
    "fallbackVerses": 0,
    "versesWithoutSourceStrongs": 0,
    "versesWithUnresolvedStrongs": 0,
    "unresolvedStrongMarkers": 0,
    "missingSourceVerses": 0,
    "extraSourceVerses": 0,
    "reconstructionFailures": 0,
    "multiTokenWordMarkers": 0,
}
diagnostics = {
    "missingSourceVerses": [],
    "extraSourceVerses": [],
    "noSourceStrongs": [],
    "unresolvedVerses": [],
}
manifest_books = []

for item in books:
    book_name = item["book"]
    path = SRC / item["filename"]
    parsed = parse_usfm_book(path)

    source_refs = {(book_name, ch, vs) for ch, vs in parsed}
    canonical_refs = {ref for ref in canonical if ref[0] == book_name}
    missing = sorted(canonical_refs - source_refs)
    extra = sorted(source_refs - canonical_refs)

    diagnostics["missingSourceVerses"].extend(f"{r[0]} {r[1]}:{r[2]}" for r in missing)
    diagnostics["extraSourceVerses"].extend(f"{r[0]} {r[1]}:{r[2]}" for r in extra)
    totals["missingSourceVerses"] += len(missing)
    totals["extraSourceVerses"] += len(extra)

    verses_out = {}
    book_stats = {
        "book": book_name,
        "file": book_name.lower().replace(" ", "_").replace(".", "") + ".json",
        "canonicalVerses": len(canonical_refs),
        "sourceVerseCoordinates": len(source_refs),
        "aligned": 0,
        "fallback": 0,
        "sourceStrongAttributes": 0,
        "mappedStrongMarkers": 0,
        "unresolvedStrongMarkers": 0,
    }

    for ref in sorted(canonical_refs, key=lambda x: (x[1], x[2])):
        totals["canonicalVerses"] += 1
        canonical_text = canonical[ref]
        raw = parsed.get((ref[1], ref[2]))

        if raw is None:
            book_stats["fallback"] += 1
            continue

        totals["sourceVerseCoordinates"] += 1
        try:
            source = parse_usfm_visible(raw)
        except Exception as exc:
            raise RuntimeError(
                f"{ref[0]} {ref[1]}:{ref[2]}: {exc}"
            ) from exc
        source_count = source["strongAttributes"]

        totals["sourceStrongAttributes"] += source_count
        totals["multiTokenWordMarkers"] += source["multiTokenWordMarkers"]
        book_stats["sourceStrongAttributes"] += source_count
        label = f"{ref[0]} {ref[1]}:{ref[2]}"

        if source_count == 0:
            totals["versesWithoutSourceStrongs"] += 1
            book_stats["fallback"] += 1
            diagnostics["noSourceStrongs"].append(label)
            continue

        strong_pairs, unresolved, error = map_strong_spans(
            source["visible"],
            source["strongSpans"],
            canonical_text,
        )

        if error or unresolved:
            totals["versesWithUnresolvedStrongs"] += 1
            totals["unresolvedStrongMarkers"] += len(unresolved)
            book_stats["fallback"] += 1
            book_stats["unresolvedStrongMarkers"] += len(unresolved)
            diagnostics["unresolvedVerses"].append({
                "reference": label,
                "error": error,
                "sourceText": source["visible"],
                "canonicalText": canonical_text,
                "unresolved": unresolved,
            })
            continue

        try:
            segments = build_segments(canonical_text, strong_pairs)
        except Exception as exc:
            totals["reconstructionFailures"] += 1
            book_stats["fallback"] += 1
            diagnostics["unresolvedVerses"].append({
                "reference": label,
                "error": "reconstruction: " + str(exc),
                "sourceText": source["visible"],
                "canonicalText": canonical_text,
            })
            continue

        if len(strong_pairs) != source_count:
            raise RuntimeError(
                f"{label}: mapped {len(strong_pairs)} != source {source_count}"
            )

        verse_key = f"{book_name}|{ref[1]}|{ref[2]}"
        verses_out[verse_key] = segments
        totals["alignedVerses"] += 1
        totals["mappedStrongMarkers"] += len(strong_pairs)
        book_stats["aligned"] += 1
        book_stats["mappedStrongMarkers"] += len(strong_pairs)

    book_stats["fallback"] = book_stats["canonicalVerses"] - book_stats["aligned"]

    payload = {
        "schemaVersion": "2.0-comparison",
        "translationId": "kjv",
        "source": "eBible.org eng-kjv USFM",
        "book": book_name,
        "verses": verses_out,
    }
    text = json.dumps(payload, indent=2) + "\n"
    out_path = OUT / book_stats["file"]
    out_path.write_text(text, encoding="utf-8")
    book_stats["checksum"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    book_stats["size"] = out_path.stat().st_size
    manifest_books.append(book_stats)

totals["fallbackVerses"] = totals["canonicalVerses"] - totals["alignedVerses"]

manifest = {
    "schemaVersion": "2.0-comparison",
    "translationId": "kjv",
    "source": {
        "provider": "eBible.org",
        "package": "eng-kjv USFM",
        "archiveSha256": EXPECTED_ARCHIVE_SHA,
        "sourceManifest": str(SOURCE_MANIFEST.relative_to(ROOT)),
    },
    "targetAsset": "source/growdaily/assets/bible/en_kjv.json",
    "outputPurpose": "comparison-only; not production",
    "books": manifest_books,
    "totals": totals,
}

(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
(OUT / "diagnostics.json").write_text(json.dumps(diagnostics, indent=2) + "\n", encoding="utf-8")

print()
print("=== EBIBLE ALIGNMENT COMPARISON RESULTS ===")
for key, value in totals.items():
    print(f"{key}={value}")

print()
print("NO_SOURCE_STRONGS=" + ",".join(diagnostics["noSourceStrongs"]))
print()
print("FIRST_UNRESOLVED_VERSES=")
for item in diagnostics["unresolvedVerses"][:30]:
    print(json.dumps(item, ensure_ascii=False))

print()
print("OUTPUT=", OUT)
print("MANIFEST=", OUT / "manifest.json")
print("DIAGNOSTICS=", OUT / "diagnostics.json")
print("REPO_FILES_WRITTEN=0")
print("EBIBLE_ALIGNMENT_COMPARISON=PASS")
