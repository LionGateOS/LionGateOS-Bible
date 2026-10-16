"""gd_scripture_engine.py -- deterministic scripture reference extraction.

This module is GD Bible's DETERMINISTIC scripture-reference layer. It is a
different evidentiary class from model-attributed ``research_findings.
scripture_refs`` and must never be merged with it (GD Bible standing safeguard;
see ``docs/CHURCH_ARCHIVE_SEARCH_ROADMAP.md`` sec. 3.1 items 4-5 and DEF-06).

Granularity model (roadmap CASE-03 prerequisite)
------------------------------------------------
Every result carries ``granularity`` in ``{"book", "chapter", "verse", "range"}``:

    book      "the book of Revelation"    -> Revelation            (explicit framing)
    chapter   "Matthew 24"                -> Matthew 24
    verse     "Romans 8:18"               -> Romans 8:18
    range     "Romans 8:18-28"            -> Romans 8:18-28        (same chapter)
              "Romans 8:18-9:5"           -> Romans 8:18-9:5       (cross-chapter,
                                                                   never truncated)
              "Romans 8-10"               -> Romans 8-10           (chapter range)

Result schema
-------------
Legacy fields, unchanged for simple verse references:

    canonical, raw_match, book, chapter, verse, start_offset, end_offset

Additive fields (all optional to legacy consumers):

    granularity          book | chapter | verse | range
    book_id              1-based canonical (Protestant 66-book) ordinal, else None
    chapter_end          end chapter for a range, else None
    verse_start          int start verse, else None
    verse_end            int end verse for a range, else None
    verse_suffix         single-letter verse suffix ("a"/"b"/"c") on the start
    verse_end_suffix     single-letter verse suffix on the end verse
    reference_key        stable, display-independent identity string
    resolution_status    "syntactically_parsed" | "unresolved"
    canonical_status     "not_asserted" | "asserted_valid" | "asserted_invalid"
                         | "not_applicable"
    canonical_issues     list of canonical violation codes; empty when valid
    citation_context     "explicit" | "standalone" | "preceded_by_citation_cue"
                         | "followed_by_boundary" | "followed_by_connector"
                         | "unstructured"
    sequence_index       0-based position of this item inside its reference sequence
    sequence_raw         raw text of the whole reference sequence it belongs to
    sequence_start_offset / sequence_end_offset   offsets of that sequence
    engine_version       VERSION of the engine that produced the row

``book_id`` is the stable reference identity key (never a display string).
``reference_key`` examples: ``"b58:c8:v13"``, ``"b45:c8:v18-c9:v5"``,
``"b40:c24"``, ``"b66"``.

Parsing is NOT canonical assertion
----------------------------------
``resolution_status="syntactically_parsed"`` means only that a book name and a
numeric coordinate were recognised. It does NOT mean the coordinate exists in
the Bible. Canonical validity is a separate, explicit verdict carried by
``canonical_status``. Invalid coordinates are reported as ``asserted_invalid``
and are never clamped, repaired or silently dropped.

Canonical coordinates
---------------------
The 66-book KJV coordinate table is the pinned derived artifact
``gd_canonical_coordinates.json`` (1,189 chapters / 31,102 verses; counts only,
no scripture text). See ``COORDINATES_SOURCE`` for provenance and
``has_canonical_coordinates()`` for availability. If the table cannot be loaded
every row stays ``canonical_status="not_asserted"``: the engine never implies a
validity it cannot establish.

Single-chapter books (canonical citation convention)
----------------------------------------------------
For the books the pinned coordinate table proves contain exactly ONE chapter
(Obadiah, Philemon, 2 John, 3 John, Jude), a *bare* number is canonically a
VERSE, following ordinary citation practice::

    Jude 6        -> Jude 1:6        (verse granularity)
    Jude 3-4      -> Jude 1:3-4      (range granularity)
    III John 2    -> 3 John 1:2      (via an alias / Roman numeral)
    Obadiah 21    -> Obadiah 1:21
    Philemon 25   -> Philemon 1:25

Explicit ``chapter:verse`` syntax is untouched (``Jude 1:6`` stays ``Jude 1:6``),
multi-chapter books never use the shorthand, and the convention is active only
while the pinned table is loaded -- the single-chapter set is read from the
artifact, never hardcoded. Impossible verse numbers are not repaired: ``Jude 26``
becomes ``Jude 1:26`` and is then reported ``asserted_invalid`` against the same
table (Jude has 25 verses). ``raw_match`` and the offsets always describe the
original text, so a row may read ``canonical="Jude 1:6"`` with
``raw_match="Jude 6"``.

European comma notation
-----------------------
German/European material separates chapter from verse with a comma rather than
a colon, so a TIGHT ``chapter,verse`` is read as a single reference::

    Hab. 1,3-4      -> Habakkuk 1:3-4
    Phil. 2,5       -> Philippians 2:5
    Mal. 1,1-5      -> Malachi 1:1-5
    Daniel 11,40-41 -> Daniel 11:40-41
    Hab. 1,3-4; 3,2 -> Habakkuk 1:3-4 and Habakkuk 3:2

The discriminator is typographic and deterministic, never a language guess: the
comma must have NO whitespace on either side, and the form is read only where
the colon form is absent -- at the book anchor, or after a semicolon (which
starts a new reference). Therefore::

    Heb. 8:8, 13     -> Hebrews 8:8 + Hebrews 8:13      (English verse list)
    Hebrews 8, 13    -> Hebrews 8 + Hebrews 13          (spaced chapter list)
    Hab. 1, 3-4      -> not read as European (spaced: ambiguous)

Commas after a comma separator are never re-read this way, so English verse
lists keep their meaning. A thousands separator such as ``Mark 5,000`` is read as
the (rejected) coordinate ``Mark 5:0`` rather than a valid chapter, and is
reported ``asserted_invalid`` -- numbers are never silently repaired.

Citation structure (chapter-level precision)
--------------------------------------------
A bare chapter number is Scripture only when the surrounding text shows citation
structure. Cue words come in two strengths:

* **strong cues** are citation evidence on their own -- citation verbs/nouns
  (``see``, ``read``, ``notice``, ``compare``, ``chapter``, ``verse``,
  ``quoted``, ...) plus the locative ``in`` ("in Matthew 24").
* **generic words** are ordinary grammar (``to``, ``and``, ``of``, ``with``,
  ``for``, ``as``, ``now``, ``then``, ...). They are transparent, so a strong cue
  behind one still counts, and they count as list structure when they link onto a
  preceding reference ("Deuteronomy 28 and Leviticus 26") -- but they are NEVER
  sufficient by themselves.

When the only evidence is a generic word, the structure *after* the number
decides; if there is none, the match is held back as
``citation_context="unstructured"`` rather than guessed::

    I spoke to John 3 times yesterday.   -> held back (prose follows)
    Mary and Jude 6 students attended.   -> held back (prose follows)
    the prophecy of Revelation 12        -> Revelation 12 (strong cue behind "of")

A canonical coordinate being valid never establishes that prose was a citation,
and the single-chapter convention does not change that: ``Jude 6`` is a verse
only when the surrounding text is citation-like in the first place.

Options
-------
``extract_references(text, include_unresolved=False, include_bare_books=False,
                     canonical=True, include_unstructured_chapters=False)``

``canonical``
    Default True. Run deterministic assertion against the pinned coordinate
    table, filling ``canonical_status`` / ``canonical_issues``. When False every
    row keeps ``canonical_status="not_asserted"`` (pure syntactic parse layer).
``include_unstructured_chapters``
    Default False. A ``chapter``-level match is only treated as a citation when
    it has citation structure (below). Unstructured ones are held back from the
    default output but are never silently discarded: set this True to receive
    them explicitly labelled ``citation_context="unstructured"``.
``include_unresolved``
    When True, ``chapter:verse`` spans with no determinable book are reported as
    explicit unresolved rows (``resolution_status="unresolved"``, ``book=None``,
    ``canonical=None``) instead of being omitted. Default False (precision
    first): a standalone ``12:24`` is NOT guessed to be Scripture.
``include_bare_books``
    When True, bare canonical book mentions are reported as ``granularity="book"``.
    Default False: a bare prose "John"/"Mark"/"Acts" is not a citation by itself.
    Book-only references are still reported by default when explicitly framed
    ("the book of Revelation", "the epistle to the Romans").

Deterministic precision guards (frozen in ``tests/test_gd_scripture_engine.py``)
--------------------------------------------------------------------------------
* A book token must resolve to one of the 66 canonical books.
* ``chapter``-only and ``book``-only matches require a capitalized book token.
* A ``chapter``-level match (``chapter`` or chapter ``range``) additionally
  requires *citation structure*: it is the whole input, is introduced by a
  citation cue, or is closed by citation punctuation or a citation connector.
  This is a closed structural test, not a noun denylist. "Genesis 49 is a
  prophecy" and "Job 42 tasks" are syntactically identical, so the engine does
  not guess for either; unstructured chapter matches are excluded by default and
  remain recoverable via ``include_unstructured_chapters=True``.
* Inherited-book continuation happens only inside a single reference sequence
  (same clause, explicit citation separator) -- never across a sentence break.
"""

import json
import os
import re

# Engine version. Bumped when extraction behaviour or schema changes.
# 1.0.0 -> implicit, unversioned original engine (chapter:verse only, lossy).
# 1.1.0 -> DEF-06 repair: versioning, granularity model, chapter-only, verse
#          lists, inherited-book continuation, cross-chapter ranges, Psalm(s),
#          Roman-numeral book names.
# 1.2.0 -> DEF-06 blockers: deterministic canonical assertion against the pinned
#          66-book KJV coordinate table; parse/assert separation via
#          canonical_status; citation-structure rule replaces the chapter-only
#          noun denylist; global MAX_CHAPTER/MAX_VERSE ceilings removed.
# 1.3.0 -> canonical single-chapter-book citation convention: for a book the
#          pinned table proves has exactly one chapter, a bare number is a verse
#          ("Jude 6" -> "Jude 1:6"), still asserted against the same table.
# 1.4.0 -> European comma chapter/verse notation: a TIGHT "chapter,verse"
#          ("Hab. 1,3-4" -> Habakkuk 1:3-4), at the book anchor and after a
#          semicolon. Spaced English chapter lists and colon verse lists are
#          untouched.
# 1.5.0 -> citation-cue precision: generic grammatical words (to/and/of/with/
#          for/as/now/then/...) no longer promote a chapter match on their own.
#          Strong cues still do; a generic word needs following structure or
#          list structure, else the match is held back as unstructured.
VERSION = "1.5.0"

# Canonical 66 Books
CANON = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges", "Ruth",
    "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther",
    "Job", "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah", "Lamentations", "Ezekiel", "Daniel",
    "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi",
    "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians",
    "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude", "Revelation"
]

# Common variations and abbreviations mapped to Canonical Names.
# The v1.0.0 entries are preserved byte-for-byte; the v1.1.0 additions are
# grouped at the end of the literal.
ALIASES = {
    "gen": "Genesis", "ex": "Exodus", "exod": "Exodus", "lev": "Leviticus", "num": "Numbers", "deut": "Deuteronomy",
    "josh": "Joshua", "judg": "Judges", "sam": "1 Samuel", "1 sam": "1 Samuel", "i sam": "1 Samuel", "2 sam": "2 Samuel", "ii sam": "2 Samuel",
    "1 kgs": "1 Kings", "i kgs": "1 Kings", "2 kgs": "2 Kings", "ii kgs": "2 Kings",
    "1 chron": "1 Chronicles", "i chron": "1 Chronicles", "2 chron": "2 Chronicles", "ii chron": "2 Chronicles",
    "neh": "Nehemiah", "esth": "Esther", "job": "Job",
    "ps": "Psalms", "psa": "Psalms", "prov": "Proverbs", "eccl": "Ecclesiastes", "song": "Song of Solomon", "cant": "Song of Solomon",
    "isa": "Isaiah", "jer": "Jeremiah", "lam": "Lamentations", "ezek": "Ezekiel", "dan": "Daniel",
    "hos": "Hosea", "obad": "Obadiah", "jon": "Jonah", "mic": "Micah", "nah": "Nahum", "hab": "Habakkuk", "zeph": "Zephaniah", "hag": "Haggai", "zech": "Zechariah", "mal": "Malachi",
    "matt": "Matthew", "mt": "Matthew", "mrk": "Mark", "mk": "Mark", "lu": "Luke", "jn": "John", "acts": "Acts",
    "rom": "Romans",
    "1 cor": "1 Corinthians", "i cor": "1 Corinthians", "1 co": "1 Corinthians", "1cor": "1 Corinthians",
    "2 cor": "2 Corinthians", "ii cor": "2 Corinthians", "2 co": "2 Corinthians", "2cor": "2 Corinthians",
    "gal": "Galatians", "eph": "Ephesians", "phil": "Philippians", "col": "Colossians",
    "1 thess": "1 Thessalonians", "i thess": "1 Thessalonians", "2 thess": "2 Thessalonians", "ii thess": "2 Thessalonians",
    "1 tim": "1 Timothy", "i tim": "1 Timothy", "2 tim": "2 Timothy", "ii tim": "2 Timothy",
    "tit": "Titus", "philem": "Philemon", "heb": "Hebrews", "jas": "James",
    "1 pet": "1 Peter", "i pet": "1 Peter", "2 pet": "2 Peter", "ii pet": "2 Peter",
    "1 john": "1 John", "i john": "1 John", "2 john": "2 John", "ii john": "2 John", "3 john": "3 John", "iii john": "3 John",
    # Short epistle forms. "jn" alone means John, so the ordinal-prefixed forms
    # must exist too or "II Jn 7" silently resolves to John 7 (wrong book). The
    # numeric head expands to the roman/word heads in _ORDINAL_PATTERNS.
    "1 jn": "1 John", "2 jn": "2 John", "3 jn": "3 John",
    "rev": "Revelation", "apoc": "Revelation",

    # --- v1.1.0 additions (DEF-06) ---
    # Singular/plural Psalm family (normalization also folds "psalm" -> "psalms").
    "psalm": "Psalms", "psalms": "Psalms", "pss": "Psalms", "pslm": "Psalms",
    # Song of Solomon alternates.
    "song of solomon": "Song of Solomon", "song of songs": "Song of Solomon", "canticles": "Song of Solomon",
    # Ordinal word forms for numbered books.
    "first samuel": "1 Samuel", "second samuel": "2 Samuel",
    "first kings": "1 Kings", "second kings": "2 Kings",
    "first chronicles": "1 Chronicles", "second chronicles": "2 Chronicles",
    "first corinthians": "1 Corinthians", "second corinthians": "2 Corinthians",
    "first thessalonians": "1 Thessalonians", "second thessalonians": "2 Thessalonians",
    "first timothy": "1 Timothy", "second timothy": "2 Timothy",
    "first peter": "1 Peter", "second peter": "2 Peter",
    "first john": "1 John", "second john": "2 John", "third john": "3 John",
}

# --------------------------------------------------------------------------
# Book resolution
# --------------------------------------------------------------------------

# Ordinal head tokens folded to the Arabic prefix used by CANON.
_ORDINAL_HEADS = {
    "i": "1", "ii": "2", "iii": "3",
    "1st": "1", "2nd": "2", "3rd": "3",
    "first": "1", "second": "2", "third": "3",
}

# Regex alternation fragments for the Arabic head tokens.
_ORDINAL_PATTERNS = {
    "1": r"(?:1|i|1st|first)",
    "2": r"(?:2|ii|2nd|second)",
    "3": r"(?:3|iii|3rd|third)",
}


def _normalize_book_key(raw):
    """Fold a raw book token to the lookup key used by the book index."""
    text = raw.strip().lower().replace(".", " ")
    text = re.sub(r"[^a-z0-9&\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    tokens = text.split(" ")
    head = _ORDINAL_HEADS.get(tokens[0])
    if head is not None:
        tokens[0] = head
    key = " ".join(tokens)
    if key == "psalm":
        key = "psalms"
    return key


def _build_book_index():
    """Canonical names always win; aliases fill the remaining keys."""
    index = {}
    for book in CANON:
        index[_normalize_book_key(book)] = book
    for alias, book in ALIASES.items():
        index.setdefault(_normalize_book_key(alias), book)
    for book in CANON:  # re-assert canonical precedence
        index[_normalize_book_key(book)] = book
    return index


BOOK_INDEX = _build_book_index()


def _key_to_pattern(key):
    """Build a whitespace/period-tolerant regex fragment for a normalized key.

    Tokens are separated by ``[\\s.]+`` so "1 Cor." / "1 Cor" / "1. Cor" all
    resolve, and an Arabic ordinal head also matches its roman/word forms.
    """
    parts = []
    for position, token in enumerate(key.split(" ")):
        if position == 0 and token in _ORDINAL_PATTERNS:
            parts.append(_ORDINAL_PATTERNS[token])
        elif token == "psalms":
            parts.append(r"psalms?")  # singular "Psalm" resolves to canonical "Psalms"
        else:
            parts.append(re.escape(token))
    return r"[\s.]+".join(parts)


_BOOK_ALTERNATION = "|".join(
    sorted((_key_to_pattern(key) for key in BOOK_INDEX), key=len, reverse=True)
)

# Book token, longest alternative first. A trailing period is part of the token
# ("1 Cor. 11:1"); `(?![A-Za-z])` prevents matching inside a longer word.
BOOK_PATTERN = re.compile(
    r"\b(?P<book>" + _BOOK_ALTERNATION + r")\.?(?![A-Za-z])",
    re.IGNORECASE,
)

# Framing phrases that make a book-only reference explicit and unambiguous.
BOOK_FRAME_PATTERN = re.compile(
    r"\b(?:the\s+)?(?:book|epistle|letter)\s+(?:of|to)\s+"
    r"|\bgospel\s+according\s+to\s+",
    re.IGNORECASE,
)

# --------------------------------------------------------------------------
# Numeric tail grammar
# --------------------------------------------------------------------------

# chapter / verse number: 1-3 digits, optional single-letter suffix, never
# followed by another digit or letter ("2020" and "3rd" are not references).
_NUMBER_RE = re.compile(r"(\d{1,3})([a-cA-C])?(?![\dA-Za-z])")
_LEAD_RE = re.compile(r"\s*")
_COLON_RE = re.compile(r"\s*:\s*")
_STRICT_COLON_RE = re.compile(r":")
_RANGE_RE = re.compile(r"\s*[-\u2013]\s*")
_ITEM_SEP_RE = re.compile(
    r"\s*(?:(?P<comma>,)|(?P<semi>;)|(?P<and>&|\band\b))\s*", re.IGNORECASE
)
_NUMERIC_TAIL_RE = re.compile(r"\s*\.?\s*\d")

# --------------------------------------------------------------------------
# Citation structure (chapter-level precision)
# --------------------------------------------------------------------------
# A bare chapter number is only a citation when the surrounding text shows
# citation structure. This is a CLOSED structural test -- deliberately NOT a
# noun denylist. Corpus audit (1,000 documents, 2,266 chapter-level matches)
# found the accepted structures below cover the citation forms actually used
# ("in Romans 8" 743, sentence-initial followed by punctuation/end 1,220,
# "and verse 1" continuations 573, ...). Chapter numbers with no structure are
# held back rather than guessed, because "Genesis 49 is a prophecy" and
# "Job 42 tasks" are syntactically identical.

# Citation evidence in its own right: citation verbs/nouns, plus the locative
# preposition "in" that carries a reference ("in Matthew 24", "in Jude 6").
_STRONG_CITATION_CUES = frozenset({
    "in", "notice", "see", "read", "study", "compare", "cf", "consider", "turn",
    "look", "chapter", "chapters", "verse", "verses", "book", "epistle",
    "prophecy", "prophecies", "account", "recorded", "written", "found",
    "quoted", "cited",
})

# Generic grammatical words. They are TRANSPARENT -- the scan continues past
# them, so a strong cue behind one still counts ("verses of Matthew 24",
# "the account we read from Acts 15") -- but they are NEVER sufficient on their
# own. Ordinary prose puts these in front of a book name constantly
# ("I spoke to John 3 times", "Mary and Mark 5 students"), so when the only
# evidence is a generic word the FOLLOWING structure has to decide.
_GENERIC_PRECEDING_WORDS = frozenset({
    "of", "and", "or", "to", "at", "from", "with", "into", "about", "by", "on",
    "for", "as", "but", "also", "now", "then",
})

# Neutral words skipped when looking one step further back for a cue, so that
# "In the Genesis 19 account" still resolves to the cue "In".
_CUE_FILLERS = frozenset({
    "the", "a", "an", "this", "that", "these", "those", "his", "her", "its",
    "their", "our", "your", "whole", "entire", "same",
})

# Tokens that close a reference: a citation list continues.
_CITATION_CONNECTORS = frozenset({
    "and", "or", "verse", "verses", "ff", "cf", "see", "also",
})

# A generic cue sitting directly after a numeric reference is linking a new
# reference into a list ("Deuteronomy 28 and Leviticus 26", "Judges 4 and 5").
# That is structure, not prose.
_NUMBER_THEN_RE = re.compile(r"\d\s*$")

_CITATION_BOUNDARY_CHARS = ".,;:!?)]}\"'\u201d\u2019\u2026"
_CITATION_CONNECTOR_CHARS = ",;"

_PRECEDING_WORD_RE = re.compile(r"([A-Za-z][A-Za-z'\-]*)\s*$")
_WORD_RE = re.compile(r"([A-Za-z][A-Za-z'\-]*)")


def _following_structure(text, end):
    """Structure just after a match: "connector" / "boundary" / None.

    End of text counts as a boundary, matching a sentence-final reference.
    """
    tail = _LEAD_RE.match(text, end)
    if tail.end() >= len(text):
        return "boundary"
    char = text[tail.end()]
    if char in _CITATION_CONNECTOR_CHARS:
        return "connector"
    if char in _CITATION_BOUNDARY_CHARS:
        return "boundary"
    match = _WORD_RE.match(text, tail.end())
    if match and match.group(1).lower() in _CITATION_CONNECTORS:
        return "connector"
    return None


def _citation_context(text, start, end, raw_match):
    """Classify the citation structure around a chapter-level match.

    Returns one of the closed ``citation_context`` values. Only chapter-level
    granularity uses the structured/unstructured distinction; chapter:verse
    syntax is explicit on its own.

    Evidence, in order:

    1. the match is the whole text                 -> ``standalone``
    2. a STRONG citation cue precedes it          -> ``preceded_by_citation_cue``
    3. citation structure follows it              -> ``followed_by_connector`` /
                                                     ``followed_by_boundary``
    4. only a generic word precedes it            -> ``unstructured``

    A generic word ("to", "and", "of", ...) is never sufficient by itself:
    ordinary prose puts one in front of a book name constantly, and it must not
    override clear prose after the number. It is only transparent, so a strong
    cue behind it can still be found, and a generic word that links onto a
    preceding numeric reference counts as list structure. Otherwise the follow
    structure decides, and an ambiguous chapter-level form is held back rather
    than guessed -- which is what keeps "I spoke to John 3 times yesterday" and
    "Mary and Jude 6 students attended" out of the default results.
    """
    if text.strip() == raw_match.strip():
        return "standalone"

    follower = _following_structure(text, end)

    pos = start
    for _ in range(3):
        match = _PRECEDING_WORD_RE.search(text, 0, pos)
        if not match:
            break
        word = match.group(1).lower()
        if word in _STRONG_CITATION_CUES:
            return "preceded_by_citation_cue"
        if word in _GENERIC_PRECEDING_WORDS:
            if _NUMBER_THEN_RE.search(text, 0, match.start()):
                # Links onto a preceding reference: list structure.
                return "preceded_by_citation_cue"
            # Transparent but never sufficient: keep looking further back.
            pos = match.start()
            continue
        if word in _CUE_FILLERS:
            pos = match.start()
            continue
        break

    if follower == "connector":
        return "followed_by_connector"
    if follower == "boundary":
        return "followed_by_boundary"
    return "unstructured"


def _read_number(text, pos, lead=None):
    """Read a plausible number at ``pos``; returns dict or None."""
    if lead is not None:
        match = lead.match(text, pos)
        if not match:
            return None
        pos = match.end()
    match = _NUMBER_RE.match(text, pos)
    if not match:
        return None
    return {
        "value": int(match.group(1)),
        "suffix": match.group(2),
        "start": match.start(),
        "end": match.end(),
    }


def _read_comma_verse(text, pos):
    """Read a TIGHT European-style ",verse" following a chapter number.

    German/European material writes the chapter/verse separator as a comma:
    "Hab. 1,3-4" is Habakkuk 1:3-4. The discriminating signal is typographic and
    deterministic: the comma must have NO whitespace on either side, so

        "Hab. 1,3-4"      -> European  -> Habakkuk 1:3-4
        "Hebrews 8, 13"   -> English chapter list -> left to the sequence logic
        "Mark 5,000"      -> thousands separator; read as a (rejected) verse

    ``pos`` is the offset immediately after the chapter digits, so simply
    requiring ``text[pos] == ","`` enforces "no space before the comma", and
    demanding a digit at ``pos + 1`` enforces "no space after it".
    """
    if pos >= len(text) or text[pos] != ",":
        return None
    return _read_number(text, pos + 1)


def _first_letter_is_upper(text, start, end):
    for char in text[start:end]:
        if char.isalpha():
            return char.isupper()
    return False


def _overlaps(span, occupied):
    start, end = span
    for other_start, other_end in occupied:
        if start < other_end and other_start < end:
            return True
    return False


# --------------------------------------------------------------------------
# Reference sequence parsing
# --------------------------------------------------------------------------

def _parse_range_end(text, pos):
    """Parse the tail of a range.

    Returns ``(chapter_end, verse_end, end_suffix, end_offset)``.
    ``chapter_end`` is None for a same-chapter range; both are None when no
    range follows.

    A cross-chapter range is only recognised when the colon is immediately
    followed by digits (``8:18-9:5``). A colon that introduces a quotation or a
    following clause (``5:17-18: "Think not..."``) is not a separator, so the
    range end is kept instead of being discarded.
    """
    dash = _RANGE_RE.match(text, pos)
    if not dash:
        return None, None, None, pos
    end_chapter = _read_number(text, dash.end())
    if not end_chapter:
        return None, None, None, pos
    colon = _STRICT_COLON_RE.match(text, end_chapter["end"])
    if colon:
        end_verse = _read_number(text, colon.end())
        if end_verse:
            return (end_chapter["value"], end_verse["value"],
                    end_verse["suffix"], end_verse["end"])
    return None, end_chapter["value"], end_chapter["suffix"], end_chapter["end"]


def _parse_reference_sequence(text, book_start, book_end):
    """Parse one book token plus its numeric reference sequence.

    Returns ``(items, sequence_end)``. Each item is a dict with chapter/verse
    spans; nothing is emitted unless the anchor number is valid.
    """
    first = _read_number(text, book_end, _LEAD_RE)
    if not first or first["suffix"]:
        return [], book_end
    chapter = first["value"]

    chapter_end = None
    verse_start = verse_end = None
    verse_suffix = verse_end_suffix = None
    pos = first["end"]

    colon = _COLON_RE.match(text, pos)
    if colon:
        verse = _read_number(text, colon.end())
        if verse:
            verse_start = verse["value"]
            verse_suffix = verse["suffix"]
            pos = verse["end"]
            chapter_end, verse_end, verse_end_suffix, pos = _parse_range_end(text, pos)

    if not colon:
        # European comma notation: "Hab. 1,3-4" == Habakkuk 1:3-4. Only a tight
        # comma counts (see _read_comma_verse), and only when the explicit colon
        # form is absent, so "Heb. 8:8, 13" stays a verse list.
        comma_verse = _read_comma_verse(text, pos)
        if comma_verse:
            verse_start = comma_verse["value"]
            verse_suffix = comma_verse["suffix"]
            pos = comma_verse["end"]
            chapter_end, verse_end, verse_end_suffix, pos = _parse_range_end(text, pos)

    if verse_start is None and chapter_end is None:
        dash = _RANGE_RE.match(text, pos)
        if dash:
            end_chapter = _read_number(text, dash.end())
            if (end_chapter
                    and not _STRICT_COLON_RE.match(text, end_chapter["end"])):
                chapter_end = end_chapter["value"]
                pos = end_chapter["end"]
        # A bare chapter is the riskiest granularity: require a capitalized book
        # token. Whether it is a citation at all is decided afterwards by
        # _citation_context (citation structure) -- never by numeric ceilings.
        if not _first_letter_is_upper(text, book_start, book_end):
            return [], book_end

    items = [(chapter, chapter_end, verse_start, verse_end,
              verse_suffix, verse_end_suffix, book_start, pos)]
    last_chapter = chapter
    last_had_verse = verse_start is not None
    last_had_chapter_end = chapter_end is not None

    while True:
        separator = _ITEM_SEP_RE.match(text, pos)
        if not separator:
            break
        if separator.group("semi"):
            separator_kind = "semi"
        elif separator.group("and"):
            separator_kind = "and"
        else:
            separator_kind = "comma"
        cursor = separator.end()

        nxt = _read_number(text, cursor)
        if not nxt:
            break
        if BOOK_PATTERN.match(text, nxt["start"]):
            # The number is the ordinal prefix of another book, not a
            # continuation: "Matthew 8:14, Luke 4:38, 1 Corinthians 9:5".
            break

        after_next = _STRICT_COLON_RE.match(text, nxt["end"])
        if after_next:
            # New chapter (book inherited) with an explicit verse.
            verse = _read_number(text, after_next.end())
            if not verse:
                break
        elif separator_kind == "semi":
            # A semicolon starts a new reference, so European comma notation is
            # read here too ("Hab. 1,3-4; 3,2" -> Habakkuk 1:3-4 + 3:2). It is
            # deliberately NOT read after a comma separator, so an English verse
            # list keeps its meaning ("Heb. 8:8, 13, 15" -> 8:8 + 8:13 + 8:15).
            verse = _read_comma_verse(text, nxt["end"])
        else:
            verse = None

        if verse is not None:
            new_chapter = nxt["value"]
            end_chapter, end_verse, end_suffix, send = _parse_range_end(
                text, verse["end"])
            items.append((new_chapter, end_chapter, verse["value"], end_verse,
                          verse["suffix"], end_suffix, nxt["start"], send))
            last_chapter = new_chapter
            last_had_verse = True
            last_had_chapter_end = end_chapter is not None
            pos = send
            continue

        # Bare number continuation: a verse list after a verse, otherwise a
        # chapter list inside the inherited book.
        if separator_kind == "semi" or last_had_chapter_end:
            break
        value = nxt["value"]
        end_verse = end_suffix = None
        send = nxt["end"]
        dash = _RANGE_RE.match(text, send)
        if dash:
            range_end = _read_number(text, dash.end())
            if range_end and not _STRICT_COLON_RE.match(text, range_end["end"]):
                end_verse = range_end["value"]
                end_suffix = range_end["suffix"]
                send = range_end["end"]

        if last_had_verse:
            items.append((last_chapter, None, value, end_verse,
                          nxt["suffix"], end_suffix, nxt["start"], send))
            pos = send
            continue

        items.append((value, end_verse, None, None, None, None, nxt["start"], send))
        last_chapter = value
        last_had_verse = False
        pos = send

    return items, pos


# --------------------------------------------------------------------------
# Result materialization
# --------------------------------------------------------------------------

def _make_item(book, book_id, item, sequence, sequence_index):
    (chapter, chapter_end, verse_start, verse_end,
     verse_suffix, verse_end_suffix, start, end) = item

    if verse_start is None:
        verse_display = None
        if chapter_end is None:
            granularity = "chapter"
            canonical = f"{book} {chapter}"
            reference_key = f"b{book_id}:c{chapter}"
        else:
            granularity = "range"
            canonical = f"{book} {chapter}-{chapter_end}"
            reference_key = f"b{book_id}:c{chapter}-c{chapter_end}"
    else:
        verse_display = f"{verse_start}{verse_suffix or ''}"
        if verse_end is None:
            granularity = "verse"
            canonical = f"{book} {chapter}:{verse_display}"
            reference_key = f"b{book_id}:c{chapter}:v{verse_start}"
        else:
            granularity = "range"
            if chapter_end is None:
                verse_display = f"{verse_display}-{verse_end}{verse_end_suffix or ''}"
                reference_key = (f"b{book_id}:c{chapter}:v{verse_start}"
                                 f"-c{chapter}:v{verse_end}")
            else:
                verse_display = (f"{verse_display}-{chapter_end}:"
                                 f"{verse_end}{verse_end_suffix or ''}")
                reference_key = (f"b{book_id}:c{chapter}:v{verse_start}"
                                 f"-c{chapter_end}:v{verse_end}")
            canonical = f"{book} {chapter}:{verse_display}"

    return {
        # --- legacy fields (v1.0.0 contract, unchanged for simple verses) ---
        "canonical": canonical,
        "raw_match": None,  # filled by caller from the item/sequence span
        "book": book,
        "chapter": chapter,
        "verse": verse_display,
        "start_offset": start,
        "end_offset": end,
        # --- additive fields (v1.1.0) ---
        "granularity": granularity,
        "book_id": book_id,
        "chapter_end": chapter_end,
        "verse_start": verse_start,
        "verse_end": verse_end,
        "verse_suffix": verse_suffix,
        "verse_end_suffix": verse_end_suffix,
        "reference_key": reference_key,
        "resolution_status": "syntactically_parsed",
        "canonical_status": "not_asserted",
        "canonical_issues": [],
        "citation_context": None,  # filled in by extract_references
        "sequence_index": sequence_index,
        "sequence_raw": sequence,
        "sequence_start_offset": None,
        "sequence_end_offset": None,
        "engine_version": VERSION,
    }


def _make_book_only(text, canonical, book, book_id, start, end):
    return {
        "canonical": canonical,
        "raw_match": text[start:end],
        "book": book,
        "chapter": None,
        "verse": None,
        "start_offset": start,
        "end_offset": end,
        "granularity": "book",
        "book_id": book_id,
        "chapter_end": None,
        "verse_start": None,
        "verse_end": None,
        "verse_suffix": None,
        "verse_end_suffix": None,
        "reference_key": f"b{book_id}",
        "resolution_status": "syntactically_parsed",
        "canonical_status": "not_asserted",
        "canonical_issues": [],
        "citation_context": "explicit",  # explicit citation framing
        "sequence_index": 0,
        "sequence_raw": text[start:end],
        "sequence_start_offset": start,
        "sequence_end_offset": end,
        "engine_version": VERSION,
    }


def _make_unresolved(text, match):
    chapter = int(match.group(1))
    verse_start = int(match.group(2))
    chapter_end = int(match.group(3)) if match.group(3) else None
    verse_end = int(match.group(4)) if match.group(4) else None
    if verse_end is None:
        verse_display = str(verse_start)
        granularity = "verse"
    else:
        granularity = "range"
        if chapter_end is None:
            verse_display = f"{verse_start}-{verse_end}"
        else:
            verse_display = f"{verse_start}-{chapter_end}:{verse_end}"
    return {
        "canonical": None,
        "raw_match": text[match.start():match.end()],
        "book": None,
        "chapter": chapter,
        "verse": verse_display,
        "start_offset": match.start(),
        "end_offset": match.end(),
        "granularity": granularity,
        "book_id": None,
        "chapter_end": chapter_end,
        "verse_start": verse_start,
        "verse_end": verse_end,
        "verse_suffix": None,
        "verse_end_suffix": None,
        "reference_key": None,
        "resolution_status": "unresolved",
        "canonical_status": "not_applicable",
        "canonical_issues": [],
        "citation_context": "explicit",
        "sequence_index": 0,
        "sequence_raw": text[match.start():match.end()],
        "sequence_start_offset": match.start(),
        "sequence_end_offset": match.end(),
        "engine_version": VERSION,
    }


# Loose "chapter:verse" shape for opt-in unresolved reporting.
_UNRESOLVED_RE = re.compile(
    r"(\d{1,3}):(\d{1,3})(?:\s*[-\u2013]\s*(?:(\d{1,3}):)?(\d{1,3}))?(?![\dA-Za-z])"
)


# --------------------------------------------------------------------------
# Canonical coordinate assertion (assert layer -- separate from parsing)
# --------------------------------------------------------------------------
# Parsing recognises a book name and a numeric coordinate. Canonical assertion
# decides whether that coordinate EXISTS in the 66-book KJV Bible. The two are
# deliberately separate so that a parsed coordinate never implies validity.

COORDINATES_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "gd_canonical_coordinates.json")


def _load_coordinates_artifact(path=COORDINATES_PATH):
    try:
        with open(path, encoding="utf-8") as handle:
            artifact = json.load(handle)
    except (OSError, ValueError):
        return None
    return artifact if isinstance(artifact, dict) else None


def _table_from_artifact(artifact):
    """Build ``{book: (verses_per_chapter, ...)}``; None when unusable."""
    if not artifact:
        return None
    books = artifact.get("books")
    if not isinstance(books, list) or len(books) != len(CANON):
        return None
    table = {}
    for entry in books:
        if not isinstance(entry, dict):
            return None
        name = entry.get("book")
        counts = entry.get("chapter_verse_counts")
        if name not in CANON or name in table:
            return None
        if not isinstance(counts, list) or not counts:
            return None
        for count in counts:
            if isinstance(count, bool) or not isinstance(count, int) or count < 1:
                return None
        table[name] = tuple(counts)
    return table if len(table) == len(CANON) else None


_COORDINATES_ARTIFACT = _load_coordinates_artifact()
CANONICAL_COORDINATES = _table_from_artifact(_COORDINATES_ARTIFACT)
COORDINATES_SOURCE = (_COORDINATES_ARTIFACT or {}).get("source")

# Books the pinned artifact PROVES have exactly one chapter. Only these may use
# the single-chapter citation convention; the set is read from the artifact and
# is empty when the artifact is unavailable, which disables the convention
# instead of guessing at book structure.
SINGLE_CHAPTER_BOOKS = frozenset(
    book for book, chapters in (CANONICAL_COORDINATES or {}).items()
    if len(chapters) == 1
)


def has_canonical_coordinates():
    """True when the pinned 66-book KJV coordinate table is loaded and usable."""
    return CANONICAL_COORDINATES is not None


def _normalize_single_chapter_item(book, item):
    """Apply the canonical single-chapter citation convention to one item.

    For a book with exactly one chapter, a bare number is a VERSE and a bare
    range is a VERSE range ("Jude 6" -> "Jude 1:6", "Jude 3-4" -> "Jude 1:3-4").
    Explicit ``chapter:verse`` syntax (``verse_start`` present) and every
    multi-chapter book are returned unchanged. The item's offsets are preserved,
    so ``raw_match`` keeps spanning the original text. Verse limits are NOT
    applied here -- the verse may still be impossible, and the assert layer
    reports that.
    """
    if book not in SINGLE_CHAPTER_BOOKS:
        return item
    chapter, chapter_end, verse_start, verse_end, vs, ves, start, end = item
    if verse_start is not None:
        return item
    if chapter_end is None:
        return (1, None, chapter, None, None, None, start, end)
    return (1, None, chapter, chapter_end, None, None, start, end)


def _assert_reference(row, table):
    """Return ``(canonical_status, issues)`` for one parsed row."""
    if row["resolution_status"] == "unresolved" or row["book"] is None:
        return "not_applicable", []
    if table is None:
        return "not_asserted", ["coordinate_table_unavailable"]
    if row["granularity"] == "book":
        return "asserted_valid", []

    counts = table.get(row["book"])
    if not counts:
        return "not_asserted", ["book_absent_from_coordinate_table"]

    total_chapters = len(counts)

    def verse_limit(number):
        if number is None or not 1 <= number <= total_chapters:
            return None
        return counts[number - 1]

    chapter = row["chapter"]
    chapter_end = row["chapter_end"]
    verse_start = row["verse_start"]
    verse_end = row["verse_end"]
    issues = []

    if chapter is None or not 1 <= chapter <= total_chapters:
        issues.append("chapter_out_of_range")
    if chapter_end is not None:
        if not 1 <= chapter_end <= total_chapters:
            issues.append("end_chapter_out_of_range")
        elif chapter is not None and chapter_end < chapter:
            issues.append("reverse_chapter_range")

    limit = verse_limit(chapter)
    if verse_start is not None and limit is not None and not 1 <= verse_start <= limit:
        issues.append("verse_out_of_range")

    end_limit = verse_limit(chapter_end if chapter_end is not None else chapter)
    if verse_end is not None and end_limit is not None and not 1 <= verse_end <= end_limit:
        issues.append("end_verse_out_of_range")

    if (chapter_end is None and verse_start is not None and verse_end is not None
            and verse_end < verse_start):
        issues.append("reverse_verse_range")

    return ("asserted_valid" if not issues else "asserted_invalid"), issues


def assert_canonical_references(rows, coordinates=None):
    """Return NEW rows carrying ``canonical_status`` and ``canonical_issues``.

    Deterministic assertion against the pinned 66-book KJV coordinate table
    (``gd_canonical_coordinates.json``). It never clamps, repairs, reinterprets
    or drops a coordinate: an impossible reference such as ``Revelation 23:1``
    is reported as ``canonical_status="asserted_invalid"`` with the offending
    codes in ``canonical_issues``. The input rows are not mutated.
    """
    table = CANONICAL_COORDINATES if coordinates is None else coordinates
    asserted = []
    for row in rows:
        new_row = dict(row)
        status, issues = _assert_reference(new_row, table)
        new_row["canonical_status"] = status
        new_row["canonical_issues"] = issues
        asserted.append(new_row)
    return asserted


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def extract_references(text, include_unresolved=False, include_bare_books=False,
                       canonical=True, include_unstructured_chapters=False):
    """Deterministically extract and normalize scripture references from text.

    Backward compatible with the v1.0.0 call signature ``extract_references(text)``
    and with its result fields for simple verse references. See the module
    docstring for the additive fields, the parse/assert split and the precision
    guards.
    """
    if not text:
        return []

    results = []
    occupied = []
    position = 0
    length = len(text)

    while position < length:
        match = BOOK_PATTERN.search(text, position)
        if not match:
            break
        book = BOOK_INDEX.get(_normalize_book_key(match.group("book")))
        items, sequence_end = _parse_reference_sequence(text, match.start(), match.end())
        if not items or book is None:
            position = match.end()
            continue

        book_id = CANON.index(book) + 1
        sequence_raw = text[match.start():sequence_end]
        for index, item in enumerate(items):
            start, end = item[6], item[7]
            if item[2] is None:
                # Chapter-level surface form: only a citation with citation
                # structure (closed structural test, not a noun denylist). A
                # match without structure is held back by default, never
                # silently discarded -- include_unstructured_chapters=True
                # returns it labelled citation_context="unstructured".
                citation_context = _citation_context(
                    text, start, end, text[start:end])
                if (citation_context == "unstructured"
                        and not include_unstructured_chapters):
                    continue
            else:
                citation_context = "explicit"
            row = _make_item(book, book_id,
                             _normalize_single_chapter_item(book, item),
                             sequence_raw, index)
            row["raw_match"] = text[row["start_offset"]:row["end_offset"]]
            row["citation_context"] = citation_context
            row["sequence_start_offset"] = match.start()
            row["sequence_end_offset"] = sequence_end
            results.append(row)
            occupied.append((row["start_offset"], row["end_offset"]))
        position = max(sequence_end, match.end())

    # Explicitly framed book-only references ("the book of Revelation").
    for frame in BOOK_FRAME_PATTERN.finditer(text):
        match = BOOK_PATTERN.match(text, frame.end())
        if not match:
            continue
        if _NUMERIC_TAIL_RE.match(text, match.end()):
            continue  # handled as chapter/verse by the numeric scan
        if _overlaps((frame.start(), match.end()), occupied):
            continue
        if not _first_letter_is_upper(text, match.start(), match.end()):
            continue
        book = BOOK_INDEX.get(_normalize_book_key(match.group("book")))
        if book is None:
            continue
        row = _make_book_only(
            text, book, book, CANON.index(book) + 1, frame.start(), match.end())
        results.append(row)
        occupied.append((row["start_offset"], row["end_offset"]))

    # Opt-in: bare canonical book mentions as granularity "book".
    if include_bare_books:
        for match in BOOK_PATTERN.finditer(text):
            if _overlaps((match.start(), match.end()), occupied):
                continue
            if _NUMERIC_TAIL_RE.match(text, match.end()):
                continue
            if not _first_letter_is_upper(text, match.start(), match.end()):
                continue
            book = BOOK_INDEX.get(_normalize_book_key(match.group("book")))
            if book is None:
                continue
            row = _make_book_only(
                text, book, book, CANON.index(book) + 1, match.start(), match.end())
            results.append(row)
            occupied.append((row["start_offset"], row["end_offset"]))

    # Opt-in: report unroutable chapter:verse spans instead of dropping them.
    if include_unresolved:
        for match in _UNRESOLVED_RE.finditer(text):
            if _overlaps((match.start(), match.end()), occupied):
                continue
            row = _make_unresolved(text, match)
            results.append(row)
            occupied.append((row["start_offset"], row["end_offset"]))

    # Deterministic canonical assertion (separate from parsing).
    if canonical:
        results = assert_canonical_references(results)

    results.sort(key=lambda row: (row["start_offset"], row["end_offset"]))
    return results


if __name__ == "__main__":
    # Internal Unit Test
    test_text = (
        "We see in 1 Cor. 13:4-5 and Matt 24:14 the truth, but false texts like "
        "Hezekiah 1:1 or Normal 4:5 are ignored. Hebrews 8:8, 13 and Romans 8:18-9:5 "
        "matter, as does Psalm 23:1."
    )
    print(f"Running deterministic extraction test (engine v{VERSION})...")
    print(f"Source text: '{test_text}'\n")

    for found in extract_references(test_text):
        print(f"Verified: {str(found['canonical']):<24} "
              f"[{found['granularity']:<7}] "
              f"{found['canonical_status']:<16} "
              f"key={str(found['reference_key']):<16} "
              f"from '{found['raw_match']}'")
