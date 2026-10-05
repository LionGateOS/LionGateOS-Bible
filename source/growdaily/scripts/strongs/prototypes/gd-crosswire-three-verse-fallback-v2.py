import hashlib
import html
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path("/home/liongateos/LionGateOS-Bible")
OSIS = Path("/tmp/gd-crosswire-kjv-audit/kjv.osis.xml")
OUT = Path("/tmp/gd-crosswire-three-verse-fallback.json")

TARGETS = [
    ("Mark", 9, 43, "Mark.9.43"),
    ("Luke", 6, 41, "Luke.6.41"),
    ("Luke", 17, 36, "Luke.17.36"),
]

WORD_RE = re.compile(r'<w\b([^>]*)>(.*?)</w>', re.DOTALL)
STRONG_RE = re.compile(r'strong:([GH]\d+)', re.I)
TAG_RE = re.compile(r'<[^>]+>')

def plain(value):
    return html.unescape(TAG_RE.sub("", value))

def norm_piece(ch):
    if ch in ("æ", "Æ"):
        return "ae"
    if ch in ("œ", "Œ"):
        return "oe"
    if ch.isalnum():
        return ch.lower()
    return ""

def normalized_map(text):
    normalized = []
    boundaries = [0]
    norm_to_original = []
    for i, ch in enumerate(text):
        piece = norm_piece(ch)
        for out in piece:
            normalized.append(out)
            norm_to_original.append((i, i + 1))
        boundaries.append(len(normalized))
    return "".join(normalized), boundaries, norm_to_original

def parse_fragment(fragment):
    pieces = []
    spans = []
    cursor = 0
    out_len = 0
    for match in WORD_RE.finditer(fragment):
        before = plain(fragment[cursor:match.start()])
        pieces.append(before)
        out_len += len(before)
        surface = plain(match.group(2))
        start = out_len
        pieces.append(surface)
        out_len += len(surface)
        ids = [sid.upper() for sid in STRONG_RE.findall(match.group(1))]
        if ids:
            spans.append({
                "start": start,
                "end": out_len,
                "surface": surface,
                "strongs": ids,
            })
        cursor = match.end()
    pieces.append(plain(fragment[cursor:]))
    return "".join(pieces), spans

def map_spans(source_text, spans, canonical):
    source_norm, source_bounds, _ = normalized_map(source_text)
    canonical_norm, _, canonical_chars = normalized_map(canonical)
    matcher = SequenceMatcher(None, source_norm, canonical_norm, autojunk=False)
    char_map = {}
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            char_map[block.a + offset] = block.b + offset

    mapped = []
    for span in spans:
        left = source_bounds[span["start"]]
        right = source_bounds[span["end"]]
        positions = list(range(left, right))
        if not positions:
            raise RuntimeError(f"empty normalized span: {span!r}")
        missing = [p for p in positions if p not in char_map]
        if missing:
            raise RuntimeError(
                f"unmapped Strong's span: {span!r}; missing={len(missing)}"
            )
        targets = [char_map[p] for p in positions]
        expected = list(range(targets[0], targets[0] + len(targets)))
        if targets != expected:
            raise RuntimeError(f"non-contiguous Strong's span: {span!r}")
        start = canonical_chars[targets[0]][0]
        end = canonical_chars[targets[-1]][1]
        mapped.append({
            "start": start,
            "end": end,
            "sourceSurface": span["surface"],
            "canonicalSurface": canonical[start:end],
            "strongs": span["strongs"],
        })
    return mapped

def build_segments(canonical, mapped):
    segments = []
    cursor = 0
    for item in mapped:
        start = item["start"]
        end = item["end"]
        if start < cursor:
            raise RuntimeError(f"overlapping mapping: {item!r}")
        if start > cursor:
            segments.append([canonical[cursor:start], None])
        segments.append([canonical[start:end], item["strongs"][0]])
        for sid in item["strongs"][1:]:
            segments.append(["", sid])
        cursor = end
    if cursor < len(canonical):
        segments.append([canonical[cursor:], None])
    rebuilt = "".join(segment[0] for segment in segments)
    if rebuilt != canonical:
        raise RuntimeError("canonical reconstruction failure")
    return segments

manifest = json.loads(
    (ROOT / "source/growdaily/docs/bible/EBIBLE_KJV_STRONGS_SOURCE_MANIFEST.json")
    .read_text(encoding="utf-8")
)
canonical_data = json.loads(
    (ROOT / "source/growdaily/assets/bible/en_kjv.json").read_text(encoding="utf-8")
)
book_index = {item["book"]: i for i, item in enumerate(manifest["files"])}
osis = OSIS.read_text(encoding="utf-8")

payload = {
    "source": {
        "provider": "CrossWire Bible Society",
        "repository": "https://gitlab.com/crosswire-bible-society/kjv",
        "commit": "d490be7e34762deb2c76cb2c1306d4808e27890d",
        "osisSha256": hashlib.sha256(OSIS.read_bytes()).hexdigest(),
        "distributionLicense": "GPL",
        "scope": "Residual fallback source for exactly three eBible KJV verses with no Strong's markup",
    },
    "verses": {},
}

total_markers = 0

for book, chapter, verse, osis_ref in TARGETS:
    start_marker = f'<verse osisID="{osis_ref}" sID="{osis_ref}"/>'
    end_marker = f'<verse eID="{osis_ref}"/>'
    start = osis.find(start_marker)
    if start < 0:
        raise RuntimeError(f"missing start marker: {osis_ref}")
    start += len(start_marker)
    end = osis.find(end_marker, start)
    if end < 0:
        raise RuntimeError(f"missing end marker: {osis_ref}")

    source_text, source_spans = parse_fragment(osis[start:end])
    canonical = canonical_data[book_index[book]]["chapters"][chapter - 1][verse - 1]
    mapped = map_spans(source_text, source_spans, canonical)
    segments = build_segments(canonical, mapped)
    ids = [sid for _, sid in segments if sid]
    total_markers += len(ids)

    key = f"{book}|{chapter}|{verse}"
    payload["verses"][key] = {
        "sourceText": source_text,
        "canonicalText": canonical,
        "sourceStrongMarkerCount": sum(len(x["strongs"]) for x in source_spans),
        "mappedStrongMarkerCount": len(ids),
        "segments": segments,
    }

    print(f"REFERENCE={key}")
    print(f"SOURCE_STRONG_MARKERS={sum(len(x['strongs']) for x in source_spans)}")
    print(f"MAPPED_STRONG_MARKERS={len(ids)}")
    print(f"RECONSTRUCTION_MATCH={''.join(x[0] for x in segments) == canonical}")
    print(f"STRONG_IDS={','.join(ids)}")
    if key == "Luke|17|36":
        note = " this verse is not found in most of the Greek copies"
        print(f"EDITORIAL_NOTE_UNTAGGED={segments[-1] == [note, None]}")
    print()

OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(f"FALLBACK_VERSES={len(payload['verses'])}")
print(f"TOTAL_CROSSWIRE_MARKERS={total_markers}")
print(f"OUTPUT={OUT}")
print(f"OUTPUT_SHA256={hashlib.sha256(OUT.read_bytes()).hexdigest()}")
print("CROSSWIRE_FALLBACK_PROTOTYPE=PASS")
