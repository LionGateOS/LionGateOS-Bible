#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "source", "growdaily");

const standardBible =
  require(path.join(ROOT, "assets/bible/en_kjv.json"));

const customBible =
  require(path.join(ROOT, "assets/bible/kjv_modified.json"));

const manifest =
  require(path.join(ROOT, "assets/strong/alignment/manifest.json"));

const customLoader =
  require(path.join(ROOT, "logic/customKjvInlineStrongs.js"));

const output =
  process.argv[2] || "/tmp/gdplus-projected-segments.json";

const clean = value =>
  String(
    typeof value === "string" ? value : value?.text || ""
  ).replace(/[{}]/g, "");

const verses = {};

let canonical = 0;
let projected = 0;
let fallback = 0;
let changed = 0;
let changedProjected = 0;
let strongsMarkers = 0;
let failures = 0;

for (let b = 0; b < manifest.books.length; b++) {
  const meta = manifest.books[b];
  const standardBook = standardBible[b];
  const customBook = customBible[b];

  for (let c = 0; c < standardBook.chapters.length; c++) {
    const standardChapter = standardBook.chapters[c];
    const customChapter = customBook.chapters[c];

    for (let v = 0; v < standardChapter.length; v++) {
      canonical++;

      const chapter = c + 1;
      const verse = v + 1;
      const ref = `${meta.book}|${chapter}|${verse}`;

      const standardText = clean(standardChapter[v]);
      const customText = clean(customChapter[v]);

      const isChanged = standardText !== customText;
      if (isChanged) changed++;

      const segments = customLoader.getVerseSegments(
        meta.book,
        chapter,
        verse,
        customText,
        standardText
      );

      if (!segments) {
        fallback++;
        continue;
      }

      const reconstructed =
        segments.map(segment => segment[0]).join("");

      if (reconstructed !== customText) {
        console.error("RECONSTRUCTION_FAILURE:", ref);
        failures++;
        continue;
      }

      for (const segment of segments) {
        if (
          !Array.isArray(segment) ||
          typeof segment[0] !== "string" ||
          !(
            segment[1] === null ||
            /^(H|G)\d+$/.test(segment[1])
          )
        ) {
          console.error("INVALID_SEGMENT:", ref);
          failures++;
          break;
        }

        if (segment[1]) strongsMarkers++;
      }

      verses[ref] = segments;
      projected++;

      if (isChanged) changedProjected++;
    }
  }
}

const stats = {
  canonicalVerses: canonical,
  projectedVerses: projected,
  plainFallbackVerses: fallback,
  changedCustomVerses: changed,
  changedProjectedVerses: changedProjected,
  strongsMarkers,
  failures,
};

if (canonical !== 31102) throw new Error("canonical count");
if (projected !== 31102) throw new Error("projected count");
if (fallback !== 0) throw new Error("fallback count");
if (changed !== 335) throw new Error("changed count");
if (changedProjected !== 335) throw new Error("changed projection count");
if (strongsMarkers !== 348902) throw new Error("marker count");
if (failures !== 0) throw new Error("projection failures");

fs.writeFileSync(
  output,
  JSON.stringify({
    schemaVersion: "1.0",
    translationId: "gd",
    sourceAlignmentSchema: "2.0",
    stats,
    verses,
  }) + "\n",
  "utf8"
);

console.log("CANONICAL=", canonical);
console.log("PROJECTED=", projected);
console.log("FALLBACK=", fallback);
console.log("CHANGED=", changed);
console.log("CHANGED_PROJECTED=", changedProjected);
console.log("STRONGS_MARKERS=", strongsMarkers);
console.log("FAILURES=", failures);
console.log("OUTPUT=", output);
console.log("GDPLUS_PROJECTION_GENERATOR=PASS");
