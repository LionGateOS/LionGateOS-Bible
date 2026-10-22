"use strict";

// Conservatively projects standard-KJV Strong's relationships onto custom-KJV
// text. Exact matching words may retain an ID. Changed, inserted, deleted, or
// ambiguous repeated words remain unnumbered.

function tokenizeWithPositions(text) {
  const tokens = [];
  const regex = /\S+/g;
  let match;

  while ((match = regex.exec(text)) !== null) {
    const lexicalWords = Array.from(
      match[0].matchAll(/[^\W_]+(?:['’\-][^\W_]+)*/gu)
    );
    const hasSingleWord = lexicalWords.length === 1;
    const word = hasSingleWord ? lexicalWords[0] : null;

    tokens.push({
      text: match[0],
      matchText: hasSingleWord ? word[0] : match[0],
      matchStart: hasSingleWord ? word.index : null,
      matchEnd: hasSingleWord ? word.index + word[0].length : null,
      start: match.index,
      end: match.index + match[0].length,
    });
  }

  return tokens;
}

function tokenMatchText(token) {
  return token.matchText || token.text;
}

function buildStandardTokenMap(segments) {
  if (!Array.isArray(segments)) return null;

  let text = "";
  const markerByWord = new Map();

  for (const segment of segments) {
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
    const segmentEnd = text.length;

    if (!strongsId) continue;

    const words = Array.from(
      segmentText.matchAll(/[^\W_]+(?:['’\-][^\W_]+)*/gu)
    );

    if (!words.length) continue;

    const word = words[words.length - 1];
    const wordStart = start + word.index;
    const wordEnd = wordStart + word[0].length;
    const key = `${wordStart}:${wordEnd}`;

    if (
      markerByWord.has(key) &&
      markerByWord.get(key)?.strongsId !== strongsId
    ) {
      markerByWord.set(key, null);
    } else if (!markerByWord.has(key)) {
      markerByWord.set(key, {
        start: wordStart,
        end: wordEnd,
        boundary: segmentEnd,
        strongsId,
      });
    }
  }

  const tokens = tokenizeWithPositions(text).map((token) => {
    const words = Array.from(
      token.text.matchAll(/[^\W_]+(?:['’\-][^\W_]+)*/gu)
    );

    if (words.length !== 1) {
      return { ...token, strongsId: null, markers: [] };
    }

    const word = words[0];
    const wordStart = token.start + word.index;
    const wordEnd = wordStart + word[0].length;
    const markers = [];

    for (const marker of markerByWord.values()) {
      if (
        marker &&
        marker.start >= wordStart &&
        marker.end <= wordEnd
      ) {
        markers.push({
          start: marker.start - wordStart,
          end: Math.min(marker.boundary, wordEnd) - wordStart,
          strongsId: marker.strongsId,
        });
      }
    }

    markers.sort((a, b) => a.end - b.end || a.start - b.start);

    const fullWordMarker =
      markers.length === 1 &&
      markers[0].start === 0 &&
      markers[0].end === word[0].length;

    return {
      ...token,
      strongsId: fullWordMarker ? markers[0].strongsId : null,
      markers,
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
      if (
        tokenMatchText(standardTokens[i - 1]) ===
        tokenMatchText(customTokens[j - 1])
      ) {
        table[i][j] = table[i - 1][j - 1] + 1;
      } else {
        table[i][j] = Math.max(
          table[i - 1][j],
          table[i][j - 1]
        );
      }
    }
  }

  // Work backwards too, so only forced, unambiguous word matches
  // can inherit a Strong's ID.
  const suffix = Array.from(
    { length: rows },
    () => Array(cols).fill(0)
  );

  for (let i = standardTokens.length - 1; i >= 0; i--) {
    for (let j = customTokens.length - 1; j >= 0; j--) {
      if (
        tokenMatchText(standardTokens[i]) ===
        tokenMatchText(customTokens[j])
      ) {
        suffix[i][j] = suffix[i + 1][j + 1] + 1;
      } else {
        suffix[i][j] = Math.max(
          suffix[i + 1][j],
          suffix[i][j + 1]
        );
      }
    }
  }

  const length = table[rows - 1][cols - 1];
  const safeMatches = new Map();

  for (let j = 0; j < customTokens.length; j++) {
    let bestWithoutTarget = 0;

    for (let i = 0; i < rows; i++) {
      bestWithoutTarget = Math.max(
        bestWithoutTarget,
        table[i][j] + suffix[i][j + 1]
      );
    }

    // If the target word can be skipped in an optimal alignment,
    // its source association is not certain.
    if (bestWithoutTarget >= length) continue;

    const candidates = [];

    for (let i = 0; i < standardTokens.length; i++) {
      if (
        tokenMatchText(standardTokens[i]) ===
          tokenMatchText(customTokens[j]) &&
        table[i][j] + 1 + suffix[i + 1][j + 1] === length
      ) {
        candidates.push(i);
      }
    }

    if (candidates.length === 1) {
      safeMatches.set(j, candidates[0]);
    }
  }

  const pairs = [];
  let i = standardTokens.length;
  let j = customTokens.length;

  while (i > 0 && j > 0) {
    if (
      tokenMatchText(standardTokens[i - 1]) ===
      tokenMatchText(customTokens[j - 1])
    ) {
      pairs.unshift({
        standardIndex: i - 1,
        customIndex: j - 1,
        safe: safeMatches.get(j - 1) === i - 1,
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
    const value = tokenMatchText(token);
    counts.set(value, (counts.get(value) || 0) + 1);
  }

  return counts;
}

const EXPLICIT_PHRASE_EQUIVALENTS = Object.freeze({
  "Genesis|1|1": {
    source: "heaven",
    replacement: ["heavens"],
    strongsId: "H8064",
  },
  "Job|39|9": {
    source: "unicorn",
    replacement: ["wild", "ox"],
    strongsId: "H7214",
  },
  "Job|39|10": {
    source: "unicorn",
    replacement: ["wild", "ox"],
    strongsId: "H7214",
  },
  "Matthew|12|40": {
    source: "whale's",
    replacement: ["great", "fish's"],
    strongsId: "G2785",
  },
  "Luke|17|21": {
    source: "within",
    replacement: ["in", "the", "midst", "of"],
    strongsId: "G1787",
  },
  "Acts|10|42": {
    source: "quick",
    replacement: ["the", "living"],
    strongsId: "G2198",
  },
});

function projectSegments(
  stdText,
  customText,
  stdSegments,
  verseKey = null
) {
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
  const customIds = new Array(customTokens.length).fill(null);
  const customMarkers = new Array(customTokens.length).fill(null);

  for (const pair of pairs) {
    if (!pair.safe) continue;

    const source = standard.tokens[pair.standardIndex];
    customIds[pair.customIndex] = source.strongsId;
    customMarkers[pair.customIndex] = source.markers || [];
  }

  // Apply only explicitly verified, verse-specific phrase replacements.
  // The complete replacement phrase receives one Strong's marker.
  const phraseGroups = new Map();
  const phraseRule = verseKey
    ? EXPLICIT_PHRASE_EQUIVALENTS[verseKey]
    : null;

  if (phraseRule) {
    let phraseOccurrences = 0;

    for (
      let start = 0;
      start <= customTokens.length - phraseRule.replacement.length;
      start++
    ) {
      if (
        phraseRule.replacement.every(
          (word, offset) =>
            tokenMatchText(customTokens[start + offset]) === word
        )
      ) {
        phraseOccurrences++;
      }
    }

    // Never apply a phrase rule if the target phrase is ambiguous.
    if (phraseOccurrences === 1) {
      const boundaries = [
        { standardIndex: -1, customIndex: -1 },
        ...pairs,
        {
          standardIndex: standard.tokens.length,
          customIndex: customTokens.length,
        },
      ];

      for (
        let gapIndex = 1;
        gapIndex < boundaries.length;
        gapIndex++
      ) {
        const previous = boundaries[gapIndex - 1];
        const next = boundaries[gapIndex];

        const sourceGap = standard.tokens.slice(
          previous.standardIndex + 1,
          next.standardIndex
        );

        const targetStart = previous.customIndex + 1;
        const targetEnd = next.customIndex;
        const targetGap = customTokens.slice(
          targetStart,
          targetEnd
        );

        if (
          sourceGap.length === 1 &&
          targetGap.length === phraseRule.replacement.length &&
          tokenMatchText(sourceGap[0]) === phraseRule.source &&
          sourceGap[0].strongsId === phraseRule.strongsId &&
          standardCounts.get(phraseRule.source) === 1 &&
          phraseRule.replacement.every(
            (word, offset) =>
              tokenMatchText(targetGap[offset]) === word
          )
        ) {
          phraseGroups.set(targetStart, {
            endIndex: targetEnd,
            strongsId: phraseRule.strongsId,
          });
          break;
        }
      }
    }
  }

  const projected = [];
  let cursor = 0;

  for (let index = 0; index < customTokens.length;) {
    const token = customTokens[index];
    const phraseGroup = phraseGroups.get(index);

    if (phraseGroup) {
      const lastToken = customTokens[phraseGroup.endIndex - 1];

      projected.push([
        customText.slice(cursor, lastToken.end),
        phraseGroup.strongsId,
      ]);

      cursor = lastToken.end;
      index = phraseGroup.endIndex;
      continue;
    }

    const markers = customMarkers[index] || [];
    const hasSubwordMarkers =
      markers.length > 1 ||
      markers.some(
        (marker) =>
          marker.start !== 0 ||
          marker.end !== tokenMatchText(token).length
      );

    if (hasSubwordMarkers && Number.isInteger(token.matchStart)) {
      const markerPoints = markers
        .filter((marker) => marker.strongsId)
        .map((marker) => ({
          position: token.start + token.matchStart + marker.end,
          strongsId: marker.strongsId,
        }))
        .filter(
          (marker) =>
            marker.position >= cursor &&
            marker.position <= token.end
        )
        .sort((a, b) => a.position - b.position);

      if (markerPoints.length) {
        for (const marker of markerPoints) {
          projected.push([
            customText.slice(cursor, marker.position),
            marker.strongsId,
          ]);
          cursor = marker.position;
        }

        if (cursor < token.end) {
          projected.push([customText.slice(cursor, token.end), null]);
          cursor = token.end;
        }

        index++;
        continue;
      }
    }

    projected.push([
      customText.slice(cursor, token.end),
      customIds[index],
    ]);

    cursor = token.end;
    index++;
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
    standardSegments,
    `${book}|${chapter}|${verse}`
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
