"use strict";

const assert = require("node:assert/strict");
const logic = require("../source/growdaily/logic/customKjvInlineStrongs.js");

const tests = [];

function test(name, run) {
  tests.push({ name, run });
}

function markedWords(segments) {
  const result = [];

  for (const [surface, id] of segments) {
    if (!id) continue;

    const words = Array.from(
      surface.matchAll(/[\p{L}\p{N}]+(?:['’\-][\p{L}\p{N}]+)*/gu),
      match => match[0]
    );

    assert.ok(
      words.length > 0,
      `Strong's ID ${id} has no lexical word in ${JSON.stringify(surface)}`
    );

    result.push([words[words.length - 1], id]);
  }

  return result;
}

function project(ref, standard, custom, sourceSegments) {
  const result = logic._test.projectSegments(
    standard, custom, sourceSegments, ref
  );

  assert.ok(result, `Projection returned no result for ${ref}`);
  assert.equal(
    result.map(segment => segment[0]).join(""),
    custom,
    `Custom wording was not reconstructed exactly for ${ref}`
  );

  return markedWords(result);
}

test("Genesis 1:1 — marker belongs to the final word of each source segment", () => {
  const standard = "In the beginning God created the heaven and the earth.";
  const custom = "In the beginning God created the heavens and the earth.";

  const segments = [
    ["In the beginning", "H7225"],
    [" God", "H0430"],
    [" created", "H1254"],
    [" the heaven", "H8064"],
    [" and", "H0853"],
    [" the earth", "H0776"],
    [".", null],
  ];

  assert.deepEqual(project("Genesis|1|1", standard, custom, segments), [
    ["beginning", "H7225"],
    ["God", "H0430"],
    ["created", "H1254"],
    ["heavens", "H8064"],
    ["and", "H0853"],
    ["earth", "H0776"],
  ]);
});

test("Genesis 1:2 — preserve associations across punctuation and repeated words", () => {
  const standard =
    "And the earth was without form, and void; and darkness was upon the face of the deep. And the Spirit of God moved upon the face of the waters.";
  const custom =
    "And the earth became without form, and void; and darkness was upon the face of the deep. And the Spirit of God moved upon the face of the waters.";

  const segments = [
    ["And the earth", "H0776"],
    [" was", "H1961"],
    [" without form", "H8414"],
    [", and void", "H0922"],
    ["; and darkness", "H2822"],
    [" was upon the face", "H6440"],
    [" of the deep", "H8415"],
    [". And the Spirit", "H7307"],
    [" of God", "H0430"],
    [" moved", "H7363"],
    [" upon", "H5921"],
    [" the face", "H6440"],
    [" of the waters", "H4325"],
    [".", null],
  ];

  assert.deepEqual(project("Genesis|1|2", standard, custom, segments), [
    ["earth", "H0776"],
    ["form", "H8414"],
    ["void", "H0922"],
    ["darkness", "H2822"],
    ["face", "H6440"],
    ["deep", "H8415"],
    ["Spirit", "H7307"],
    ["God", "H0430"],
    ["moved", "H7363"],
    ["upon", "H5921"],
    ["face", "H6440"],
    ["waters", "H4325"],
  ]);
});

test("Matthew 12:40 — preserve the explicit great fish phrase mapping", () => {
  const standard =
    "For as Jonas was three days and three nights in the whale's belly; so shall the Son of man be three days and three nights in the heart of the earth.";
  const custom =
    "For as Jonas was three days and three nights in the great fish's belly; so shall the Son of man be three days and three nights in the heart of the earth.";

  const segments = [
    ["For", "G1063"], [" as", "G5618"], [" Jonas", "G2495"],
    [" was", "G2258"], [" three", "G5140"], [" days", "G2250"],
    [" and", "G2532"], [" three", "G5140"], [" nights", "G3571"],
    [" in", "G1722"], [" the whale's", "G2785"], [" belly", "G2836"],
    ["; so", "G3779"], [" shall", "G2071"], [" the Son", "G5207"],
    [" of man", "G0444"], [" be", "G2071"], [" three", "G5140"],
    [" days", "G2250"], [" and", "G2532"], [" three", "G5140"],
    [" nights", "G3571"], [" in", "G1722"], [" the heart", "G2588"],
    [" of the earth", "G1093"], [".", null],
  ];

  assert.deepEqual(project("Matthew|12|40", standard, custom, segments), [
    ["For", "G1063"], ["as", "G5618"], ["Jonas", "G2495"],
    ["was", "G2258"], ["three", "G5140"], ["days", "G2250"],
    ["and", "G2532"], ["three", "G5140"], ["nights", "G3571"],
    ["in", "G1722"], ["fish's", "G2785"], ["belly", "G2836"],
    ["so", "G3779"], ["shall", "G2071"], ["Son", "G5207"],
    ["man", "G0444"], ["be", "G2071"], ["three", "G5140"],
    ["days", "G2250"], ["and", "G2532"], ["three", "G5140"],
    ["nights", "G3571"], ["in", "G1722"], ["heart", "G2588"],
    ["earth", "G1093"],
  ]);
});

test("Punctuation — commas and semicolons do not steal word associations", () => {
  const segments = [
    ["was", "G001"],
    [" without form", "H8414"],
    [", and void", "H0922"],
    [";", null],
  ];

  assert.deepEqual(
    project(
      "Test|1|1",
      "was without form, and void;",
      "became without form, and void;",
      segments
    ),
    [["form", "H8414"], ["void", "H0922"]]
  );
});

test("Repeated words — preserve distinct IDs when ordered matches are safe", () => {
  const segments = [
    ["The word", "H001"],
    [" word", "H002"],
    [" was", "G003"],
    [" here", "G004"],
    [".", null],
  ];

  assert.deepEqual(
    project(
      "Test|1|2",
      "The word word was here.",
      "The word word became here.",
      segments
    ),
    [["word", "H001"], ["word", "H002"], ["here", "G004"]]
  );
});

test("Repeated words — leave genuinely ambiguous word mapping unnumbered", () => {
  const segments = [
    ["The word", "G010"],
    [" was", "G011"],
    [" here", "G012"],
    [".", null],
  ];

  assert.deepEqual(
    project(
      "Test|1|3",
      "The word was here.",
      "The word word was here.",
      segments
    ),
    [["was", "G011"], ["here", "G012"]]
  );
});

test("Punctuation changes preserve safe lexical-word associations", () => {
  const segments = [
    ["The testimony", "G3142"],
    [" was recorded", "G3140"],
    [" in heaven", "G3772"],
    [".", null],
  ];

  assert.deepEqual(
    project(
      "Test|2|1",
      "The testimony was recorded in heaven.",
      "The testimony was recorded,",
      segments
    ),
    [["testimony", "G3142"], ["recorded", "G3140"]]
  );
});

test("Hyphenated final words retain their Strong's association", () => {
  const segments = [
    ["to", "G4314"],
    [" you-ward", "G5209"],
    [".", null],
  ];

  assert.deepEqual(
    project("Test|2|2", "to you-ward.", "by you-ward.", segments),
    [["you-ward", "G5209"]]
  );
});

test("Shortened 1 John 5:7 preserves forced repeated-word matches", () => {
  const standard =
    "For there are three that bear record in heaven, the Father, the Word, and the Holy Ghost: and these three are one.";
  const custom = "For there are three that bear record,";
  const segments = [
    ["For", "G3754"], [" there are", "G1526"],
    [" three", "G5140"], [" that bear record", "G3140"],
    [" in", "G1722"], [" heaven", "G3772"],
    [", the Father", "G3962"], [", the Word", "G3056"],
    [", and", "G2532"], [" the Holy", "G0040"],
    [" Ghost", "G4151"], [": and", "G2532"],
    [" these", "G3778"], [" three", "G5140"],
    [" are", "G1526"], [" one", "G1520"], [".", null],
  ];

  assert.deepEqual(
    project("1 John|5|7", standard, custom, segments),
    [
      ["For", "G3754"],
      ["are", "G1526"],
      ["three", "G5140"],
      ["record", "G3140"],
    ]
  );
});

test("Galatians 5:22 — goodness marker survives punctuation and wording changes", () => {
  const standard =
    "But the fruit of the Spirit is love, joy, peace, longsuffering, gentleness, goodness, faith,";
  const custom =
    "But the fruit of the Spirit is love, joy, peace, patience and mercy, kindness, goodness and generosity, faith,";
  const segments = [
    ["But", "G1161"], [" the fruit", "G2590"],
    [" of the Spirit", "G4151"], [" is", "G2076"],
    [" love", "G0026"], [", joy", "G5479"],
    [", peace", "G1515"], [", longsuffering", "G3115"],
    [", gentleness", "G5544"], [", goodness", "G0019"],
    [", faith", "G4102"], [",", null],
  ];

  const result = project("Galatians|5|22", standard, custom, segments);
  assert.ok(result.some(([word, id]) => word === "goodness" && id === "G0019"));
  assert.ok(result.some(([word, id]) => word === "faith" && id === "G4102"));
});

test("Galatians 5:23 — Meekness marker survives comma removal", () => {
  const standard = "Meekness, temperance: against such there is no law.";
  const custom = "Meekness and humility, self-control: against such there is no law.";
  const segments = [
    ["Meekness", "G4236"], [", temperance", "G1466"],
    [": against", "G2596"], [" such", "G5108"],
    [" there is", "G2076"], [" no", "G3756"],
    [" law", "G3551"], [".", null],
  ];

  const result = project("Galatians|5|23", standard, custom, segments);
  assert.ok(result.some(([word, id]) => word === "Meekness" && id === "G4236"));
  assert.ok(result.some(([word, id]) => word === "against" && id === "G2596"));
});

test("Subword Strong's markers — preserve both associations inside whosoever", () => {
  const standard =
    "And whosoever speaketh a word against the Son of man, it shall be forgiven him: but whosoever speaketh against the Holy Ghost, it shall not be forgiven him, neither in this world, neither in the world to come.";
  const custom = standard.replace("the Holy Ghost", "the Holy Spirit");

  const segments = [
    ["And", "G2532"],
    [" whosoever", "G3748"],
    [" speaketh", "G2036"],
    [" a word", "G3056"],
    [" against", "G2596"],
    [" the Son", "G5207"],
    [" of man", "G0444"],
    [", it shall be forgiven", "G0863"],
    [" him", "G0846"],
    [": but", "G1161"],
    [" who", "G3739"],
    ["soever", "G0302"],
    [" speaketh", "G2036"],
    [" against", "G2596"],
    [" the", "G4151"],
    [" Holy", "G0040"],
    [" Ghost", "G4151"],
    [", it shall", "G0863"],
    [" not", "G3756"],
    [" be forgiven", "G0863"],
    [" him", "G0846"],
    [", neither", "G3777"],
    [" in", "G1722"],
    [" this", "G5129"],
    [" world", "G0165"],
    [", neither", "G3777"],
    [" in", "G1722"],
    [" the", "G3195"],
    [" world to come", "G3195"],
    [".", null],
  ];

  const result = logic._test.projectSegments(
    standard, custom, segments, "Matthew|12|32"
  );

  assert.ok(result, "Projection should succeed");
  assert.equal(
    result.map(([surface]) => surface).join(""),
    custom,
    "Visible wording and spacing must remain unchanged"
  );

  assert.ok(
    result.some(
      (segment, index) =>
        segment[0] === " who" &&
        segment[1] === "G3739" &&
        result[index + 1]?.[0] === "soever" &&
        result[index + 1]?.[1] === "G0302"
    ),
    "Both source markers must remain at their original subword boundaries"
  );

  assert.ok(
    result.some(
      ([surface, id]) => surface === " whosoever" && id === "G3748"
    ),
    "The first whosoever must retain its separate source marker"
  );
});

let failures = 0;

for (const item of tests) {
  try {
    item.run();
    process.stdout.write(`PASS: ${item.name}\n`);
  } catch (error) {
    failures++;
    process.stdout.write(`FAIL: ${item.name}\n`);
    process.stdout.write(`${String(error.message).split("\n").slice(0, 12).join("\n")}\n\n`);
  }
}

process.stdout.write(`\nTests: ${tests.length}; Passed: ${tests.length - failures}; Failed: ${failures}\n`);
process.exitCode = failures === 0 ? 0 : 1;
