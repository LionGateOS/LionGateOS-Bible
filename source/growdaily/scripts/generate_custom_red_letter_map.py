#!/usr/bin/env python3
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STD_MAP = ROOT / "assets/red_letters/jesus_speech_map.json"
STD_BIBLE = ROOT / "assets/bible/en_kjv.json"
CUSTOM_BIBLE = ROOT / "assets/bible/kjv_modified.json"
OUTPUT = ROOT / "assets/red_letters/jesus_speech_map_custom.json"

def clean(value):
    if isinstance(value, dict):
        value = value.get("text", "")
    return re.sub(r"\s+", " ", str(value).replace("{", "").replace("}", "")).strip()

def index_bible(path):
    data = json.loads(path.read_text())
    result = {}
    for book in data:
        for chapter_number, chapter in enumerate(book["chapters"], 1):
            for verse_number, verse in enumerate(chapter, 1):
                result[f'{book["name"]}|{chapter_number}|{verse_number}'] = clean(verse)
    return result

def project_segments(segments, custom_text, key):
    standard_text = "".join(segment["text"] for segment in segments)
    standard_flags = []
    for segment in segments:
        standard_flags.extend([segment["red"]] * len(segment["text"]))

    if standard_text == custom_text:
        return segments

    custom_flags = [None] * len(custom_text)
    matcher = SequenceMatcher(None, standard_text, custom_text, autojunk=False)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            custom_flags[j1:j2] = standard_flags[i1:i2]
            continue

        if j1 == j2:
            continue

        candidates = set(standard_flags[i1:i2])
        if not candidates:
            if i1 > 0:
                candidates.add(standard_flags[i1 - 1])
            if i1 < len(standard_flags):
                candidates.add(standard_flags[i1])

        if len(candidates) != 1:
            raise RuntimeError(
                f"Ambiguous red/white boundary while projecting {key}: "
                f"{standard_text[i1:i2]!r} -> {custom_text[j1:j2]!r}"
            )

        custom_flags[j1:j2] = [next(iter(candidates))] * (j2 - j1)

    if any(flag is None for flag in custom_flags):
        raise RuntimeError(f"Unassigned characters while projecting {key}")

    projected = []
    start = 0
    for position in range(1, len(custom_text)):
        if custom_flags[position] != custom_flags[start]:
            projected.append({
                "text": custom_text[start:position],
                "red": custom_flags[start],
            })
            start = position

    projected.append({
        "text": custom_text[start:],
        "red": custom_flags[start],
    })

    return projected

speech_map = json.loads(STD_MAP.read_text())
standard = index_bible(STD_BIBLE)
custom = index_bible(CUSTOM_BIBLE)

result = {}
changed = []

for key, segments in speech_map.items():
    standard_text = "".join(segment["text"] for segment in segments)

    if standard.get(key) != standard_text:
        raise RuntimeError(f"Standard reconstruction mismatch: {key}")
    if key not in custom:
        raise RuntimeError(f"Custom verse missing: {key}")

    result[key] = project_segments(segments, custom[key], key)

    if custom[key] != standard_text:
        changed.append(key)

for key, segments in result.items():
    reconstructed = "".join(segment["text"] for segment in segments)
    if reconstructed != custom[key]:
        raise RuntimeError(f"Custom reconstruction mismatch: {key}")
    if not any(segment["red"] for segment in segments):
        raise RuntimeError(f"No purple segment remains: {key}")

temporary = OUTPUT.with_suffix(".json.tmp")
temporary.write_text(
    json.dumps(result, ensure_ascii=False, separators=(",", ":"))
)
temporary.replace(OUTPUT)

print("=== CUSTOM RED-LETTER MAP GENERATED ===")
print("Map entries:", len(result))
print("Exact unchanged entries:", len(result) - len(changed))
print("Projected custom entries:", len(changed))
print("Projection failures: 0")
print("Output:", OUTPUT.relative_to(ROOT))
print("\nProjected verses:")
for key in changed:
    print(" ", key)
print("\nNo existing files were overwritten except the generated custom map.")
