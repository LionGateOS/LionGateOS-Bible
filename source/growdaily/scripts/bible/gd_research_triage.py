"""Research triage: ranked, topic-tagged signal detection.

Milestone 1.  Pure CPU -- this module never contacts a model.

Purpose
-------
The archive is ~194 MB / ~48.5 M tokens.  Sending all of it to a local
27B model is ~13 hours of prompt ingest alone, so the corpus has to be
ranked *before* any inference happens.  This module scans extracted text
once and scores every chunk against the research goals:

* ``translation``      -- Bible translation and wording
* ``capitalization``   -- capitalization of biblical terms
* ``interpretation``   -- scripture interpretation and corrections
* ``terminology``      -- preferred terminology
* ``speaker``          -- statements by Herbert W. Armstrong / Gerald Flurry

Every candidate record keeps the source path, chunk offsets and the
offsets of the matched text, so a reviewer can jump straight back to the
passage in the original document.

All patterns are compiled into a **single** alternation so each character
of the corpus is visited once, not once per pattern.  Matches are counted
with a per-pattern cap, which stops a document that repeats one word a
thousand times from dominating the ranking.
"""

from __future__ import annotations

import re

TRIAGE_VERSION = "1.0.0"

#: A single pattern can contribute at most this many hits to one chunk's
#: score.  Without the cap, a chunk that says "God" forty times would
#: outrank a chunk that actually discusses translation.
PER_PATTERN_CAP = 5

#: Snippets persisted per candidate chunk.  Bounds index size.
MAX_SNIPPETS_PER_CHUNK = 6

#: Characters of context stored either side of a match.
SNIPPET_RADIUS = 110

#: Safety valve: stop scanning a single document after this many matches.
MAX_MATCHES_PER_DOCUMENT = 60000

TOPICS = ("translation", "capitalization", "interpretation", "terminology", "speaker")

#: (name, topic, tier, weight, regex)
#:
#: Tier A -- explicit statements about translation, wording, capitalization
#:           or terminology.  These are the research goals stated directly.
#: Tier B -- capitalization of biblical/divine terms in practice.
#: Tier C -- scripture citation and interpretation.
#: Tier D -- speaker attribution.
PATTERNS = (
    # ---- Tier A: explicit research targets -------------------------------
    ("translation_discussion", "translation", "A", 10,
     r"\btranslat(?:e|es|ed|ing|ion|ions|or|ors)\b"),
    ("capitalization_discussion", "capitalization", "A", 10,
     r"\bcapitali[sz](?:e|es|ed|ing|ation|ations)\b"),
    ("terminology_discussion", "terminology", "A", 10,
     r"\bterminolog(?:y|ies|ical|ically)\b"),
    ("wording_discussion", "translation", "A", 10,
     r"\bwording\b"),
    ("named_translation", "translation", "A", 10,
     r"\b(?:King James|KJV|Revised Standard|RSV|Moffatt|Ferrar Fenton|"
     r"Emphatic Diaglott|American Standard|Revised Version|New International|"
     r"NIV|New English Bible|Jerusalem Bible|Living Bible|Goodspeed|Weymouth|"
     r"Rotherham|Lamsa|Phillips|New American Standard|NASB|New World Translation|"
     r"Companion Bible|Concordant Version)\b"),
    ("textual_criticism", "translation", "A", 9,
     r"\b(?:variant reading|textual variant|interpolat\w*|spurious|"
     r"manuscript evidence|marginal reading|italicized|italicised|"
     r"original Greek|original Hebrew)\b"),
    ("correction_language", "interpretation", "A", 9,
     r"\b(?:should read|should be translated|ought to be translated|"
     r"mistranslat\w*|mis-translat\w*|wrongly translated|incorrectly translated|"
     r"erroneous translation|correct translation|wrong translation)\b"),
    ("capitalization_instruction", "capitalization", "A", 9,
     r"\b(?:upper[-\s]?case|lower[-\s]?case|small caps|capital letter|"
     r"capitalized|capitalised)\b"),

    # ---- Tier B: capitalization of biblical terms in practice ------------
    ("divine_name_caps", "capitalization", "B", 6, r"\b(?:LORD|GOD)\b"),
    ("eternal_title", "capitalization", "B", 6, r"\bthe Eternal\b"),
    ("eternal_lower", "capitalization", "B", 6, r"\bthe eternal\b"),
    ("holy_day_terms", "capitalization", "B", 3,
     r"\b(?:Sabbath|Passover|Pentecost|Tabernacles|Atonement|"
     r"Unleavened Bread|Feast of Trumpets)\b"),
    ("spirit_terms", "capitalization", "B", 3, r"\b(?:Holy Spirit|Holy Ghost)\b"),
    # Church/Gospel/Word are extremely common in this corpus; at a low
    # weight they contribute to a score without promoting a chunk on
    # their own, which is what keeps the MEDIUM band meaningful.
    ("church_caps", "capitalization", "B", 1, r"\bChurch\b"),
    ("gospel_caps", "capitalization", "B", 1, r"\bGospel\b"),
    ("word_of_god_caps", "capitalization", "B", 3, r"\bWord of God\b"),

    # ---- Tier C: scripture citation and interpretation -------------------
    ("scripture_ref_full", "interpretation", "C", 5,
     r"\b(?:Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|"
     r"Samuel|Kings|Chronicles|Ezra|Nehemiah|Esther|Job|Psalms?|Proverbs|"
     r"Ecclesiastes|Isaiah|Jeremiah|Lamentations|Ezekiel|Daniel|Hosea|Joel|"
     r"Amos|Obadiah|Jonah|Micah|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|"
     r"Malachi|Matthew|Mark|Luke|John|Acts|Romans|Corinthians|Galatians|"
     r"Ephesians|Philippians|Colossians|Thessalonians|Timothy|Titus|Hebrews|"
     r"James|Peter|Jude|Revelation)\s+\d+:\d+"),
    ("scripture_ref_abbrev", "interpretation", "C", 4,
     r"\b(?:Gen|Ex|Lev|Num|Deut|Josh|Judg|Sam|Kgs|Chr|Neh|Esth|Ps|Prov|Eccl|"
     r"Isa|Jer|Lam|Ezek|Dan|Hos|Amos|Obad|Jonah|Mic|Nah|Hab|Zeph|Hag|Zech|"
     r"Mal|Matt|Mk|Lk|Jn|Rom|Cor|Gal|Eph|Phil|Col|Thess|Tim|Tit|Philem|Heb|"
     r"Jas|Pet|Rev)\.?\s+\d+:\d+"),
    ("interpretation_language", "interpretation", "C", 4,
     r"\b(?:interpretation|interpreted|the meaning of|prophesied|foreshadow\w*|"
     r"typolog\w*|symboliz\w*|symbolis\w*)\b"),
    ("correction_generic", "interpretation", "C", 2,
     r"\b(?:erroneous|inaccurate|corrupt\w*|altered the text|added to the text|"
     r"removed from the text|changed the text)\b"),

    # ---- Tier D: speaker attribution -------------------------------------
    ("hwa_name", "speaker", "D", 6,
     r"\b(?:Herbert W\.?\s+Armstrong|Herbert Armstrong|H\.\s?W\.\s?A\.|"
     r"Mr\.?\s+Armstrong)\b"),
    ("flurry_name", "speaker", "D", 6,
     r"\b(?:Gerald\s+(?:R\.?\s+)?Flurry|Mr\.?\s+Flurry)\b"),
    ("speaker_attribution", "speaker", "D", 5,
     r"\b(?:Armstrong|Flurry)\s+(?:wrote|said|stated|explained|taught|showed|"
     r"made clear|pointed out)\b"),
)

_PATTERN_BY_NAME = {name: (topic, tier, weight) for name, topic, tier, weight, _ in PATTERNS}

#: One combined alternation: every character of the corpus is scanned once.
COMBINED_RE = re.compile(
    "|".join("(?P<%s>%s)" % (name, regex) for name, _, _, _, regex in PATTERNS),
    re.IGNORECASE,
)

#: Terms whose **mixed** capitalization within one chunk is itself the
#: research signal.  "God" and "god" appearing together, or "the Eternal"
#: beside "the eternal", is exactly the phenomenon the capitalization goal
#: is looking for -- far more precise than counting either form alone.
MIXED_CASE_TERMS = (
    "God", "Church", "Gospel", "Spirit", "Bible",
    "Scripture", "Sabbath", "LORD", "Eternal",
)

_MIXED_CASE_PATTERNS = []
_MIXED_CASE_INDEX = {}
for _term in MIXED_CASE_TERMS:
    for _form, _regex in (("cap", r"\b%s\b" % _term), ("low", r"\b%s\b" % _term.lower())):
        _group = "%s__%s" % (_term.lower(), _form)
        _MIXED_CASE_PATTERNS.append("(?P<%s>%s)" % (_group, _regex))
        _MIXED_CASE_INDEX[_group] = (_term, _form)

MIXED_CASE_RE = re.compile("|".join(_MIXED_CASE_PATTERNS))  # case-SENSITIVE by design

MIXED_CASE_WEIGHT = 10
MIXED_CASE_SIGNAL = "mixed_capitalization"

#: Register the synthetic signal so scoring and reporting treat it like
#: any other Tier A pattern (it is one of the strongest signals we have).
_PATTERN_BY_NAME[MIXED_CASE_SIGNAL] = ("capitalization", "A", MIXED_CASE_WEIGHT)


def mixed_capitalization_terms(text):
    """Terms appearing in BOTH capitalized and lowercase form in *text*.

    ``["God", "Church"]`` means the passage contains both ``God`` and
    ``god``, or both ``Church`` and ``church`` -- a direct capitalization
    research signal rather than an incidental word count.
    """
    seen = {}
    for match in MIXED_CASE_RE.finditer(text):
        term, form = _MIXED_CASE_INDEX[match.lastgroup]
        seen.setdefault(term, set()).add(form)
    return sorted(term for term, forms in seen.items() if len(forms) == 2)

PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"
PRIORITY_ORDER = (PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW)


def scan_text(text, limit=MAX_MATCHES_PER_DOCUMENT):
    """Yield ``(name, topic, tier, weight, start, end)`` for every signal hit.

    Stops after *limit* matches and reports that it did so via the fourth
    return value of :func:`scan_document`.
    """
    count = 0
    for match in COMBINED_RE.finditer(text):
        name = match.lastgroup
        topic, tier, weight = _PATTERN_BY_NAME[name]
        yield name, topic, tier, weight, match.start(), match.end()
        count += 1
        if count >= limit:
            return


def scan_document(text):
    """Scan a whole document once.

    Returns ``(matches, truncated)`` where *matches* is a list of
    ``(name, topic, tier, weight, start, end)`` tuples.
    """
    matches = list(scan_text(text))
    truncated = len(matches) >= MAX_MATCHES_PER_DOCUMENT
    return matches, truncated


def snippet(text, start, end, radius=SNIPPET_RADIUS):
    """Exact source slice around a match, with its own offsets."""
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    return {
        "snippet": text[left:right],
        "snippet_char_start": left,
        "snippet_char_end": right,
    }


def scan_mixed_case(text, limit=MAX_MATCHES_PER_DOCUMENT):
    """Yield ``(term, form, start, end)`` for capitalized/lowercase forms."""
    count = 0
    for match in MIXED_CASE_RE.finditer(text):
        term, form = _MIXED_CASE_INDEX[match.lastgroup]
        yield term, form, match.start(), match.end()
        count += 1
        if count >= limit:
            return


def analyze_document(text, chunks):
    """Scan a document once and return ``(candidate_records, truncated)``.

    Scanning happens at document level and matches are bucketed into
    chunks by offset, so the text is traversed a fixed number of times
    no matter how many chunks it contains.
    """
    matches, truncated = scan_document(text)
    mixed = list(scan_mixed_case(text))
    return score_chunks(text, chunks, matches, mixed), truncated


def _locate_chunk(chunk_bounds, cursor, start):
    """Advance *cursor* to the chunk containing *start*.

    Matches arrive in ascending offset order, so a moving cursor locates
    the owning chunk in O(1) amortised rather than O(chunks) per match.
    Returns ``(index, cursor)`` with ``index == -1`` when *start* lies
    outside every window.
    """
    while cursor < len(chunk_bounds) and start >= chunk_bounds[cursor][1]:
        cursor += 1
    if cursor >= len(chunk_bounds):
        return -1, cursor
    chunk_start, chunk_end = chunk_bounds[cursor]
    if not (chunk_start <= start < chunk_end):
        return -1, cursor
    return cursor, cursor


def score_chunks(text, chunks, matches, mixed_matches=None):
    """Bucket signals into chunks and score each one.

    Returns one candidate record per chunk that contains at least one
    signal.  Chunks with no signal are omitted entirely -- that omission
    *is* the triage.
    """
    chunk_bounds = [(c["char_start"], c["char_end"]) for c in chunks]
    by_chunk = {}

    cursor = 0
    for name, topic, tier, weight, start, end in matches:
        index, cursor = _locate_chunk(chunk_bounds, cursor, start)
        if index < 0:
            if cursor >= len(chunk_bounds):
                break
            continue
        entry = by_chunk.setdefault(index, {"counts": {}, "snips": []})
        if entry["counts"].get(name, 0) < PER_PATTERN_CAP:
            entry["counts"][name] = entry["counts"].get(name, 0) + 1
        if len(entry["snips"]) < MAX_SNIPPETS_PER_CHUNK:
            info = snippet(text, start, end)
            info.update({
                "signal": name,
                "topic": topic,
                "match_char_start": start,
                "match_char_end": end,
                "matched_text": text[start:end],
            })
            entry["snips"].append(info)

    # Mixed capitalization is itself a Tier A signal: a chunk qualifies if
    # it uses both forms of a term, even with no hit from the fixed set.
    mixed_by_chunk = {}
    cursor = 0
    for term, form, start, end in (mixed_matches or ()):
        index, cursor = _locate_chunk(chunk_bounds, cursor, start)
        if index < 0:
            if cursor >= len(chunk_bounds):
                break
            continue
        mixed_by_chunk.setdefault(index, {}).setdefault(term, set()).add(form)
        if form == "low":
            entry = by_chunk.setdefault(index, {"counts": {}, "snips": []})
            if len(entry["snips"]) < MAX_SNIPPETS_PER_CHUNK:
                info = snippet(text, start, end)
                info.update({
                    "signal": MIXED_CASE_SIGNAL,
                    "topic": "capitalization",
                    "match_char_start": start,
                    "match_char_end": end,
                    "matched_text": text[start:end],
                    "term": term,
                })
                entry["snips"].append(info)

    for index, seen in mixed_by_chunk.items():
        terms = sorted(term for term, forms in seen.items() if len(forms) == 2)
        if not terms:
            continue
        entry = by_chunk.setdefault(index, {"counts": {}, "snips": []})
        entry["counts"][MIXED_CASE_SIGNAL] = min(len(terms), PER_PATTERN_CAP)
        entry["mixed_terms"] = terms

    records = []
    for index, chunk in enumerate(chunks):
        entry = by_chunk.get(index)
        if not entry or not entry["counts"]:
            continue  # this omission is the triage

        counts = entry["counts"]
        score = 0
        topics = set()
        tiers = set()
        signals = []
        for name, hits in sorted(counts.items()):
            topic, tier, weight = _PATTERN_BY_NAME[name]
            score += hits * weight
            topics.add(topic)
            tiers.add(tier)
            signals.append({"signal": name, "topic": topic, "tier": tier,
                            "hits": hits, "weight": weight})

        record = {
            "chunk_id": chunk["chunk_id"],
            "char_start": chunk["char_start"],
            "char_end": chunk["char_end"],
            "char_count": chunk["char_count"],
            "score": score,
            "priority": classify(score, tiers),
            "topics": sorted(topics),
            "tiers": sorted(tiers),
            "signals": signals,
            "matches": entry["snips"],
        }
        if entry.get("mixed_terms"):
            record["mixed_capitalization_terms"] = entry["mixed_terms"]
        records.append(record)
    return records


def classify(score, tiers):
    """Map a score and matched tiers onto a priority class.

    HIGH requires a Tier A match: an explicit statement about translation,
    wording, capitalization, terminology or a text correction.  MEDIUM is
    the practical tier -- divine-name and holy-day usage, or scripture
    interpretation with enough signal to be worth a model call.
    """
    if "A" in tiers:
        return PRIORITY_HIGH
    if score >= 6:
        return PRIORITY_MEDIUM
    return PRIORITY_LOW
