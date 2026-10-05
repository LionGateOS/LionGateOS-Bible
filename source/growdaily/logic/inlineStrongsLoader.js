// logic/inlineStrongsLoader.js
// GrowDaily — Inline Strong's Alignment Loader (production)
//
// Lazily loads per-book alignment assets from assets/strong/alignment/.
// Uses a static literal require() map (inlineStrongsBookLoaders.js) so Metro
// can bundle every book file at build time — works offline on native and web.
// Only one book is loaded at a time; the cache holds at most a few books.

"use strict";

// Static loader map — every require() path is a literal string.
const { BOOK_LOADERS } = require("./inlineStrongsBookLoaders");

// Book name → file slug mapping (matches manifest file naming convention)
const BOOK_SLUGS = {
  "Genesis": "genesis",
  "Exodus": "exodus",
  "Leviticus": "leviticus",
  "Numbers": "numbers",
  "Deuteronomy": "deuteronomy",
  "Joshua": "joshua",
  "Judges": "judges",
  "Ruth": "ruth",
  "1 Samuel": "1_samuel",
  "2 Samuel": "2_samuel",
  "1 Kings": "1_kings",
  "2 Kings": "2_kings",
  "1 Chronicles": "1_chronicles",
  "2 Chronicles": "2_chronicles",
  "Ezra": "ezra",
  "Nehemiah": "nehemiah",
  "Esther": "esther",
  "Job": "job",
  "Psalms": "psalms",
  "Proverbs": "proverbs",
  "Ecclesiastes": "ecclesiastes",
  "Song of Solomon": "song_of_solomon",
  "Isaiah": "isaiah",
  "Jeremiah": "jeremiah",
  "Lamentations": "lamentations",
  "Ezekiel": "ezekiel",
  "Daniel": "daniel",
  "Hosea": "hosea",
  "Joel": "joel",
  "Amos": "amos",
  "Obadiah": "obadiah",
  "Jonah": "jonah",
  "Micah": "micah",
  "Nahum": "nahum",
  "Habakkuk": "habakkuk",
  "Zephaniah": "zephaniah",
  "Haggai": "haggai",
  "Zechariah": "zechariah",
  "Malachi": "malachi",
  "Matthew": "matthew",
  "Mark": "mark",
  "Luke": "luke",
  "John": "john",
  "Acts": "acts",
  "Romans": "romans",
  "1 Corinthians": "1_corinthians",
  "2 Corinthians": "2_corinthians",
  "Galatians": "galatians",
  "Ephesians": "ephesians",
  "Philippians": "philippians",
  "Colossians": "colossians",
  "1 Thessalonians": "1_thessalonians",
  "2 Thessalonians": "2_thessalonians",
  "1 Timothy": "1_timothy",
  "2 Timothy": "2_timothy",
  "Titus": "titus",
  "Philemon": "philemon",
  "Hebrews": "hebrews",
  "James": "james",
  "1 Peter": "1_peter",
  "2 Peter": "2_peter",
  "1 John": "1_john",
  "2 John": "2_john",
  "3 John": "3_john",
  "Jude": "jude",
  "Revelation": "revelation",
};

// Cache: bookName → book data (or null if missing)
const _cache = new Map();

/**
 * Get alignment segments for a specific verse.
 *
 * @param {string} book    - Book name (e.g., "Genesis")
 * @param {number} chapter - Chapter number
 * @param {number} verse   - Verse number
 * @returns {Array<Array<[string, string|null]>>|null}
 *   Array of [text, strongsId] segments, or null if no alignment available.
 *   null means the verse should render as plain text (fallback or missing).
 */
function getVerseSegments(book, chapter, verse) {
  if (!book || !chapter || !verse) return null;

  // Load book if not cached
  if (!_cache.has(book)) {
    const slug = BOOK_SLUGS[book];
    if (!slug) {
      _cache.set(book, null);
      return null;
    }
    // Use the static loader map — every require() path is a literal string
    const loadBook = BOOK_LOADERS[slug];
    if (!loadBook) {
      _cache.set(book, null);
      return null;
    }
    try {
      const bookData = loadBook();
      _cache.set(book, bookData);
    } catch (e) {
      // Book file missing or corrupt — cache null so we don't retry
      _cache.set(book, null);
      return null;
    }
  }

  const bookData = _cache.get(book);
  if (!bookData || !bookData.verses) return null;

  const verseKey = book + "|" + chapter + "|" + verse;
  return bookData.verses[verseKey] || null;
}

/**
 * Clear the cache (useful for testing).
 */
function clearInlineCache() {
  _cache.clear();
}

module.exports = { getVerseSegments, clearInlineCache, BOOK_SLUGS };