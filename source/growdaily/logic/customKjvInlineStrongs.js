"use strict";

// Conservatively projects standard-KJV Strong's relationships onto custom-KJV
// text. Exact matching words may retain an ID. Changed, inserted, deleted, or
// ambiguous repeated words remain unnumbered.

function tokenizeWithPositions(text) {
  const tokens = [];
  const regex = /\S+/g;
  let match;

  while ((match = regex.exec(text)) !== null) {
    tokens.push({
      text: match[0],
      start: match.index,
      end: match.index + match[0].length,
    });
  }

  return tokens;
}

function buildStandardTokenMap(segments) {
  if (!Array.isArray(segments)) return null;

  let text = "";
  const ranges = [];

  for (let index = 0; index < segments.length; index++) {
    const segment = segments[index];

    if (!Array.isArray(segment) || typeof segment[0] !== "string") {
      return null;
    }

    const segmentText = segment[0];
    const strongsId =
      typeof segment[1] === "string" && segment[1]
        ? segment[1]
        : null;

    const start = text.length;
    text += segmentText;
    const end = text.length;

    // Zero-length markers are preserved only by the exact-text fast path.
    if (end > start) {
      ranges.push({ start, end, strongsId });
    }
  }

  const tokens = tokenizeWithPositions(text).map((token) => {
    const values = new Set();

    for (const range of ranges) {
      const overlaps =
        token.start < range.end &&
        token.end > range.start;

      if (overlaps) {
        values.add(range.strongsId);
      }
    }

    return {
      ...token,
      strongsId:
        values.size === 1
          ? [...values][0]
          : null,
    };
  });

  return { text, tokens };
}

function buildLcsPairs(standardTokens, customTokens) {
  const rows = standardTokens.length + 1;
  const cols = customTokens.length + 1;
  const table = Array.from(
    { length: rows },
    () => Array(cols).fill(0)
  );

  for (let i = 1; i < rows; i++) {
    for (let j = 1; j < cols; j++) {
      if (standardTokens[i - 1].text === customTokens[j - 1].text) {
        table[i][j] = table[i - 1][j - 1] + 1;
      } else {
        table[i][j] = Math.max(
          table[i - 1][j],
          table[i][j - 1]
        );
      }
    }
  }

  const pairs = [];
  let i = standardTokens.length;
  let j = customTokens.length;

  while (i > 0 && j > 0) {
    if (standardTokens[i - 1].text === customTokens[j - 1].text) {
      pairs.unshift({
        standardIndex: i - 1,
        customIndex: j - 1,
      });
      i--;
      j--;
    } else if (table[i - 1][j] >= table[i][j - 1]) {
      i--;
    } else {
      j--;
    }
  }

  return pairs;
}

function countTokenTexts(tokens) {
  const counts = new Map();

  for (const token of tokens) {
    counts.set(token.text, (counts.get(token.text) || 0) + 1);
  }

  return counts;
}

function projectSegments(stdText, customText, stdSegments) {
  if (
    typeof stdText !== "string" ||
    typeof customText !== "string"
  ) {
    return null;
  }

  const standard = buildStandardTokenMap(stdSegments);

  if (!standard || standard.text !== stdText) {
    return null;
  }

  // Preserve every original segment and zero-length marker when unchanged.
  if (customText === stdText) {
    return stdSegments;
  }

  const customTokens = tokenizeWithPositions(customText);

  if (!standard.tokens.length || !customTokens.length) {
    return null;
  }

  const pairs = buildLcsPairs(standard.tokens, customTokens);
  const standardCounts = countTokenTexts(standard.tokens);
  const customCounts = countTokenTexts(customTokens);
  const customIds = new Array(customTokens.length).fill(null);

  for (const pair of pairs) {
    const source = standard.tokens[pair.standardIndex];
    const target = customTokens[pair.customIndex];

    // Repeated words are ambiguous after a textual change. Leave them null.
    if (
      standardCounts.get(source.text) === 1 &&
      customCounts.get(target.text) === 1
    ) {
      customIds[pair.customIndex] = source.strongsId;
    }
  }

  const projected = [];
  let cursor = 0;

  for (let index = 0; index < customTokens.length; index++) {
    const token = customTokens[index];
    projected.push([
      customText.slice(cursor, token.end),
      customIds[index],
    ]);
    cursor = token.end;
  }

  if (cursor < customText.length) {
    projected.push([customText.slice(cursor), null]);
  }

  const reconstructed = projected
    .map((segment) => segment[0])
    .join("");

  return reconstructed === customText
    ? projected
    : null;
}

function getVerseSegments(
  book,
  chapter,
  verse,
  customText,
  stdText
) {
  const {
    getVerseSegments: getStandardSegments,
  } = require("./inlineStrongsLoader.js");

  const standardSegments =
    getStandardSegments(book, chapter, verse);

  if (!standardSegments) return null;

  return projectSegments(
    stdText,
    customText,
    standardSegments
  );
}

function clearInlineCache() {
  // This adapter does not cache projected verses.
}

module.exports = {
  getVerseSegments,
  clearInlineCache,
  _test: {
    tokenizeWithPositions,
    buildStandardTokenMap,
    buildLcsPairs,
    projectSegments,
  },
};
