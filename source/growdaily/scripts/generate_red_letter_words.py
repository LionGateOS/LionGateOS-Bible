#!/usr/bin/env python3
"""
Populate jesus_speech_map.json with correct per-segment red-letter data.

Output format:
{
  "Book|Chapter|Verse": [
    { "text": "And he saith unto them, ", "red": false },
    { "text": "Follow me, and I will make you fishers of men.", "red": true }
  ]
}

Consecutive words with the same red flag are merged into single segments.
Only verses that contain at least one red segment are included.
Segments concatenate to reproduce the full verse text.
"""

import json
import re
import os
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)


# ── Load data sources ──────────────────────────────────────────────────────

def load_red_letter_set():
    """Extract red-letter verse set from the ORIGINAL committed redLetters.js
    (the version with the hardcoded RED_LETTERS object)."""
    # Get the original version from git
    result = subprocess.run(
        ["git", "show", "66a59a98:logic/redLetters.js"],
        capture_output=True, text=True, cwd=ROOT,
    )
    if result.returncode != 0:
        raise RuntimeError("Could not retrieve original redLetters.js from git")
    content = result.stdout
    refs = set(re.findall(r'"(.*?)":\s*true', content))
    if not refs:
        raise RuntimeError("No red-letter refs found in original redLetters.js")
    return refs


def load_kjv():
    path = os.path.join(ROOT, "assets", "bible", "en_kjv.json")
    with open(path) as f:
        return json.load(f)


# ── Speech boundary detection ─────────────────────────────────────────────

SPEECH_VERBS = {
    "said", "saith", "saying", "spake", "answered", "cried",
    "commanded", "charged", "called", "speaketh", "calleth",
    "crieth", "asketh", "exclaimed", "replied", "testified",
    "declared", "pronounced", "warned", "counselled", "promised",
    "prayed",
}


def find_last_speech_boundary(words):
    """
    Find the word index where speech starts (after narrative intro).
    Strategy: find the LAST speech-verb + comma pattern.
    Returns the start word index, or None if no intro found.

    Skips speech verbs preceded by first-person pronouns ("I", "we")
    because those indicate the verb is WITHIN dialogue (e.g. "I said
    unto thee,"), not a narrative introduction (e.g. "Jesus said unto
    them,").
    """
    last_boundary = None

    FIRST_PERSON = {"i", "we"}

    for i, word in enumerate(words):
        clean = word.rstrip(".,;:!?'\"").lower()
        if clean not in SPEECH_VERBS:
            continue

        # Skip speech verbs preceded by first-person pronouns —
        # these are within dialogue, not narrative intros.
        if i > 0:
            prev_clean = words[i - 1].rstrip(".,;:!?'\"").lower()
            if prev_clean in FIRST_PERSON:
                continue

        # Verb itself ends with comma: "saying," "said,"
        if word.endswith(","):
            last_boundary = i + 1
            continue

        # Verb followed by preposition/object + comma within 5 words
        for j in range(i + 1, min(i + 6, len(words))):
            if words[j].endswith(","):
                last_boundary = j + 1
                break
            if words[j][-1] in ".;:!?":
                break

    return last_boundary


def find_post_speech_boundary(words, speech_start):
    """
    Detect where narration resumes after speech.
    Returns the word index where narration resumes, or None.
    """
    NARRATIVE_STARTERS = {
        "and", "then", "but", "so", "for", "when", "while",
        "after", "before", "now",
    }
    NARRATIVE_SUBJECTS = {
        "he", "she", "they", "his", "her", "the", "jesus",
        "peter", "john", "james", "judas", "pilate", "moses",
        "all", "many", "some", "one", "those", "these",
    }

    for i in range(speech_start, len(words) - 1):
        if not words[i].endswith("."):
            continue
        nxt = words[i + 1].rstrip(".,;:!?'\"").lower()
        if nxt in NARRATIVE_STARTERS and i + 2 < len(words):
            subj = words[i + 2].rstrip(".,;:!?'\"").lower()
            if subj in NARRATIVE_SUBJECTS:
                return i + 1
        elif nxt in NARRATIVE_SUBJECTS:
            return i + 1

    return None


def get_red_flags(verse_text, is_red, prev_is_red):
    """
    Returns per-word boolean list (True = red), or None if not red-letter.
    """
    if not is_red:
        return None

    text = verse_text.replace("{", "").replace("}", "")
    words = text.split()
    if not words:
        return None

    n = len(words)
    boundary = find_last_speech_boundary(words)

    if boundary is not None and boundary < n:
        speech_start = boundary
    elif prev_is_red:
        speech_start = 0
    else:
        speech_start = 0

    post = find_post_speech_boundary(words, speech_start)
    speech_end = (post - 1) if post is not None else (n - 1)

    if speech_start >= n or speech_end < speech_start:
        speech_start, speech_end = 0, n - 1

    flags = [False] * n
    for i in range(speech_start, speech_end + 1):
        flags[i] = True

    return flags


# ── Segment creation ──────────────────────────────────────────────────────

def create_segments(verse_text, red_flags):
    """
    Merge consecutive same-flag words into text segments.
    Preserves original spacing. Segments concatenate to full verse text.
    """
    text = verse_text.replace("{", "").replace("}", "")
    words = text.split()
    n = len(words)

    if n == 0 or not red_flags or len(red_flags) != n:
        return [{"text": text, "red": False}]

    # Find each word's start position in the text
    boundaries = []
    pos = 0
    for word in words:
        start = text.index(word, pos)
        boundaries.append(start)
        pos = start + len(word)

    # Group consecutive same-flag words
    segments = []
    group_start = 0
    for i in range(1, n):
        if red_flags[i] != red_flags[group_start]:
            seg_text = text[boundaries[group_start]:boundaries[i]]
            segments.append({"text": seg_text, "red": red_flags[group_start]})
            group_start = i

    # Final segment
    segments.append({"text": text[boundaries[group_start]:], "red": red_flags[group_start]})

    return segments


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    red_set = load_red_letter_set()
    kjv = load_kjv()
    print(f"Loaded {len(red_set)} red-letter verse refs from git")

    gospel_names = {"Matthew", "Mark", "Luke", "John"}
    gospel_indices = {}
    for i, book in enumerate(kjv):
        name = book.get("name", book.get("abbrev", ""))
        if name in gospel_names:
            gospel_indices[name] = i

    result = {}
    stats = {"total": 0, "full_red": 0, "partial": 0}

    for book_name in sorted(gospel_indices):
        book_idx = gospel_indices[book_name]
        chapters = kjv[book_idx]["chapters"]

        for ch_idx, chapter in enumerate(chapters):
            ch_num = ch_idx + 1
            prev_is_red = False

            for v_idx, verse_raw in enumerate(chapter):
                v_num = v_idx + 1
                text = verse_raw.get("text", "") if isinstance(verse_raw, dict) else str(verse_raw)
                ref = f"{book_name} {ch_num}:{v_num}"
                is_red = ref in red_set

                if is_red:
                    flags = get_red_flags(text, is_red, prev_is_red)
                    if flags and any(flags):
                        segments = create_segments(text, flags)
                        key = f"{book_name}|{ch_num}|{v_num}"
                        result[key] = segments
                        stats["total"] += 1
                        if all(flags):
                            stats["full_red"] += 1
                        else:
                            stats["partial"] += 1

                prev_is_red = is_red

    # ── Merge curated non-Gospel overrides ────────────────────────────────
    overrides_path = os.path.join(ROOT, "assets", "red_letters",
                                  "curated_non_gospel_overrides.json")
    override_count = 0
    if os.path.exists(overrides_path):
        with open(overrides_path) as f:
            overrides = json.load(f)
        for key, segs in overrides.items():
            if key not in result:
                result[key] = segs
                override_count += 1
                stats["total"] += 1
                if len(segs) == 1 and segs[0]["red"]:
                    stats["full_red"] += 1
                else:
                    stats["partial"] += 1
        print(f"Merged {override_count} curated non-Gospel overrides")
    else:
        print(f"WARNING: curated overrides not found at {overrides_path}")

    out_path = os.path.join(ROOT, "assets", "red_letters", "jesus_speech_map.json")
    with open(out_path, "w") as f:
        json.dump(result, f, separators=(",", ":"), ensure_ascii=False)

    size_kb = os.path.getsize(out_path) / 1024
    print(f"\nWrote {out_path}")
    print(f"  Verses: {stats['total']} ({stats['full_red']} full red, {stats['partial']} partial)")
    print(f"  File size: {size_kb:.1f} KB")

    # ── Verify ──
    samples = {
        "Matthew|4|19": "intro trimmed",
        "Matthew|3|15": "intro + post-speech trimmed",
        "Matthew|5|3": "full verse red (continuation)",
        "Mark|1|41": "long intro trimmed",
        "Matthew|26|25": "multi-speaker, last speaker",
        "John|3|7": "continuation, full red (I-said fix)",
        "John|3|10": "intro trimmed",
        "John|3|16": "continuation, full red",
        "John|3|21": "continuation, full red",
        "Acts|9|5": "curated: two speakers, Jesus only",
        "Acts|20|35": "curated: Paul quoting Jesus",
        "Revelation|2|1": "curated: full red (letter dictation)",
        "Revelation|22|20": "curated: three-part split",
        "1 Corinthians|11|24": "curated: Last Supper quote",
        "2 Corinthians|12|9": "curated: three-part split",
    }
    print("\nSample output:")
    for key, note in samples.items():
        if key in result:
            segs = result[key]
            display = ""
            for s in segs:
                if s["red"]:
                    display += f'\033[95m{s["text"]}\033[0m'
                else:
                    display += s["text"]
            print(f"  {key} ({note}):")
            print(f"    {display}")
        else:
            print(f"  {key}: NOT IN MAP")


if __name__ == "__main__":
    main()
