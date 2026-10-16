"""Frozen golden regression suite for gd_scripture_engine (DEF-06 repair).

Run:
    python3 -m unittest discover -s tests -t tests -v
    python3 -m unittest tests.test_gd_scripture_engine -v

This suite is the frozen contract for the deterministic scripture-reference
engine. It has three jobs:

1. GOLDEN   -- freeze the references the roadmap requires the engine to resolve
               (DEF-06) and the granularity model CASE-03 depends on.
2. COMPAT   -- freeze the v1.0.0 legacy result fields for every form the old
               engine already resolved, so the repair cannot silently regress
               existing behaviour.
3. PRECISION -- freeze the guards that stop ordinary prose and noncanonical
               books from becoming Scripture.

Schema note (additive extension, v1.0.0 -> v1.5.0)
-------------------------------------------------
LEGACY_FIELDS is the v1.0.0 result contract for a simple verse reference; it is
unchanged. ADDITIVE_FIELDS was added by the DEF-06 repair to carry granularity,
ranges and stable reference identity. Consumers written against v1.0.0 keep
working: every legacy key is still present with the same meaning for simple
verse references. Granularity "book"/"chapter" rows set the legacy
``chapter``/``verse`` fields to None rather than inventing a verse.

v1.2.0 added the parse/assert split. ``resolution_status="syntactically_parsed"``
asserts only that a book name and a numeric coordinate were recognised.
Canonical existence is a separate verdict in ``canonical_status``, computed
against the pinned 66-book KJV coordinate table.

v1.3.0 adds the canonical single-chapter citation convention: for a book the
pinned artifact proves has exactly one chapter, a bare number is a VERSE
(``"Jude 6"`` -> ``"Jude 1:6"``), still asserted against the same table.

v1.4.0 adds German/European comma chapter-verse notation: a TIGHT
``chapter,verse`` is one reference (``"Hab. 1,3-4"`` -> ``"Habakkuk 1:3-4"``).
The discriminator is typographic (no whitespace around the comma), so an English
spaced chapter list (``"Hebrews 8, 13"``) and an English colon verse list
(``"Heb. 8:8, 13"``) keep their existing meanings.
"""

import os
import sys
import unittest

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

import gd_scripture_engine  # noqa: E402


LEGACY_FIELDS = (
    "canonical", "raw_match", "book", "chapter", "verse",
    "start_offset", "end_offset",
)

ADDITIVE_FIELDS = (
    "granularity", "book_id", "chapter_end", "verse_start", "verse_end",
    "verse_suffix", "verse_end_suffix", "reference_key", "resolution_status",
    "canonical_status", "canonical_issues", "citation_context",
    "sequence_index", "sequence_raw", "sequence_start_offset",
    "sequence_end_offset", "engine_version",
)

GRANULARITIES = ("book", "chapter", "verse", "range")

CANONICAL_STATUSES = (
    "not_asserted", "asserted_valid", "asserted_invalid", "not_applicable",
)

CITATION_CONTEXTS = (
    "explicit", "standalone", "preceded_by_citation_cue",
    "followed_by_boundary", "followed_by_connector", "unstructured",
)

# Canonical book ordinals (1-based, Protestant order) used by reference_key.
BOOK_ID = {
    "Genesis": 1, "Psalms": 19, "Song of Solomon": 22, "Jeremiah": 24,
    "Matthew": 40, "John": 43, "Romans": 45, "1 Corinthians": 46,
    "2 Corinthians": 47, "Ephesians": 49, "Hebrews": 58, "3 John": 64,
    "Revelation": 66,
}


class TestEngineContract(unittest.TestCase):
    """Engine identity and canon integrity."""

    def test_engine_exposes_version_constant(self):
        self.assertTrue(hasattr(gd_scripture_engine, "VERSION"))
        self.assertIsInstance(gd_scripture_engine.VERSION, str)
        self.assertRegex(gd_scripture_engine.VERSION, r"^\d+\.\d+\.\d+$")
        self.assertEqual(gd_scripture_engine.VERSION, "1.5.0")

    def test_every_result_carries_engine_version(self):
        for row in gd_scripture_engine.extract_references("Genesis 1:1"):
            self.assertEqual(row["engine_version"], gd_scripture_engine.VERSION)

    def test_canon_is_the_66_books_in_order(self):
        canon = gd_scripture_engine.CANON
        self.assertEqual(len(canon), 66)
        self.assertEqual(len(set(canon)), 66)
        self.assertEqual(canon[0], "Genesis")
        self.assertEqual(canon[-1], "Revelation")
        for book, book_id in BOOK_ID.items():
            self.assertEqual(canon.index(book) + 1, book_id)

    def test_aliases_resolve_to_canonical_books_only(self):
        for alias, book in gd_scripture_engine.ALIASES.items():
            self.assertIn(book, gd_scripture_engine.CANON,
                          f"alias {alias!r} maps outside the canon")

    def test_book_id_is_stable_and_display_independent(self):
        row = gd_scripture_engine.extract_references("Heb. 8:8, 13")[1]
        self.assertEqual(row["book_id"], BOOK_ID["Hebrews"])
        self.assertEqual(row["reference_key"], "b58:c8:v13")

    def test_extraction_is_deterministic_and_non_destructive(self):
        text = "See Hebrews 8:8, 13 and Romans 8:18-9:5."
        first = gd_scripture_engine.extract_references(text)
        second = gd_scripture_engine.extract_references(text)
        self.assertEqual(first, second)
        self.assertEqual(text, "See Hebrews 8:8, 13 and Romans 8:18-9:5.")

    def test_empty_and_non_string_inputs_are_safe(self):
        self.assertEqual(gd_scripture_engine.extract_references(""), [])
        self.assertEqual(gd_scripture_engine.extract_references(None), [])

    def test_engine_stays_a_pure_deterministic_layer(self):
        # Roadmap sec. 3.1 items 4-5: deterministic extraction and
        # model-attributed scripture_refs are different evidentiary classes and
        # must never be merged. The engine must not reach for either database.
        import ast

        with open(gd_scripture_engine.__file__, encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
        # stdlib only, and no path to a database, model runtime or network.
        self.assertEqual(imported, {"re", "json", "os"})
        self.assertFalse(imported & {
            "sqlite3", "requests", "urllib", "http", "socket", "openai",
            "anthropic", "ollama", "llama_cpp", "transformers", "torch",
        })
        self.assertEqual(
            gd_scripture_engine.extract_references.__code__.co_varnames[:3],
            ("text", "include_unresolved", "include_bare_books"))


class TestGoldenReferences(unittest.TestCase):
    """Roadmap DEF-06 golden cases: expected canonical + granularity."""

    GOLDEN = [
        # (label, text, [(canonical, granularity), ...])
        ("plain verse", "Genesis 1:1", [("Genesis 1:1", "verse")]),
        ("abbrev verse", "Eph. 3:14-15", [("Ephesians 3:14-15", "range")]),
        ("abbrev verse", "Rev. 5:10", [("Revelation 5:10", "verse")]),
        ("abbrev verse", "Jer. 31:31", [("Jeremiah 31:31", "verse")]),
        ("roman numeral", "I Cor. 11:1", [("1 Corinthians 11:1", "verse")]),
        ("roman numeral", "II Corinthians 4:4", [("2 Corinthians 4:4", "verse")]),
        ("roman numeral", "III John 1:2", [("3 John 1:2", "verse")]),
        ("word ordinal", "First Corinthians 13:4", [("1 Corinthians 13:4", "verse")]),
        ("singular Psalm", "Psalm 23:1", [("Psalms 23:1", "verse")]),
        ("plural Psalms", "Psalms 23:1", [("Psalms 23:1", "verse")]),
        ("multi-word book", "Song of Solomon 2:1", [("Song of Solomon 2:1", "verse")]),
        ("chapter-only", "Matthew 24", [("Matthew 24", "chapter")]),
        ("chapter-only", "Romans 8", [("Romans 8", "chapter")]),
        ("chapter-only", "Revelation 12", [("Revelation 12", "chapter")]),
        ("chapter range", "Romans 8-10", [("Romans 8-10", "range")]),
        ("same-chapter range", "Romans 8:18-28", [("Romans 8:18-28", "range")]),
        ("cross-chapter range", "Romans 8:18-9:5", [("Romans 8:18-9:5", "range")]),
        ("verse list", "Heb. 8:8, 13",
         [("Hebrews 8:8", "verse"), ("Hebrews 8:13", "verse")]),
        ("verse list + range", "Hebrews 8:8, 13-15",
         [("Hebrews 8:8", "verse"), ("Hebrews 8:13-15", "range")]),
        ("inherited chapter after verse", "Compare Hebrews 8:8, 13:5 and note it.",
         [("Hebrews 8:8", "verse"), ("Hebrews 13:5", "verse")]),
        ("inherited book via 'and'", "The argument in Hebrews 8:8 and 12:24 is decisive.",
         [("Hebrews 8:8", "verse"), ("Hebrews 12:24", "verse")]),
        ("book-only via framing", "the book of Revelation", [("Revelation", "book")]),
        ("book-only via epistle framing", "The Epistle of James", [("James", "book")]),
    ]

    def test_golden_table(self):
        for label, text, expected in self.GOLDEN:
            with self.subTest(label=label, text=text):
                rows = gd_scripture_engine.extract_references(text)
                got = [(row["canonical"], row["granularity"]) for row in rows]
                self.assertEqual(got, expected)

    def test_granularity_model_is_fully_representable(self):
        seen = set()
        for _, text, expected in self.GOLDEN:
            for _, granularity in expected:
                seen.add(granularity)
        self.assertEqual(seen, set(GRANULARITIES))

    def test_cross_chapter_range_is_never_truncated(self):
        rows = gd_scripture_engine.extract_references(
            "Paul labours in Romans 8:18-9:5 for the glory to come.")
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["canonical"], "Romans 8:18-9:5")
        self.assertEqual(row["verse"], "18-9:5")
        self.assertEqual(
            (row["chapter"], row["verse_start"], row["chapter_end"], row["verse_end"]),
            (8, 18, 9, 5))
        self.assertEqual(row["reference_key"], "b45:c8:v18-c9:v5")
        self.assertEqual(row["granularity"], "range")

    def test_quote_introducing_colon_does_not_truncate_a_range(self):
        # Real corpus form: the colon after the range introduces a quotation.
        text = 'what Jesus said in Matthew 5:17-18: \u201cThink not that I am come\u201d'
        rows = gd_scripture_engine.extract_references(text)
        self.assertEqual([row["canonical"] for row in rows], ["Matthew 5:17-18"])
        self.assertEqual(rows[0]["granularity"], "range")

    def test_spaced_dash_range_is_preserved(self):
        rows = gd_scripture_engine.extract_references(
            "Remember it says in Revelation 3:14 -17 that the Laodecians are naked.")
        self.assertEqual([row["canonical"] for row in rows], ["Revelation 3:14-17"])

    def test_chapter_only_records_carry_no_verse(self):
        row = gd_scripture_engine.extract_references("Matthew 24")[0]
        self.assertIsNone(row["verse"])
        self.assertIsNone(row["verse_start"])
        self.assertEqual(row["chapter"], 24)
        self.assertEqual(row["granularity"], "chapter")
        self.assertEqual(row["reference_key"], "b40:c24")

    def test_book_only_record_shape(self):
        row = gd_scripture_engine.extract_references("the book of Revelation")[0]
        self.assertEqual(row["canonical"], "Revelation")
        self.assertEqual(row["granularity"], "book")
        self.assertIsNone(row["chapter"])
        self.assertIsNone(row["verse"])
        self.assertEqual(row["book_id"], 66)
        self.assertEqual(row["reference_key"], "b66")
        self.assertEqual(row["raw_match"], "the book of Revelation")


class TestVerseListsAndContinuation(unittest.TestCase):
    """Deterministic continuations, and the line where they stop."""

    def test_verse_list_keeps_every_verse(self):
        rows = gd_scripture_engine.extract_references("Heb. 8:8, 13")
        self.assertEqual([row["canonical"] for row in rows],
                         ["Hebrews 8:8", "Hebrews 8:13"])
        first, second = rows
        self.assertEqual(first["chapter"], 8)
        self.assertEqual(first["verse"], "8")
        self.assertEqual(second["chapter"], 8)
        self.assertEqual(second["verse"], "13")
        self.assertEqual(second["raw_match"], "13")
        self.assertEqual(second["sequence_raw"], "Heb. 8:8, 13")
        self.assertEqual([r["sequence_index"] for r in rows], [0, 1])
        self.assertEqual(first["sequence_start_offset"], first["start_offset"])
        self.assertEqual(second["sequence_end_offset"], first["sequence_end_offset"])

    def test_ordinal_prefix_of_next_book_is_not_a_continuation(self):
        # ", 1 Corinthians 9:5" is a new reference, not "verse 1 of Luke 4".
        text = "Peter was married (Matthew 8:14, Luke 4:38, 1 Corinthians 9:5)."
        rows = gd_scripture_engine.extract_references(text)
        self.assertEqual([row["canonical"] for row in rows],
                         ["Matthew 8:14", "Luke 4:38", "1 Corinthians 9:5"])

    def test_inherited_book_requires_a_reference_sequence(self):
        # Same clause, explicit citation separator: deterministic -> inherited.
        rows = gd_scripture_engine.extract_references("See Hebrews 8:8 and 12:24.")
        self.assertEqual([row["canonical"] for row in rows],
                         ["Hebrews 8:8", "Hebrews 12:24"])
        for row in rows:
            self.assertEqual(row["book"], "Hebrews")

    def test_inherited_book_does_not_cross_a_sentence_break(self):
        rows = gd_scripture_engine.extract_references(
            "Hebrews 12:24 is quoted. Later, 12:24 was discussed again.")
        self.assertEqual([row["canonical"] for row in rows], ["Hebrews 12:24"])

    def test_prose_between_references_breaks_the_sequence(self):
        rows = gd_scripture_engine.extract_references(
            "He cited Hebrews 12:24 and later 12:24 again.")
        self.assertEqual([row["canonical"] for row in rows], ["Hebrews 12:24"])

    def test_semicolon_without_a_chapter_is_not_guessed(self):
        # "Hebrews 8:8; 13" is genuinely ambiguous (verse 13 or chapter 13).
        rows = gd_scripture_engine.extract_references("Heb. 8:8; 13")
        self.assertEqual([row["canonical"] for row in rows], ["Hebrews 8:8"])


class TestAmbiguityRefusal(unittest.TestCase):
    """Standalone numbers must never be guessed into Scripture."""

    def test_standalone_chapter_verse_is_not_guessed(self):
        for text in ("12:24", "The meeting is at 12:24.", "See 12:24 for timing."):
            with self.subTest(text=text):
                self.assertEqual(gd_scripture_engine.extract_references(text), [])

    def test_standalone_chapter_verse_can_be_reported_unresolved_when_asked(self):
        rows = gd_scripture_engine.extract_references(
            "The meeting is at 12:24.", include_unresolved=True)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertIsNone(row["canonical"])
        self.assertIsNone(row["book"])
        self.assertIsNone(row["book_id"])
        self.assertIsNone(row["reference_key"])
        self.assertEqual(row["resolution_status"], "unresolved")
        self.assertEqual(row["granularity"], "verse")
        self.assertEqual(row["chapter"], 12)
        self.assertEqual(row["verse"], "24")
        self.assertEqual(row["raw_match"], "12:24")

    def test_unresolved_mode_does_not_fragment_resolved_references(self):
        rows = gd_scripture_engine.extract_references(
            "Romans 8:18-9:5", include_unresolved=True)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["resolution_status"], "syntactically_parsed")

    def test_bare_book_mention_is_opt_in(self):
        self.assertEqual(gd_scripture_engine.extract_references("Revelation"), [])
        rows = gd_scripture_engine.extract_references(
            "Revelation", include_bare_books=True)
        self.assertEqual([row["canonical"] for row in rows], ["Revelation"])
        self.assertEqual(rows[0]["granularity"], "book")

    def test_noncanonical_books_are_rejected(self):
        rejected = (
            "Hezekiah 1:1",
            "Normal 4:5",
            "Gospel of Thomas 1:1",
            "3 Maccabees 1:1",
            "Enoch 1:1",
            "Bel and the Dragon 1:1",
        )
        for text in rejected:
            with self.subTest(text=text):
                self.assertEqual(gd_scripture_engine.extract_references(text), [])

    def test_ordinary_prose_creates_no_false_positives(self):
        prose = (
            "The ratio was 3:16 and the clock showed 12:24 that afternoon.",
            "He scored 2:1 in the final minute of the match.",
            "Use a 1:2 ratio of flour to water.",
            "The vote was 51:49 in favour of the motion.",
            "The job 3 years ago was harder than now.",
            "Chapter and verse numbers like 12:24 appear in ordinary statistics.",
        )
        for text in prose:
            with self.subTest(text=text):
                self.assertEqual(gd_scripture_engine.extract_references(text), [])

    def test_quantity_followers_do_not_become_chapters(self):
        for text in ("Matthew 24 hours later", "Acts 2 ways of doing this"):
            with self.subTest(text=text):
                self.assertEqual(gd_scripture_engine.extract_references(text), [])

    def test_lowercase_book_token_is_not_a_chapter_citation(self):
        self.assertEqual(gd_scripture_engine.extract_references("the job 3 years ago"), [])
        # ... but a lowercase verse citation keeps v1.0.0 case-insensitivity.
        rows = gd_scripture_engine.extract_references("we read rom 8:28 today")
        self.assertEqual([row["canonical"] for row in rows], ["Romans 8:28"])


class TestLegacyCompatibility(unittest.TestCase):
    """Freeze the v1.0.0 outputs for inputs the old engine already resolved."""

    # (text, [(canonical, book, chapter, verse), ...])
    LEGACY = [
        ("1 Cor. 13:4-5 and Matt 24:14 the truth", [
            ("1 Corinthians 13:4-5", "1 Corinthians", 13, "4-5"),
            ("Matthew 24:14", "Matthew", 24, "14")]),
        ("Eph. 3:14-15", [("Ephesians 3:14-15", "Ephesians", 3, "14-15")]),
        ("Rev. 5:10", [("Revelation 5:10", "Revelation", 5, "10")]),
        ("Jer. 31:31", [("Jeremiah 31:31", "Jeremiah", 31, "31")]),
        ("I Cor. 11:1", [("1 Corinthians 11:1", "1 Corinthians", 11, "1")]),
        ("Genesis 1:2", [("Genesis 1:2", "Genesis", 1, "2")]),
        ("We see 1 Cor 13:4-5", [("1 Corinthians 13:4-5", "1 Corinthians", 13, "4-5")]),
        ("Matt 24:14", [("Matthew 24:14", "Matthew", 24, "14")]),
        ("1 Corinthians 11:1", [("1 Corinthians 11:1", "1 Corinthians", 11, "1")]),
        ("2 Cor 4:4", [("2 Corinthians 4:4", "2 Corinthians", 4, "4")]),
        ("Rom 8:28", [("Romans 8:28", "Romans", 8, "28")]),
        ("John 3:16", [("John 3:16", "John", 3, "16")]),
        ("I John 4:8", [("1 John 4:8", "1 John", 4, "8")]),
        ("III John 1:2", [("3 John 1:2", "3 John", 1, "2")]),
        ("1 John 4:8", [("1 John 4:8", "1 John", 4, "8")]),
        ("Ps 23:1", [("Psalms 23:1", "Psalms", 23, "1")]),
        ("Psa 23:1", [("Psalms 23:1", "Psalms", 23, "1")]),
        ("Gen 1:1", [("Genesis 1:1", "Genesis", 1, "1")]),
        ("Heb 13:8", [("Hebrews 13:8", "Hebrews", 13, "8")]),
        ("Rev 22:21", [("Revelation 22:21", "Revelation", 22, "21")]),
        ("1cor 5:1", [("1 Corinthians 5:1", "1 Corinthians", 5, "1")]),
        ("2cor 5:1", [("2 Corinthians 5:1", "2 Corinthians", 5, "1")]),
        ("i cor 3:1", [("1 Corinthians 3:1", "1 Corinthians", 3, "1")]),
        ("ii cor 3:1", [("2 Corinthians 3:1", "2 Corinthians", 3, "1")]),
        ("1 co 3:1", [("1 Corinthians 3:1", "1 Corinthians", 3, "1")]),
        ("Dan 9:24", [("Daniel 9:24", "Daniel", 9, "24")]),
        ("Isa 53:5", [("Isaiah 53:5", "Isaiah", 53, "5")]),
        ("Prov 3:5", [("Proverbs 3:5", "Proverbs", 3, "5")]),
        ("Eccl 3:1", [("Ecclesiastes 3:1", "Ecclesiastes", 3, "1")]),
        ("Lam 3:22", [("Lamentations 3:22", "Lamentations", 3, "22")]),
        ("Ezek 36:26", [("Ezekiel 36:26", "Ezekiel", 36, "26")]),
        ("Hos 6:1", [("Hosea 6:1", "Hosea", 6, "1")]),
        ("Mic 6:8", [("Micah 6:8", "Micah", 6, "8")]),
        ("Nah 1:1", [("Nahum 1:1", "Nahum", 1, "1")]),
        ("Hab 2:4", [("Habakkuk 2:4", "Habakkuk", 2, "4")]),
        ("Zeph 1:1", [("Zephaniah 1:1", "Zephaniah", 1, "1")]),
        ("Hag 1:1", [("Haggai 1:1", "Haggai", 1, "1")]),
        ("Zech 9:9", [("Zechariah 9:9", "Zechariah", 9, "9")]),
        ("Mal 3:1", [("Malachi 3:1", "Malachi", 3, "1")]),
        ("Acts 2:38", [("Acts 2:38", "Acts", 2, "38")]),
        ("Gal 5:22", [("Galatians 5:22", "Galatians", 5, "22")]),
        ("Phil 4:13", [("Philippians 4:13", "Philippians", 4, "13")]),
        ("Col 3:16", [("Colossians 3:16", "Colossians", 3, "16")]),
        ("1 Thess 4:16", [("1 Thessalonians 4:16", "1 Thessalonians", 4, "16")]),
        ("2 Thess 2:1", [("2 Thessalonians 2:1", "2 Thessalonians", 2, "1")]),
        ("1 Tim 2:5", [("1 Timothy 2:5", "1 Timothy", 2, "5")]),
        ("2 Tim 3:16", [("2 Timothy 3:16", "2 Timothy", 3, "16")]),
        ("Tit 2:11", [("Titus 2:11", "Titus", 2, "11")]),
        ("Philem 1:6", [("Philemon 1:6", "Philemon", 1, "6")]),
        ("Jas 2:17", [("James 2:17", "James", 2, "17")]),
        ("1 Pet 1:3", [("1 Peter 1:3", "1 Peter", 1, "3")]),
        ("2 Pet 3:9", [("2 Peter 3:9", "2 Peter", 3, "9")]),
        ("Jude 1:3", [("Jude 1:3", "Jude", 1, "3")]),
        ("Apoc 1:1", [("Revelation 1:1", "Revelation", 1, "1")]),
        ("Cant 2:1", [("Song of Solomon 2:1", "Song of Solomon", 2, "1")]),
        ("Song 2:1", [("Song of Solomon 2:1", "Song of Solomon", 2, "1")]),
        ("Mt 5:1", [("Matthew 5:1", "Matthew", 5, "1")]),
        ("Mk 1:1", [("Mark 1:1", "Mark", 1, "1")]),
        ("Lu 2:1", [("Luke 2:1", "Luke", 2, "1")]),
        ("Jn 1:1", [("John 1:1", "John", 1, "1")]),
    ]

    def test_legacy_canonical_book_chapter_verse_unchanged(self):
        for text, expected in self.LEGACY:
            with self.subTest(text=text):
                rows = gd_scripture_engine.extract_references(text)
                got = [(r["canonical"], r["book"], r["chapter"], r["verse"])
                       for r in rows]
                self.assertEqual(got, expected)

    def test_legacy_raw_match_and_offsets_are_verbatim_spans(self):
        for text, _ in self.LEGACY:
            with self.subTest(text=text):
                for row in gd_scripture_engine.extract_references(text):
                    self.assertEqual(
                        row["raw_match"],
                        text[row["start_offset"]:row["end_offset"]])
                    self.assertEqual(row["start_offset"],
                                     row["sequence_start_offset"])

    def test_every_legacy_reference_is_canonically_valid(self):
        # The v1.0.0 forms in LEGACY are all real references; none may be
        # asserted invalid by the coordinate layer.
        for text, _ in self.LEGACY:
            with self.subTest(text=text):
                for row in gd_scripture_engine.extract_references(text):
                    self.assertEqual(row["canonical_status"], "asserted_valid",
                                     f"{text!r} -> {row['canonical']}")

    def test_every_alias_and_canonical_name_round_trips(self):
        # Chapter 1 verse 1 exists in every canonical book, so every name and
        # every alias must resolve it and pass canonical assertion. An earlier
        # revision asserted "{book} 3:16" for all 66 books, which is an
        # IMPOSSIBLE reference for Obadiah, Philemon, 2 John, 3 John, Jude,
        # Haggai and Nahum -- books with no chapter 3. A test must never require
        # an impossible Bible reference to resolve.
        engine = gd_scripture_engine
        for book in engine.CANON:
            with self.subTest(book=book):
                rows = engine.extract_references(f"{book} 1:1")
                self.assertTrue(rows, f"canonical name {book!r} did not resolve")
                self.assertEqual(rows[0]["canonical"], f"{book} 1:1")
                self.assertEqual(rows[0]["book_id"], engine.CANON.index(book) + 1)
                self.assertEqual(rows[0]["canonical_status"], "asserted_valid")
        for alias, book in engine.ALIASES.items():
            with self.subTest(alias=alias):
                rows = engine.extract_references(f"{alias} 1:1")
                self.assertTrue(rows, f"alias {alias!r} did not resolve")
                self.assertEqual(rows[0]["canonical"], f"{book} 1:1")
                self.assertEqual(rows[0]["canonical_status"], "asserted_valid")


class TestResultSchema(unittest.TestCase):
    """The v1.1.0 schema is an additive extension of the v1.0.0 contract."""

    SAMPLE_TEXTS = (
        "Genesis 1:1",
        "Eph. 3:14-15",
        "Matthew 24",
        "Revelation 12",
        "Romans 8:18-9:5",
        "Heb. 8:8, 13",
        "the book of Revelation",
    )

    def test_all_declared_fields_present_and_no_undeclared_fields(self):
        expected = set(LEGACY_FIELDS) | set(ADDITIVE_FIELDS)
        for text in self.SAMPLE_TEXTS:
            with self.subTest(text=text):
                for row in gd_scripture_engine.extract_references(text):
                    self.assertEqual(set(row), expected)

    def test_granularity_values_are_from_the_model(self):
        for text in self.SAMPLE_TEXTS:
            with self.subTest(text=text):
                for row in gd_scripture_engine.extract_references(text):
                    self.assertIn(row["granularity"], GRANULARITIES)

    def test_reference_key_is_display_independent_and_stable(self):
        for text in self.SAMPLE_TEXTS:
            with self.subTest(text=text):
                for row in gd_scripture_engine.extract_references(text):
                    self.assertIsInstance(row["reference_key"], str)
                    self.assertNotIn(row["book"] or "", row["reference_key"])
                    self.assertTrue(row["reference_key"].startswith("b"))

    def test_offsets_are_ordered_and_inside_the_text(self):
        for text in self.SAMPLE_TEXTS:
            rows = gd_scripture_engine.extract_references(text)
            with self.subTest(text=text):
                previous = -1
                for row in rows:
                    self.assertLess(row["start_offset"], row["end_offset"])
                    self.assertLessEqual(row["end_offset"], len(text))
                    self.assertGreaterEqual(row["start_offset"], previous)
                    previous = row["start_offset"]
                    self.assertEqual(
                        row["raw_match"],
                        text[row["start_offset"]:row["end_offset"]])
                    self.assertLessEqual(row["sequence_start_offset"],
                                         row["sequence_end_offset"])

    def test_parsed_rows_always_carry_a_book_identity(self):
        for text in self.SAMPLE_TEXTS:
            with self.subTest(text=text):
                for row in gd_scripture_engine.extract_references(text):
                    self.assertEqual(row["resolution_status"], "syntactically_parsed")
                    self.assertIsNotNone(row["book_id"])
                    self.assertIn(row["book"], gd_scripture_engine.CANON)
                    self.assertIn(row["canonical_status"], CANONICAL_STATUSES)
                    self.assertIn(row["citation_context"], CITATION_CONTEXTS)
                    self.assertIsInstance(row["canonical_issues"], list)

    def test_every_sample_text_is_canonically_valid(self):
        for text in self.SAMPLE_TEXTS:
            with self.subTest(text=text):
                for row in gd_scripture_engine.extract_references(text):
                    self.assertEqual(row["canonical_status"], "asserted_valid")
                    self.assertEqual(row["canonical_issues"], [])


class TestCanonicalCoordinateAssertion(unittest.TestCase):
    """BLOCKER 1: a parsed coordinate is not a canonical coordinate.

    Assertion is deterministic against the pinned 66-book KJV table. Impossible
    coordinates are reported -- never clamped, repaired, reinterpreted or
    silently dropped.
    """

    # (text, expected canonical_issues) -- all canonically impossible.
    IMPOSSIBLE = (
        ("Revelation 23:1", ["chapter_out_of_range"]),
        ("Obadiah 2:1", ["chapter_out_of_range"]),
        ("Obadiah 2:99", ["chapter_out_of_range"]),
        ("John 3:999", ["verse_out_of_range"]),
        ("Jude 2:1", ["chapter_out_of_range"]),
        ("3 John 2:1", ["chapter_out_of_range"]),
        ("Romans 17:1", ["chapter_out_of_range"]),
        ("Hebrews 8:99", ["verse_out_of_range"]),
        ("Romans 8:18-99", ["end_verse_out_of_range"]),
        ("Romans 17:1-2", ["chapter_out_of_range"]),
        ("Revelation 22:21-23:1", ["end_chapter_out_of_range"]),
        ("Romans 9:5-8:18", ["reverse_chapter_range"]),
        ("Romans 8:28-18", ["reverse_verse_range"]),
    )

    VALID = (
        "Genesis 1:1", "Revelation 22:21", "Obadiah 1:21", "John 3:16",
        "Jude 1:25", "3 John 1:2", "Hebrews 8:13", "Romans 8:18-28",
        "Romans 8:18-9:5", "Psalms 119:176", "Isaiah 66:24", "Matthew 28:20",
        "Philemon 1:25", "Psalm 117:2",
    )

    def test_coordinate_table_is_loaded_and_pinned(self):
        self.assertTrue(gd_scripture_engine.has_canonical_coordinates())
        table = gd_scripture_engine.CANONICAL_COORDINATES
        self.assertEqual(len(table), 66)
        self.assertEqual(sum(len(chapters) for chapters in table.values()), 1189)
        self.assertEqual(sum(sum(chapters) for chapters in table.values()), 31102)
        self.assertEqual(table["Genesis"][0], 31)
        self.assertEqual(len(table["Psalms"]), 150)
        self.assertEqual(table["Psalms"][118], 176)
        self.assertEqual(len(table["Revelation"]), 22)
        self.assertEqual(table["Revelation"][21], 21)

    def test_coordinate_source_provenance_is_recorded(self):
        source = gd_scripture_engine.COORDINATES_SOURCE
        self.assertIsInstance(source, dict)
        self.assertEqual(len(source["sha256"]), 64)
        self.assertEqual(source["book_count"], 66)
        self.assertEqual(source["verse_count"], 31102)
        self.assertTrue(source["path"])
        self.assertTrue(source["derivation"])

    def test_impossible_coordinates_are_asserted_invalid(self):
        for text, issues in self.IMPOSSIBLE:
            with self.subTest(text=text):
                rows = gd_scripture_engine.extract_references(text)
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["canonical_status"], "asserted_invalid")
                self.assertEqual(rows[0]["canonical_issues"], issues)

    def test_invalid_coordinates_are_reported_not_clamped_or_dropped(self):
        for text, _ in self.IMPOSSIBLE:
            with self.subTest(text=text):
                row = gd_scripture_engine.extract_references(text)[0]
                # Reported verbatim: the coordinate is never rewritten into a
                # nearby valid one, and the match is never discarded.
                self.assertEqual(row["raw_match"], text)
                self.assertEqual(row["canonical"], text)
                self.assertEqual(row["resolution_status"], "syntactically_parsed")

    def test_valid_coordinates_are_asserted_valid(self):
        for text in self.VALID:
            with self.subTest(text=text):
                rows = gd_scripture_engine.extract_references(text)
                self.assertEqual(len(rows), 1, text)
                self.assertEqual(rows[0]["canonical_status"], "asserted_valid")
                self.assertEqual(rows[0]["canonical_issues"], [])

    def test_books_without_a_third_chapter_reject_chapter_three(self):
        for book in ("Obadiah", "Philemon", "2 John", "3 John", "Jude", "Haggai"):
            with self.subTest(book=book):
                rows = gd_scripture_engine.extract_references(f"{book} 3:16")
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["canonical_status"], "asserted_invalid")

    def test_parsing_without_assertion_never_claims_validity(self):
        rows = gd_scripture_engine.extract_references(
            "Revelation 23:1", canonical=False)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["canonical_status"], "not_asserted")
        self.assertEqual(rows[0]["canonical_issues"], [])
        self.assertEqual(rows[0]["resolution_status"], "syntactically_parsed")

    def test_assertion_never_mutates_its_input_rows(self):
        parsed = gd_scripture_engine.extract_references(
            "Revelation 23:1 and John 3:16", canonical=False)
        snapshot = [dict(row) for row in parsed]
        gd_scripture_engine.assert_canonical_references(parsed)
        self.assertEqual(parsed, snapshot)

    def test_unresolved_rows_are_not_applicable_not_valid(self):
        rows = gd_scripture_engine.extract_references(
            "12:24", include_unresolved=True)
        self.assertEqual(rows[0]["canonical_status"], "not_applicable")
        self.assertEqual(rows[0]["canonical_issues"], [])


class TestChapterOnlyCitationStructure(unittest.TestCase):
    """BLOCKER 2: chapter-level precision by citation structure.

    A bare chapter number is Scripture only when the surrounding text shows
    citation structure. This is deliberately a closed structural test, not an
    ever-growing noun denylist: "Job 42 tasks" and "Genesis 49 is a prophecy"
    are syntactically identical, so the engine refuses to guess for either.
    """

    REQUIRED_TRUE = (
        ("Matthew 24", ["Matthew 24"], "standalone"),
        ("Romans 8", ["Romans 8"], "standalone"),
        ("Revelation 12", ["Revelation 12"], "standalone"),
        ("the prophecy in Matthew 24", ["Matthew 24"],
         "preceded_by_citation_cue"),
        ("Read Romans 8.", ["Romans 8"], "preceded_by_citation_cue"),
        ("Notice Revelation 12, and study it.", ["Revelation 12"],
         "preceded_by_citation_cue"),
        ("Matthew 24.", ["Matthew 24"], "followed_by_boundary"),
        ("Matthew 24, 25", ["Matthew 24", "Matthew 25"],
         "followed_by_connector"),
    )

    STRUCTURE_ABSENT = (
        "Mark 24 students",
        "John 3 cars",
        "Job 42 tasks",
        "Matthew 24 hours",
        "Acts 2 ways of doing this",
        "John 3 cars were parked outside",
        "Job 42 tasks remain",
        "The teacher gave Mark 24 students a test.",
    )

    def test_required_chapter_only_cases_still_resolve(self):
        for text, canonicals, context in self.REQUIRED_TRUE:
            with self.subTest(text=text):
                rows = gd_scripture_engine.extract_references(text)
                self.assertEqual([row["canonical"] for row in rows], canonicals)
                for row in rows:
                    self.assertEqual(row["granularity"], "chapter")
                self.assertEqual(rows[0]["citation_context"], context)

    def test_structurally_unsupported_chapter_numbers_are_not_scripture(self):
        for text in self.STRUCTURE_ABSENT:
            with self.subTest(text=text):
                self.assertEqual(gd_scripture_engine.extract_references(text), [])

    def test_held_back_matches_are_recoverable_never_discarded(self):
        for text in self.STRUCTURE_ABSENT:
            with self.subTest(text=text):
                rows = gd_scripture_engine.extract_references(
                    text, include_unstructured_chapters=True)
                self.assertEqual(len(rows), 1, text)
                self.assertEqual(rows[0]["citation_context"], "unstructured")
                self.assertEqual(rows[0]["resolution_status"],
                                 "syntactically_parsed")

    def test_valid_chapter_numbers_in_prose_are_the_hard_case(self):
        # Canonical assertion cannot separate these: Job really has 42 chapters
        # and John really has 3. Only citation structure can.
        for text in ("Job 42 tasks remain", "John 3 cars"):
            with self.subTest(text=text):
                self.assertEqual(gd_scripture_engine.extract_references(text), [])
        for text in ("Job 42", "John 3"):
            with self.subTest(text=text):
                rows = gd_scripture_engine.extract_references(text)
                self.assertEqual([row["canonical"] for row in rows], [text])
                self.assertEqual(rows[0]["canonical_status"], "asserted_valid")

    def test_invalid_chapter_numbers_never_need_the_structure_test(self):
        # Mark has 16 chapters: assertion alone settles this one.
        self.assertEqual(
            gd_scripture_engine.extract_references(
                "Mark 24 students", include_unstructured_chapters=True)[0]
            ["canonical_status"], "asserted_invalid")

    def test_chapter_ranges_use_the_same_structural_test(self):
        rows = gd_scripture_engine.extract_references("Romans 8-10")
        self.assertEqual(rows[0]["citation_context"], "standalone")
        self.assertEqual(rows[0]["canonical_status"], "asserted_valid")
        self.assertEqual(gd_scripture_engine.extract_references(
            "Genesis 1-2 describes creation"), [])

    def test_citation_context_vocabulary_is_closed(self):
        texts = ("Genesis 1:1", "Matthew 24", "the book of Revelation",
                 "Hebrews 8:8, 13", "Job 42 tasks")
        for text in texts:
            with self.subTest(text=text):
                for row in gd_scripture_engine.extract_references(
                        text, include_unstructured_chapters=True):
                    self.assertIn(row["citation_context"], CITATION_CONTEXTS)

    def test_the_noun_denylist_and_global_ceilings_are_gone(self):
        for stale in ("_NON_REFERENCE_FOLLOWERS", "_chapter_only_allowed",
                      "MAX_CHAPTER", "MAX_VERSE"):
            with self.subTest(symbol=stale):
                self.assertFalse(hasattr(gd_scripture_engine, stale))


class TestSingleChapterConvention(unittest.TestCase):
    """Canonical single-chapter citation convention (v1.3.0).

    For a book the pinned artifact proves has exactly ONE chapter, a bare number
    is a VERSE (``"Jude 6"`` -> ``"Jude 1:6"``), never a chapter. Verse limits
    come from the same artifact, so impossible verse numbers stay invalid.
    """

    SINGLE_CHAPTER = ("Obadiah", "Philemon", "2 John", "3 John", "Jude")

    # (text, canonical, granularity, chapter, verse, reference_key)
    VALID = (
        ("Jude 6", "Jude 1:6", "verse", 1, "6", "b65:c1:v6"),
        ("Jude 3-4", "Jude 1:3-4", "range", 1, "3-4", "b65:c1:v3-c1:v4"),
        ("2 John 7", "2 John 1:7", "verse", 1, "7", "b63:c1:v7"),
        ("III John 2", "3 John 1:2", "verse", 1, "2", "b64:c1:v2"),
        ("Obadiah 21", "Obadiah 1:21", "verse", 1, "21", "b31:c1:v21"),
        ("Philemon 25", "Philemon 1:25", "verse", 1, "25", "b57:c1:v25"),
        ("III Jn 2", "3 John 1:2", "verse", 1, "2", "b64:c1:v2"),
        ("Jude 14-15", "Jude 1:14-15", "range", 1, "14-15", "b65:c1:v14-c1:v15"),
        ("Jude 1-4", "Jude 1:1-4", "range", 1, "1-4", "b65:c1:v1-c1:v4"),
    )

    IMPOSSIBLE_VERSE = ("Jude 26", "Obadiah 22", "Philemon 26", "3 John 15")

    def test_single_chapter_set_comes_from_the_artifact(self):
        self.assertEqual(set(gd_scripture_engine.SINGLE_CHAPTER_BOOKS),
                         set(self.SINGLE_CHAPTER))
        for book in self.SINGLE_CHAPTER:
            with self.subTest(book=book):
                self.assertEqual(
                    len(gd_scripture_engine.CANONICAL_COORDINATES[book]), 1)

    def test_bare_number_is_a_verse_not_a_chapter(self):
        for text, canonical, granularity, chapter, verse, key in self.VALID:
            with self.subTest(text=text):
                rows = gd_scripture_engine.extract_references(text)
                self.assertEqual(len(rows), 1, text)
                row = rows[0]
                self.assertEqual(row["canonical"], canonical)
                self.assertEqual(row["granularity"], granularity)
                self.assertEqual(row["chapter"], chapter)
                self.assertEqual(row["verse"], verse)
                self.assertIsNone(row["chapter_end"])
                self.assertEqual(row["reference_key"], key)
                self.assertEqual(row["canonical_status"], "asserted_valid")
                self.assertEqual(row["canonical_issues"], [])

    def test_raw_match_offsets_and_sequence_are_preserved(self):
        text = "It is written in Jude 6 that they were reserved."
        rows = gd_scripture_engine.extract_references(text)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        # The normalized coordinate differs from the verbatim original.
        self.assertEqual(row["canonical"], "Jude 1:6")
        self.assertEqual(row["raw_match"], "Jude 6")
        self.assertEqual(text[row["start_offset"]:row["end_offset"]], "Jude 6")
        self.assertEqual(row["sequence_raw"], "Jude 6")
        self.assertEqual(row["sequence_start_offset"], row["start_offset"])
        self.assertEqual(row["citation_context"], "preceded_by_citation_cue")
        self.assertEqual(row["engine_version"], gd_scripture_engine.VERSION)

    def test_explicit_chapter_verse_syntax_is_untouched(self):
        for text in ("Jude 1:6", "2 John 1:7", "Obadiah 1:21",
                     "Philemon 1:25", "3 John 1:2"):
            with self.subTest(text=text):
                rows = gd_scripture_engine.extract_references(text)
                self.assertEqual(len(rows), 1, text)
                self.assertEqual(rows[0]["canonical"], text)
                self.assertEqual(rows[0]["chapter"], 1)
                self.assertEqual(rows[0]["citation_context"], "explicit")
                self.assertEqual(rows[0]["canonical_status"], "asserted_valid")

    def test_impossible_verse_numbers_are_not_repaired(self):
        for text in self.IMPOSSIBLE_VERSE:
            with self.subTest(text=text):
                rows = gd_scripture_engine.extract_references(text)
                self.assertEqual(len(rows), 1, text)
                row = rows[0]
                self.assertEqual(row["granularity"], "verse")
                self.assertEqual(row["chapter"], 1)
                self.assertEqual(row["canonical_status"], "asserted_invalid")
                self.assertEqual(row["canonical_issues"], ["verse_out_of_range"])
                self.assertEqual(row["raw_match"], text)

    def test_multi_chapter_books_never_use_the_shorthand(self):
        for text in ("Romans 8", "Matthew 24", "John 3", "Isaiah 6", "Acts 2"):
            with self.subTest(text=text):
                rows = gd_scripture_engine.extract_references(text)
                self.assertEqual(len(rows), 1, text)
                row = rows[0]
                self.assertEqual(row["canonical"], text)
                self.assertEqual(row["granularity"], "chapter")
                self.assertIsNone(row["verse_start"])
                self.assertEqual(row["chapter"], int(text.split(" ")[-1]))
                self.assertEqual(row["canonical_status"], "asserted_valid")

    def test_single_chapter_set_is_exactly_the_one_chapter_books(self):
        for book, chapters in gd_scripture_engine.CANONICAL_COORDINATES.items():
            with self.subTest(book=book):
                self.assertEqual(
                    book in gd_scripture_engine.SINGLE_CHAPTER_BOOKS,
                    len(chapters) == 1)

    def test_multi_chapter_books_are_unaffected_by_the_convention(self):
        # A bare number in a multi-chapter book stays chapter granularity even
        # when the number would also be a valid verse number.
        for text in ("Romans 8", "John 3", "Revelation 12", "Psalms 119"):
            with self.subTest(text=text):
                row = gd_scripture_engine.extract_references(text)[0]
                self.assertEqual(row["granularity"], "chapter")
                self.assertIsNone(row["verse"])

    def test_roman_numeral_and_alias_short_forms_keep_their_book(self):
        # Regression: "II Jn 7" used to resolve to John 7 -- the ordinal head was
        # silently dropped, attributing the citation to the wrong book.
        for text, canonical in (("II Jn 7", "2 John 1:7"),
                                ("III Jn 2", "3 John 1:2"),
                                ("I Jn 4:8", "1 John 4:8"),
                                ("II Jn 1:7", "2 John 1:7"),
                                ("III John 2", "3 John 1:2"),
                                ("II Pet 2:4", "2 Peter 2:4")):
            with self.subTest(text=text):
                rows = gd_scripture_engine.extract_references(text)
                self.assertEqual(len(rows), 1, text)
                self.assertEqual(rows[0]["canonical"], canonical)
        # The unnumbered short form still means the Gospel of John.
        rows = gd_scripture_engine.extract_references("Jn 3:16")
        self.assertEqual([row["canonical"] for row in rows], ["John 3:16"])


class TestEuropeanCommaNotation(unittest.TestCase):
    """German/European comma chapter-verse notation (v1.4.0).

    A TIGHT ``chapter,verse`` is one reference. A colon form is an English verse
    list and a *spaced* comma is an English chapter list; neither may change.
    """

    # (text, canonical, granularity, reference_key)
    REQUIRED = (
        ("Mal. 1,1-5", "Malachi 1:1-5", "range", "b39:c1:v1-c1:v5"),
        ("Hab. 1,3-4", "Habakkuk 1:3-4", "range", "b35:c1:v3-c1:v4"),
        ("Eph. 2,20-22", "Ephesians 2:20-22", "range", "b49:c2:v20-c2:v22"),
        ("Phil. 2,5", "Philippians 2:5", "verse", "b50:c2:v5"),
        ("Daniel 11,40-41", "Daniel 11:40-41", "range", "b27:c11:v40-c11:v41"),
    )

    def test_required_european_comma_cases(self):
        for text, canonical, granularity, key in self.REQUIRED:
            with self.subTest(text=text):
                rows = gd_scripture_engine.extract_references(text)
                self.assertEqual(len(rows), 1, text)
                row = rows[0]
                self.assertEqual(row["canonical"], canonical)
                self.assertEqual(row["granularity"], granularity)
                self.assertEqual(row["reference_key"], key)
                self.assertEqual(row["canonical_status"], "asserted_valid")
                self.assertEqual(row["canonical_issues"], [])
                self.assertEqual(row["raw_match"], text)

    def test_semicolon_continues_european_notation(self):
        rows = gd_scripture_engine.extract_references("Hab. 1,3-4; 3,2")
        self.assertEqual([r["canonical"] for r in rows],
                         ["Habakkuk 1:3-4", "Habakkuk 3:2"])
        self.assertEqual([r["granularity"] for r in rows], ["range", "verse"])
        self.assertTrue(all(r["canonical_status"] == "asserted_valid"
                            for r in rows))
        self.assertEqual(rows[0]["raw_match"], "Hab. 1,3-4")
        self.assertEqual(rows[1]["raw_match"], "3,2")

    def test_offsets_sequence_and_provenance_are_preserved(self):
        text = "Der Prophet sagt es (Hab. 1,3-4)."
        rows = gd_scripture_engine.extract_references(text)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["canonical"], "Habakkuk 1:3-4")
        self.assertEqual(row["raw_match"], "Hab. 1,3-4")
        self.assertEqual(text[row["start_offset"]:row["end_offset"]], "Hab. 1,3-4")
        self.assertEqual(row["sequence_raw"], "Hab. 1,3-4")
        self.assertEqual(row["engine_version"], gd_scripture_engine.VERSION)

    def test_english_verse_lists_are_not_regressed(self):
        for text, want in (("Heb. 8:8, 13", ["Hebrews 8:8", "Hebrews 8:13"]),
                           ("Heb. 8:8, 13-15",
                            ["Hebrews 8:8", "Hebrews 8:13-15"]),
                           ("Hebrews 8:8, 13, 15",
                            ["Hebrews 8:8", "Hebrews 8:13", "Hebrews 8:15"])):
            with self.subTest(text=text):
                rows = gd_scripture_engine.extract_references(text)
                self.assertEqual([r["canonical"] for r in rows], want, text)
                self.assertTrue(all(r["granularity"] in ("verse", "range")
                                    for r in rows), text)
                # The list never spawns a new chapter.
                self.assertTrue(all(r["chapter"] == 8 for r in rows), text)

    def test_spaced_comma_stays_an_english_chapter_list(self):
        for text, want in (("Hebrews 8, 13", ["Hebrews 8", "Hebrews 13"]),
                           ("Matthew 24, 25", ["Matthew 24", "Matthew 25"])):
            with self.subTest(text=text):
                rows = gd_scripture_engine.extract_references(text)
                self.assertEqual([r["canonical"] for r in rows], want, text)
                self.assertTrue(all(r["granularity"] == "chapter"
                                    for r in rows), text)

    def test_numeric_comma_prose_never_becomes_valid_scripture(self):
        for text in ("The ratio was 3,16 and 51,49 overall.",
                     "In 1998, 3,000 people attended the meeting.",
                     "He scored 2:1 in the final minute."):
            with self.subTest(text=text):
                self.assertEqual(gd_scripture_engine.extract_references(text), [])
        # A thousands separator next to a book token must not yield a *valid*
        # reference either: it is read as an impossible verse and reported.
        for text in ("Mark 5,000 people were fed.",
                     "Acts 2,000 were baptized."):
            with self.subTest(text=text):
                rows = gd_scripture_engine.extract_references(text)
                self.assertTrue(rows, text)
                self.assertTrue(all(r["canonical_status"] == "asserted_invalid"
                                    for r in rows), text)
                self.assertTrue(all(r["granularity"] == "verse" for r in rows),
                                text)

    def test_colon_notation_is_unchanged(self):
        for canonical in ("John 3:16", "Hebrews 8:8", "Romans 8:18-9:5"):
            with self.subTest(canonical=canonical):
                self.assertEqual(
                    [r["canonical"] for r in
                     gd_scripture_engine.extract_references(canonical)],
                    [canonical])

    def test_single_chapter_convention_is_unchanged(self):
        rows = gd_scripture_engine.extract_references("Jude 1,6")
        self.assertEqual([r["canonical"] for r in rows], ["Jude 1:6"])
        self.assertEqual(rows[0]["granularity"], "verse")
        rows = gd_scripture_engine.extract_references("Jude 6")
        self.assertEqual([r["canonical"] for r in rows], ["Jude 1:6"])
        rows = gd_scripture_engine.extract_references("II Jn 7")
        self.assertEqual([r["canonical"] for r in rows], ["2 John 1:7"])

    def test_cross_chapter_range_behaviour_is_unchanged(self):
        rows = gd_scripture_engine.extract_references("Romans 8:18-9:5")
        self.assertEqual([r["canonical"] for r in rows], ["Romans 8:18-9:5"])
        self.assertEqual(rows[0]["granularity"], "range")
        self.assertEqual(rows[0]["chapter"], 8)
        self.assertEqual(rows[0]["chapter_end"], 9)


class TestGenericCuePrecision(unittest.TestCase):
    """Generic grammatical cues must not manufacture citations (v1.5.0).

    A generic word ("to", "and", "of", "with", "for", "as", "now", "then", ...)
    appears in front of a book name in ordinary prose all the time. It is never
    sufficient on its own: the structure AFTER the number decides.
    """

    ADVERSARIAL = (
        "I spoke to John 3 times yesterday.",
        "Mary and Mark 5 students went home.",
        "We met with Luke 2 people.",
        "The report on Acts 2 issues was filed.",
        "For John 3 examples, see the appendix.",
        "Now John 3 cars remain.",
        "Then Mark 5 students arrived.",
        "I wrote to Jude 6 times.",
        "Mary and Jude 6 students attended.",
    )

    # The two single-chapter prose cases: the single-chapter convention can make
    # the *coordinate* valid, but it must never make the *citation*.
    JUDE_PROSE = ("I wrote to Jude 6 times.",
                  "Mary and Jude 6 students attended.")

    def test_generic_cue_prose_is_not_extracted(self):
        for text in self.ADVERSARIAL:
            with self.subTest(text=text):
                self.assertEqual(gd_scripture_engine.extract_references(text), [])

    def test_jude_prose_can_never_be_asserted_valid_by_default(self):
        for text in self.JUDE_PROSE:
            with self.subTest(text=text):
                # The default path must not contain Jude 1:6 in any form.
                self.assertEqual(gd_scripture_engine.extract_references(text), [])
                rows = gd_scripture_engine.extract_references(
                    text, include_unstructured_chapters=True)
                self.assertEqual(len(rows), 1, text)
                self.assertEqual(rows[0]["citation_context"], "unstructured")
                self.assertNotEqual(rows[0]["citation_context"],
                                    "preceded_by_citation_cue")
                self.assertEqual(rows[0]["canonical"], "Jude 1:6")
                self.assertEqual(rows[0]["raw_match"], "Jude 6")

    def test_generic_prose_is_recoverable_as_unstructured(self):
        for text in self.ADVERSARIAL:
            with self.subTest(text=text):
                rows = gd_scripture_engine.extract_references(
                    text, include_unstructured_chapters=True)
                self.assertEqual(len(rows), 1, text)
                self.assertEqual(rows[0]["citation_context"], "unstructured")
                if rows[0]["book"] not in gd_scripture_engine.SINGLE_CHAPTER_BOOKS:
                    # Multi-chapter books stay chapter granularity, no verse.
                    self.assertEqual(rows[0]["granularity"], "chapter")
                    self.assertIsNone(rows[0]["verse_start"])

    def test_strong_cues_remain_sufficient_on_their_own(self):
        for text, canonical in (("the prophecy in Matthew 24", "Matthew 24"),
                                ("Read Romans 8.", "Romans 8"),
                                ("Notice Revelation 12.", "Revelation 12"),
                                ("See John 3.", "John 3"),
                                ("Compare Hebrews 8.", "Hebrews 8"),
                                ("in Jude 6", "Jude 1:6"),
                                ("See Jude 6.", "Jude 1:6")):
            with self.subTest(text=text):
                rows = gd_scripture_engine.extract_references(text)
                self.assertEqual([r["canonical"] for r in rows], [canonical])
                self.assertEqual(rows[0]["citation_context"],
                                 "preceded_by_citation_cue")

    def test_standalone_chapter_references_are_unchanged(self):
        for canonical in ("Matthew 24", "Romans 8", "Revelation 12"):
            with self.subTest(canonical=canonical):
                rows = gd_scripture_engine.extract_references(canonical)
                self.assertEqual([r["canonical"] for r in rows], [canonical])
                self.assertEqual(rows[0]["citation_context"], "standalone")

    def test_a_strong_cue_behind_a_generic_word_still_counts(self):
        # "of"/"from" are generic, but "verses"/"read" behind them are not.
        for text, canonical in (
                ("the last few verses of Matthew 24 should be followed by",
                 "Matthew 24"),
                ("the account we read from Acts 15 makes clear", "Acts 15")):
            with self.subTest(text=text):
                rows = gd_scripture_engine.extract_references(text)
                self.assertEqual([r["canonical"] for r in rows], [canonical])
                self.assertEqual(rows[0]["citation_context"],
                                 "preceded_by_citation_cue")

    def test_generic_cue_linking_onto_a_reference_is_list_structure(self):
        rows = gd_scripture_engine.extract_references(
            "Deuteronomy 28 and Leviticus 26 are not all the result")
        self.assertEqual([r["canonical"] for r in rows],
                         ["Deuteronomy 28", "Leviticus 26"])
        for row in rows:
            self.assertEqual(row["granularity"], "chapter")

    def test_cue_sets_are_disjoint_and_generic_words_stay_generic(self):
        strong = gd_scripture_engine._STRONG_CITATION_CUES
        generic = gd_scripture_engine._GENERIC_PRECEDING_WORDS
        self.assertFalse(strong & generic)
        for word in ("to", "and", "or", "with", "about", "by", "on", "for", "as",
                     "but", "also", "now", "then", "from", "at", "of"):
            with self.subTest(word=word):
                self.assertIn(word, generic)
                self.assertNotIn(word, strong)
        for word in ("see", "read", "notice", "compare", "chapter", "verse",
                     "quoted", "cited"):
            with self.subTest(word=word):
                self.assertIn(word, strong)

    def test_generic_cue_with_following_structure_is_still_a_citation(self):
        # Same generic cue, but citation structure follows the number.
        for text, context in (("Matthew 24, 25", "followed_by_connector"),
                              ("see also Psalm 89", "preceded_by_citation_cue")):
            with self.subTest(text=text):
                rows = gd_scripture_engine.extract_references(text)
                self.assertTrue(rows)
                self.assertEqual(rows[0]["citation_context"], context)


if __name__ == "__main__":
    unittest.main(verbosity=2)
