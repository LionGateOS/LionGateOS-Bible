#!/usr/bin/env node
/**
 * buildStrongsAlignment.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Generates precise English word-to-Strong's alignment for GrowDaily's
 * LionGateOS Custom KJV using the same kaiserlik/kjv source data.
 *
 * Unlike the existing buildStrongsMapping.js which only preserves sequential
 * Strong's IDs, this generator:
 * - Preserves English text context around each Strong's marker
 * - Determines exact word/phrase boundaries where possible
 * - Classifies confidence levels for each alignment
 * - Falls back safely for text mismatches
 *
 * Source:
 *   https://github.com/kaiserlik/kjv  (public domain KJV + Strong's inline)
 *
 * Output:
 *   /tmp/growdaily-strongs-alignment-preview.json
 *
 * Output schema:
 *   {
 *     "schemaVersion": "1.0",
 *     "translationId": "kjv_custom",
 *     "generated": "ISO timestamp",
 *     "verses": {
 *       "Genesis|1|1": {
 *         "exactTextMatch": true,
 *         "displayText": "In the beginning God created the heaven and the earth.",
 *         "segments": [
 *           {
 *             "text": "In the beginning",
 *             "strongs": ["H7225"],
 *             "segmentIndex": 0,
 *             "supplied": false,
 *             "confidence": "exact-single-token"
 *           }
 *         ]
 *       }
 *     }
 *   }
 * ─────────────────────────────────────────────────────────────────────────────
 */

"use strict";

const fs = require("fs");
const path = require("path");

// ── book table ────────────────────────────────────────────────────────────────
// Maps kaiserlik file codes → canonical app book names.
const BOOKS = [
  { code: "Gen",  app: "Genesis" },
  { code: "Exo",  app: "Exodus" },
  { code: "Lev",  app: "Leviticus" },
  { code: "Num",  app: "Numbers" },
  { code: "Deu",  app: "Deuteronomy" },
  { code: "Jos",  app: "Joshua" },
  { code: "Jdg",  app: "Judges" },
  { code: "Rth",  app: "Ruth" },
  { code: "1Sa",  app: "1 Samuel" },
  { code: "2Sa",  app: "2 Samuel" },
  { code: "1Ki",  app: "1 Kings" },
  { code: "2Ki",  app: "2 Kings" },
  { code: "1Ch",  app: "1 Chronicles" },
  { code: "2Ch",  app: "2 Chronicles" },
  { code: "Ezr",  app: "Ezra" },
  { code: "Neh",  app: "Nehemiah" },
  { code: "Est",  app: "Esther" },
  { code: "Job",  app: "Job" },
  { code: "Psa",  app: "Psalms" },
  { code: "Pro",  app: "Proverbs" },
  { code: "Ecc",  app: "Ecclesiastes" },
  { code: "Sng",  app: "Song of Solomon" },
  { code: "Isa",  app: "Isaiah" },
  { code: "Jer",  app: "Jeremiah" },
  { code: "Lam",  app: "Lamentations" },
  { code: "Eze",  app: "Ezekiel" },
  { code: "Dan",  app: "Daniel" },
  { code: "Hos",  app: "Hosea" },
  { code: "Joe",  app: "Joel" },
  { code: "Amo",  app: "Amos" },
  { code: "Oba",  app: "Obadiah" },
  { code: "Jon",  app: "Jonah" },
  { code: "Mic",  app: "Micah" },
  { code: "Nah",  app: "Nahum" },
  { code: "Hab",  app: "Habakkuk" },
  { code: "Zep",  app: "Zephaniah" },
  { code: "Hag",  app: "Haggai" },
  { code: "Zec",  app: "Zechariah" },
  { code: "Mal",  app: "Malachi" },
  { code: "Mat",  app: "Matthew" },
  { code: "Mar",  app: "Mark" },
  { code: "Luk",  app: "Luke" },
  { code: "Jhn",  app: "John" },
  { code: "Act",  app: "Acts" },
  { code: "Rom",  app: "Romans" },
  { code: "1Co",  app: "1 Corinthians" },
  { code: "2Co",  app: "2 Corinthians" },
  { code: "Gal",  app: "Galatians" },
  { code: "Eph",  app: "Ephesians" },
  { code: "Phl",  app: "Philippians" },
  { code: "Col",  app: "Colossians" },
  { code: "1Th",  app: "1 Thessalonians" },
  { code: "2Th",  app: "2 Thessalonians" },
  { code: "1Ti",  app: "1 Timothy" },
  { code: "2Ti",  app: "2 Timothy" },
  { code: "Tit",  app: "Titus" },
  { code: "Phm",  app: "Philemon" },
  { code: "Heb",  app: "Hebrews" },
  { code: "Jas",  app: "James" },
  { code: "1Pe",  app: "1 Peter" },
  { code: "2Pe",  app: "2 Peter" },
  { code: "1Jo",  app: "1 John" },
  { code: "2Jo",  app: "2 John" },
  { code: "3Jo",  app: "3 John" },
  { code: "Jde",  app: "Jude" },
  { code: "Rev",  app: "Revelation" },
];

const BASE_URL = "https://raw.githubusercontent.com/kaiserlik/kjv/main";
const STRONGS_RE = /\[([HG]\d+)\]/g;

// ── helpers ───────────────────────────────────────────────────────────────────

/**
 * Clean Kaiserlik text by removing Strong's markers and HTML tags
 * while preserving visible text content.
 */
function cleanKaiserlikText(text) {
  if (!text) return "";

  // Remove Strong's markers [H####] or [G####]
  let clean = text.replace(/\[([HG]\d+)\]/g, "");

  // Remove HTML tags but preserve their content
  // e.g., "<em>was</em>" becomes "was"
  clean = clean.replace(/<[^>]+>/g, "");

  // Normalize whitespace
  clean = clean.replace(/\s+/g, " ").trim();

  return clean;
}

/**
 * Extract all text segments from annotated English text.
 * This properly handles consecutive markers and trailing text.
 */
function extractAllTextSegments(enText) {
  const segments = [];
  let lastIndex = 0;
  let segmentIndex = 0;
  let match;
  const regex = /\[([HG]\d+)\]/g;

  // Find all Strong's markers and extract segments
  while ((match = regex.exec(enText)) !== null) {
    // Extract text before this marker
    const beforeText = enText.substring(lastIndex, match.index);
    segments.push({
      text: beforeText,
      strongsId: match[1],
      segmentIndex: segmentIndex++,
      position: lastIndex
    });

    lastIndex = match.index + match[0].length;
  }

  // Add any trailing text after the last marker
  const trailingText = enText.substring(lastIndex);
  if (trailingText) {
    segments.push({
      text: trailingText,
      strongsId: null,
      segmentIndex: segmentIndex++,
      position: lastIndex
    });
  }

  return segments;
}

/**
 * Determine if text contains HTML supplied-word markers.
 */
function hasSuppliedWords(text) {
  return /<[^>]+>/g.test(text);
}

/**
 * Classify confidence level for a Strong's annotation based on context.
 */
function classifyConfidence(text, strongsId) {
  if (!strongsId) {
    // This is trailing text or text without a Strong's number
    return "trailing-text";
  }

  if (!text || !text.trim()) {
    return "zero-length";
  }

  // Split into words
  const words = text.trim().split(/\s+/).filter(w => w.length > 0);

  if (words.length === 0) {
    return "zero-length";
  } else if (words.length === 1) {
    return "exact-single-token";
  } else if (words.length <= 3) {
    // Check if it's a clear phrase like "without form,"
    const lastWord = words[words.length - 1];
    if (/[,:;.]$/.test(lastWord)) {
      return "high-confidence-phrase";
    }
    return "ambiguous";
  } else {
    return "ambiguous";
  }
}

/**
 * Parse one book's JSON blob into our alignment structure.
 */
function parseBookForAlignment(data, bookCode, customKjvVerses) {
  // Use the first available key — some books use code ("Gen"), others full name
  const topKey = Object.keys(data)[0];
  const bookData = data[topKey];
  if (!bookData) throw new Error("No key " + bookCode + " in downloaded data");

  const results = {};
  let verseCount = 0;
  let alignedCount = 0;

  // Track which canonical keys we've already processed to avoid duplicates
  const processedKeys = new Set();

  for (const chKey of Object.keys(bookData)) {
    // chKey = "Gen|1"
    const chNum = chKey.split("|")[1];
    if (!chNum) continue;

    const chObj = bookData[chKey];

    for (const vKey of Object.keys(chObj)) {
      // vKey = "Gen|1|1"
      const vNum = vKey.split("|")[2];
      if (!vNum) continue;

      const enText = chObj[vKey]?.en || "";

      // Convert to canonical key format
      const canonicalKey = BOOKS.find(b => b.code === bookCode).app + "|" + chNum + "|" + vNum;

      // Skip if we already processed this verse (to avoid duplicates)
      if (processedKeys.has(canonicalKey)) {
        continue;
      }

      // Mark this key as processed
      processedKeys.add(canonicalKey);
      verseCount++;

      // Get corresponding Custom KJV verse
      const customKjvText = customKjvVerses.get(canonicalKey);

      if (!customKjvText) {
        // No corresponding verse in Custom KJV
        results[canonicalKey] = {
          exactTextMatch: false,
          fallbackReason: "missing-in-custom-kjv"
        };
        continue;
      }

      // Clean the Kaiserlik text for comparison
      const cleanKaiserlik = cleanKaiserlikText(enText);

      // Check for exact text match
      if (cleanKaiserlik === customKjvText) {
        // Text matches - we can generate alignment
        const allSegments = extractAllTextSegments(enText);
        const allOrderedSegments = [];

        if (allSegments.length > 0) {
          // Process ALL segments to preserve text for reconstruction
          let reconstructedText = "";

          for (let i = 0; i < allSegments.length; i++) {
            const segment = allSegments[i];

            // Create a segment for text reconstruction (includes all text)
            // For reconstruction, we need to preserve the original text structure
            const originalText = segment.text;
            const cleanedText = cleanKaiserlikText(segment.text);

            // Add to reconstructed text to verify we can rebuild the original
            reconstructedText += originalText;

            allOrderedSegments.push({
              text: originalText, // Store original text for display
              cleanText: cleanedText, // Store cleaned text for reference
              strongs: segment.strongsId ? [segment.strongsId] : [],
              segmentIndex: segment.segmentIndex,
              supplied: /<[^>]+>/.test(segment.text),
              confidence: classifyConfidence(cleanedText, segment.strongsId)
            });
          }

          // Verify that when we clean the reconstructed text, it matches the custom KJV text
          const cleanedReconstructed = cleanKaiserlikText(reconstructedText);
          if (cleanedReconstructed !== customKjvText) {
            // If there's a mismatch, use fallback
            results[canonicalKey] = {
              exactTextMatch: false,
              displayText: customKjvText,
              fallbackReason: "text-mismatch"
            };
            continue;
          }

          alignedCount++;
        }

        results[canonicalKey] = {
          exactTextMatch: true,
          displayText: customKjvText,
          segments: allOrderedSegments // Store ALL segments for reconstruction
        };
      } else {
        // Text doesn't match - use verse-level fallback
        results[canonicalKey] = {
          exactTextMatch: false,
          displayText: customKjvText,
          fallbackReason: "text-mismatch"
        };
      }
    }
  }

  return { results, verseCount, alignedCount };
}
/**
 * Fallback parser for malformed JSON files.
 */
function parseRawFallback(rawText, code) {
  // Match verse keys like "Gen|1|1" or "1Sa|1|1" and their "en" values.
  const VERSE_RE = /"([A-Za-z0-9]+\|(\d+)\|(\d+))"[^{]*{[^"]*"en"\s*:\s*"((?:[^"\\]|\\.)*)"/g;
  const result = {};
  let m;
  while ((m = VERSE_RE.exec(rawText)) !== null) {
    const [, vKey,, , enText] = m;
    // vKey = "1Sa|1|1" — extract chapter portion as top-level group key
    const parts = vKey.split("|");
    const bookCode = parts[0];
    const chKey = bookCode + "|" + parts[1];
    if (!result[bookCode]) result[bookCode] = {};   // use code as top key
    if (!result[bookCode][chKey]) result[bookCode][chKey] = {};
    result[bookCode][chKey][vKey] = { en: enText.replace(/\\"/g, '"') };
  }
  // Wrap in outer object matching kaiserlik's shape
  const outerKey = Object.keys(result)[0] || code;
  return { [outerKey]: result[outerKey] || {} };
}

/** Simple rate-limited fetch with retry, with JSON fallback for malformed files. */
async function fetchWithRetry(url, retries = 3) {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error("HTTP " + res.status);
      const rawText = await res.text();
      try {
        return JSON.parse(rawText);
      } catch {
        // JSON is malformed (unescaped quotes in non-en fields) — use regex fallback
        process.stdout.write("(fallback) ");
        return parseRawFallback(rawText, url.split("/").pop().replace(".json", ""));
      }
    } catch (err) {
      if (attempt === retries) throw err;
      await new Promise(r => setTimeout(r, 1000 * attempt));
    }
  }
}

// ── main ──────────────────────────────────────────────────────────────────────

async function main() {
  console.log("Building precise Strong's alignment for GrowDaily LionGateOS Custom KJV…\n");

  // Load Custom KJV for text comparison
  const kjvModifiedPath = path.resolve(__dirname, "..", "assets", "bible", "kjv_modified.json");
  const kjvModified = JSON.parse(fs.readFileSync(kjvModifiedPath, "utf8"));

  // Flatten Custom KJV into canonical map
  function flattenCustomKjv() {
    const verseMap = new Map();
    const bookNames = [
      "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges", "Ruth",
      "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah",
      "Esther", "Job", "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah",
      "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah",
      "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi", "Matthew", "Mark", "Luke",
      "John", "Acts", "Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians",
      "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy",
      "Titus", "Philemon", "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John", "3 John",
      "Jude", "Revelation"
    ];

    kjvModified.forEach((book, bookIndex) => {
      const bookName = bookNames[bookIndex] || book.name || book.abbrev;
      if (book.chapters) {
        book.chapters.forEach((chapter, chapterIndex) => {
          const chapterNum = chapterIndex + 1;
          if (Array.isArray(chapter)) {
            chapter.forEach((verse, verseIndex) => {
              const verseNum = verseIndex + 1;
              const verseKey = bookName + "|" + chapterNum + "|" + verseNum;
              verseMap.set(verseKey, verse);
            });
          }
        });
      }
    });

    return verseMap;
  }

  const customKjvVerses = flattenCustomKjv();
  console.log("Loaded " + customKjvVerses.size + " Custom KJV verses for comparison\n");

  // Output structure
  const output = {
    schemaVersion: "1.0",
    translationId: "kjv_custom",
    generated: new Date().toISOString(),
    source: "https://github.com/kaiserlik/kjv",
    verses: {}
  };

  let totalVerses = 0;
  let totalAligned = 0;

  // Process each book
  for (let i = 0; i < BOOKS.length; i++) {
    const { code, app } = BOOKS[i];
    const url = BASE_URL + "/" + code + ".json";
    process.stdout.write("[" + String(i + 1).padStart(2, "0") + "/" + BOOKS.length + "] " + app.padEnd(22, " "));

    let data;
    try {
      data = await fetchWithRetry(url);
    } catch (err) {
      console.error("FAILED: " + err.message);
      continue;
    }

    const { results, verseCount, alignedCount } = parseBookForAlignment(data, code, customKjvVerses);

    // Merge results, ensuring we only include verses that exist in Custom KJV
    // and we don't overwrite existing entries
    for (const [key, value] of Object.entries(results)) {
      // Only include verses that exist in the canonical Custom KJV
      if (customKjvVerses.has(key) && !output.verses.hasOwnProperty(key)) {
        output.verses[key] = value;
      }
    }

    totalVerses += verseCount;
    totalAligned += alignedCount;
    const pct = ((alignedCount / verseCount) * 100).toFixed(0);
    console.log(verseCount + " verses  " + alignedCount + " aligned (" + pct + "%)");
  }

  // ── write output ────────────────────────────────────────────────────────────
  // Ensure all Custom KJV verses are included in output
  // Some verses may be missing from Kaiserlik data, so we add them as fallbacks
  for (const [verseKey, customKjvText] of customKjvVerses) {
    if (!output.verses.hasOwnProperty(verseKey)) {
      output.verses[verseKey] = {
        exactTextMatch: false,
        displayText: customKjvText,
        fallbackReason: "missing-in-source"
      };
    }
  }
  const outFile = "/tmp/growdaily-strongs-alignment-preview.json";
  const json = JSON.stringify(output, null, 2);
  fs.writeFileSync(outFile, json, "utf8");
  const mb = (Buffer.byteLength(json, "utf8") / 1024 / 1024).toFixed(2);

  console.log("\nTotal verses processed: " + totalVerses.toLocaleString());
  console.log("Unique verses in output: " + Object.keys(output.verses).length.toLocaleString());
  console.log("Aligned verses:         " + totalAligned.toLocaleString() + " (" + ((totalAligned/totalVerses)*100).toFixed(1) + "%)");
  console.log("Output:                 " + outFile + "  (" + mb + " MB)");

  // ── spot-check ───────────────────────────────────────────────────────────────
  console.log("\n── Spot-checks ──────────────────────────────────────────────");
  const checks = [
    { key: "Genesis|1|1", label: "Gen 1:1" },
    { key: "Genesis|1|2", label: "Gen 1:2" },
    { key: "John|1|1", label: "John 1:1" },
    { key: "Acts|12|4", label: "Acts 12:4" },
  ];

  for (const { key, label } of checks) {
    const verse = output.verses[key];
    if (!verse) {
      console.log("  " + label + "  → NO DATA");
    } else if (!verse.exactTextMatch) {
      console.log("  " + label + "  → FALLBACK (" + verse.fallbackReason + ")");
    } else {
      const segments = verse.segments || [];
      const preview = segments.slice(0, 3).map(s => s.text + (s.strongs.length > 0 ? "[" + s.strongs[0] + "]" : "")).join(", ");
      console.log("  " + label);
      console.log("    " + segments.length + " segments: " + preview + (segments.length > 3 ? " …" : ""));
    }
  }

  console.log("\nDone.\n");
}

if (require.main === module) {
  main().catch(err => {
    console.error("\nFatal:", err.message);
    process.exit(1);
  });
}

module.exports = { cleanKaiserlikText, extractAllTextSegments, classifyConfidence };