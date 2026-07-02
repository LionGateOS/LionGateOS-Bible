#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const ROOT = path.resolve(__dirname, "..");
const manifest = require("../assets/strong/alignment/manifest.json");
const standardBible = require("../assets/bible/en_kjv.json");
const customBible = require("../assets/bible/kjv_modified.json");
const standardLoader = require("../logic/inlineStrongsLoader");
const customLoader = require("../logic/customKjvInlineStrongs");

const clean = (value) =>
  String(
    typeof value === "string"
      ? value
      : value?.text || ""
  ).replace(/[{}]/g, "");

const stats = {
  books: 0,
  canonical: 0,
  aligned: 0,
  standardFallback: 0,
  customProjected: 0,
  customProjectionFallback: 0,
  changedAligned: 0,
};

const failures = [];

for (let bookIndex = 0; bookIndex < manifest.books.length; bookIndex++) {
  const meta = manifest.books[bookIndex];
  const standardBook = standardBible[bookIndex];
  const customBook = customBible[bookIndex];

  if (!standardBook || !customBook || !meta.file) {
    failures.push(`${meta.book}: missing Bible data or alignment file`);
    continue;
  }

  const filePath = path.resolve(
    ROOT,
    "assets/strong/alignment",
    meta.file
  );

  const raw = fs.readFileSync(filePath, "utf8");
  const checksum = crypto
    .createHash("sha256")
    .update(raw, "utf8")
    .digest("hex");

  if (checksum !== meta.checksum) {
    failures.push(`${meta.book}: checksum mismatch`);
  }

  const alignment = JSON.parse(raw);
  const alignedKeys = new Set(Object.keys(alignment.verses || {}));
  let bookCanonical = 0;
  let bookAligned = 0;

  const standardChapters = standardBook.chapters || [];
  const customChapters = customBook.chapters || [];

  if (standardChapters.length !== customChapters.length) {
    failures.push(`${meta.book}: chapter-count mismatch`);
  }

  for (
    let chapterIndex = 0;
    chapterIndex < standardChapters.length;
    chapterIndex++
  ) {
    const standardChapter = standardChapters[chapterIndex] || [];
    const customChapter = customChapters[chapterIndex] || [];

    if (standardChapter.length !== customChapter.length) {
      failures.push(
        `${meta.book} ${chapterIndex + 1}: verse-count mismatch`
      );
    }

    for (
      let verseIndex = 0;
      verseIndex < standardChapter.length;
      verseIndex++
    ) {
      bookCanonical++;
      stats.canonical++;

      const chapter = chapterIndex + 1;
      const verse = verseIndex + 1;
      const key = `${meta.book}|${chapter}|${verse}`;
      const standardText = clean(standardChapter[verseIndex]);
      const customText = clean(customChapter[verseIndex]);
      const storedSegments = alignment.verses[key] || null;
      const runtimeSegments = standardLoader.getVerseSegments(
        meta.book,
        chapter,
        verse
      );

      if (!storedSegments) {
        stats.standardFallback++;

        if (runtimeSegments !== null) {
          failures.push(`${key}: runtime loader returned unexpected data`);
        }

        continue;
      }

      bookAligned++;
      stats.aligned++;

      if (
        !runtimeSegments ||
        JSON.stringify(runtimeSegments) !==
          JSON.stringify(storedSegments)
      ) {
        failures.push(`${key}: runtime loader differs from stored data`);
      }

      const reconstructedStandard = storedSegments
        .map((segment) => segment[0])
        .join("");

      if (reconstructedStandard !== standardText) {
        failures.push(`${key}: standard text reconstruction mismatch`);
      }

      for (const segment of storedSegments) {
        if (
          !Array.isArray(segment) ||
          typeof segment[0] !== "string" ||
          !(
            segment[1] === null ||
            /^(H|G)\d+$/.test(segment[1])
          )
        ) {
          failures.push(`${key}: invalid alignment segment`);
          break;
        }
      }

      const changed = customText !== standardText;
      if (changed) stats.changedAligned++;

      const projected = customLoader.getVerseSegments(
        meta.book,
        chapter,
        verse,
        customText,
        standardText
      );

      if (!projected) {
        stats.customProjectionFallback++;

        if (!changed) {
          failures.push(`${key}: unchanged custom verse failed projection`);
        }

        continue;
      }

      stats.customProjected++;

      const reconstructedCustom = projected
        .map((segment) => segment[0])
        .join("");

      if (reconstructedCustom !== customText) {
        failures.push(`${key}: custom text reconstruction mismatch`);
      }

      if (
        changed &&
        reconstructedCustom === standardText
      ) {
        failures.push(`${key}: standard wording leaked into custom text`);
      }
    }
  }

  for (const key of alignedKeys) {
    if (!key.startsWith(meta.book + "|")) {
      failures.push(`${meta.book}: foreign alignment key ${key}`);
    }
  }

  if (bookCanonical !== meta.canonicalVerses) {
    failures.push(`${meta.book}: canonical total mismatch`);
  }

  if (bookAligned !== meta.aligned) {
    failures.push(`${meta.book}: aligned total mismatch`);
  }

  if (
    bookCanonical - bookAligned !== meta.fallback ||
    meta.missing !== 0
  ) {
    failures.push(`${meta.book}: fallback accounting mismatch`);
  }

  stats.books++;
}

if (
  stats.books !== 66 ||
  stats.canonical !== 31100 ||
  stats.aligned !== 26926 ||
  stats.standardFallback !== 4174
) {
  failures.push(
    "Full-Bible totals differ from the verified manifest totals"
  );
}

console.log("\n=== FULL-BIBLE INLINE STRONG'S RUNTIME AUDIT ===\n");
console.log("Books checked:              ", stats.books);
console.log("Canonical verses:           ", stats.canonical);
console.log("Standard aligned:           ", stats.aligned);
console.log("Standard plain fallbacks:   ", stats.standardFallback);
console.log("Changed aligned custom:     ", stats.changedAligned);
console.log("Custom projections:         ", stats.customProjected);
console.log("Custom projection fallbacks:", stats.customProjectionFallback);
console.log("Failures:                   ", failures.length);

if (failures.length) {
  console.log("\nFirst failures:");
  failures.slice(0, 30).forEach((failure) => {
    console.log(" - " + failure);
  });
  process.exit(1);
}

console.log("\nPASS: all 66 books and 31,100 verses verified.");
console.log("PASS: no standard wording replaced custom wording.");
console.log("PASS: all fallback paths were explicit and safe.");
