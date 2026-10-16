# GD Bible Revision Review Packets V1 — CPU Audit Record

**Status:** milestone complete (packet layer built and audited; production packet artifact intentionally NOT written).
**Owner:** GD Bible workstream.
**Scope:** deterministic, CPU-only, read-only construction of per-verse evidence packets for a later
Bible-revision judgment stage, plus the owner-specified review inputs (Track C) and the separate
style-policy inputs.
**Recorded:** 2026-10-14 (EDT).
**Worktree:** `/home/liongateos/gd-bible-closeout`
**Branch:** `gd-full-high-research-closeout`
**Initial GD packet-work base:** `f8e50c30563e9522b422e987962d876bda795006`
**Final reconciled HEAD / origin/main before commit:** `1dd1d4d98f47ce6042e5e6c77f023cc547c0d1df`

**Provenance note:** CASE completed shared-main promotion. The isolated GD branch was
first cleanly fast-forwarded from `f8e50c3` to `bfa5e86`, preserving the accumulated
uncommitted GD review-packet files. Shared main later advanced by two additional CASE
commits, and the isolated GD branch was then cleanly fast-forwarded from `bfa5e86` to
`1dd1d4d`, again preserving the same uncommitted GD work. The final reconciled HEAD
(`1dd1d4d`) was NOT the original starting HEAD; that was `f8e50c3`.

## 0. Boundary of this milestone

This milestone **does not** invoke a model, does **not** make a Bible editorial decision, does **not**
edit the canonical GD Bible, and does **not** write production packets. It constructs and audits the
packets only. Archive scripture references remain **model-attributed evidence**.

Owner-specified material is carried as **review candidates**: never accepted translation, never archive
evidence, and never accompanied by an invented theological or linguistic justification.

## 1. Frozen inputs and measured hashes

| Role | Path | SHA-256 |
|---|---|---|
| Finding reference map | `…/gd-bible-revision-mapping-v1/finding_reference_map.jsonl` | `7b98d8a9a7ce1748dfd65fbada34e95e0a53cd8d8454dcdf4ff5c5410f0bda8f` |
| Verse evidence index | `…/gd-bible-revision-mapping-v1/verse_evidence_index.jsonl` | `f6cc556ed145848079827ec8f134e38ec8e39e7302f6b2fa0107d77e0631a52a` |
| Reference anomalies | `…/gd-bible-revision-mapping-v1/reference_anomalies.jsonl` | `e66309b7e39b793b3260803096dba71fbac0b23ea7dae7f126ef50b2e2bc001b` |
| Evidence-bridge manifest | `…/gd-bible-revision-mapping-v1/manifest.json` | `9329dbf1d451ad7711785cc3935168814d1e5dd9a4b92a36328ac0c07a84eab2` |
| Standard KJV asset | `…/assets/bible/en_kjv.json` | `4109ee74d422614995325b5d2f43da9ec35d9be547d6a11bc68fb0978179585f` |
| Current GD asset | `…/assets/bible/kjv_modified.json` | `f2e29b70e61fb1345d80721905caf9f59049f5265ad1c28bd2f9e2d82fedbb4c` *(measured this milestone)* |
| Transformation manifest | `…/docs/bible/TRANSFORMATION_MANIFEST.json` | `c3451fb48212c0c8081a57b3b1db131fa969da0d554a71e7b2923994a1cb333f` *(measured this milestone)* |
| Owner review inputs | `gd_bible_owner_review_inputs.json` (SHA-pinned; Git-visible, **untracked, not committed**) | `d6eb6552e46626dc4ef234d8f18f230a1c7b34461b8eb5f2109a1b1ae477e824` |
| Canonical coordinate table | `gd_canonical_coordinates.json` (committed) | `a0d2c672f6c06f3307c22027216ae53f98bdf910903ef86c049fbbdeb4e9753f` |
| Mapping module | `gd_bible_revision_mapping.py` (imported) | `56d81325488c40e917a2eaaed4c05c2fe124e18b1a4e41aac51ddbae09642792` |
| Scripture engine | `gd_scripture_engine.py` (imported) | `7e336688d359693b046034a7bf49b827e1edc06da510f3bbb8a9310833b670fa` |
| Packet builder source | `gd_bible_revision_review_packets.py` | recorded live in the stream manifest at write time |

All four evidence-bridge hashes and the standard-KJV hash match their published pins exactly. The
current-GD, transformation-manifest and owner-input hashes were not previously pinned; they are now
measured, recorded here, and enforced as pins by the builder.

**Tracking status of the owner-input document (accurate as of this record).** `gd_bible_owner_review_inputs.json`
is **SHA-pinned** by the builder and **visible to Git** through a deliberately narrow `.gitignore`
exception (`!gd_bible_owner_review_inputs.json`), while the broad `*.json` exclusion remains in force for
everything else. It is **currently untracked and is NOT committed** — nothing in this workstream is
staged, committed or pushed. Repository-backed durability of the owner inputs is therefore **not yet
complete**; it becomes complete only after the eventual reviewed commit. Until then the document exists
only in the worktree, and a pinned build fails closed if it is missing or altered in any way.

The owner-input hash changed in the most recent record-correction pass because omitted raw owner text
was restored verbatim (the full first Jude note and the three reverential-capitalization notes). No
count, selection rule, overlap or review identity changed as a result.

The coordinate table and the two imported modules are pinned too. A pinned run refuses an explicit
alternate coordinate source **before any input is read**, so the provenance recorded in the manifest can
never name a different file than the one actually used. `dependency_pins` in the manifest records the
coordinate path/hash/counts (`66 / 1189 / 31102`) and the mapping (`1.0.0`) and engine (`1.5.0`)
paths, hashes and versions that were actually imported.

## 2. Versions and schema

| Item | Value |
|---|---|
| Packet schema | `gd-bible-revision-review-packet/1` |
| Packet builder version | `1.0.0` |
| Source mapping schema | `gd-bible-revision-reference-map/1` |
| Owner inputs schema | `gd-bible-owner-review-inputs/1` |
| Owner overlay schema | `gd-bible-owner-review-overlay/1` |
| Review universe schema | `gd-bible-review-universe-index/1` |
| Authoritative association | `verse_evidence_index:verse_key+finding_uid` |

Each per-verse packet carries: `schema_version`, `packet_builder_version`, `track`, `track_name`,
`priority_tier`, `verse_key`, `canonical_reference`, `book_id`, `book`, `chapter`, `verse`,
`standard_kjv_text`, `current_gd_text`, `text_differs`, `currently_changed`,
`direct_archive_verse_evidence`, `current_transformation_rules`, `evidence_summary`, `evidence`,
`selection_basis`.

Each evidence item carries `finding_uid`, the finding's topic/quote/note/confidence/provenance/
speaker/occurrences/char offsets/quote hash, source document path + SHA-256, collection, chunk id,
research generation, final pass + pass key, `raw_scripture_refs`, per-verse `verse_raw_refs`,
`mapped_verse_keys`, and a `provenance` block naming the association and the
`model_attributed_archive_evidence` evidence class.

## 3. Construction rules

**Track A — Existing Change Audit (exact rule).** Parse every `TRANSFORMATION_MANIFEST.json` reference
with the committed GD mapping parser (`classify_raw_reference` → `expand_verse_keys`); require every
reference to resolve to exactly one canonical verse key; each such verse yields exactly one packet.
Emitted even with no mapped archive evidence (`evidence = []`, counts 0,
`direct_archive_verse_evidence = false`, `selection_basis.rule = existing_gd_transformation_review`).
Absence of mapped archive evidence is not evidence that the wording is wrong.

**Track B — New Change Discovery Tier 1 (exact rule).** From `verse_evidence_index.jsonl`, count unique
findings per verse whose `finding_topic` is one of `translation`, `terminology`, `wording`,
`capitalization`. A verse qualifies when it is **not** currently changed **and** that count is `>= 20`.
`scripture` alone never qualifies. Evidence on a Track B packet is the complete deduplicated finding
list attached to the verse; `revision_relevant_finding_count` is recorded separately from the all-topic
evidence count.

**Join rules.** Findings are never re-mapped in this layer and no verse association is inferred.
Findings are deduplicated by `finding_uid` per verse. Bible text is joined verbatim by
`book_id`/`chapter`/`verse` from both assets, failing closed on out-of-range book/chapter/verse or any
asset/coordinate disagreement.

**Transformation accounting.** `applicationCount` is an applied-transformation count, not a reference
count: R024/R025/R026 have more applications than reference entries, and R001/R011 repeat a reference
entry verbatim. Both facts are preserved per verse in `manifest_reference_strings` (duplicates intact)
and per rule in the manifest inventory. 383 applications ≠ 364 reference entries ≠ 335 unique verses.

**Track C — Owner-Specified Review Candidates (exact rule).** Track C is not evidence-derived: a verse
is a candidate because the owner named it. There is **no archive-evidence threshold** and no
revision-relevant finding count on the Track C path. Owner material is resolved through the *already
committed* Scripture reference parser (`classify_raw_reference`) — no new verse parser exists — and the
raw owner string, its raw parser status, the parser input actually used and any owner-declared
normalization are all preserved verbatim:

- the raw spelling is kept (`owner_reference_raw`), so `Isaias 35:7` stays `Isaias 35:7` while its
  canonical target is `Isaiah 35:7` (the committed parser returns `unresolved` for that spelling and
  **no alias was added to it**; the normalization is recorded as `owner_declared`);
- `Jude 1` resolves through single-chapter semantics to `b65:c1:v1`;
- a duplicated owner note (1 John 2:20, recorded twice) keeps both occurrences on **one** review
  identity;
- all three Jeremiah 17:9 alternatives are preserved (`alternatives_preserved: true`,
  `selection: null`) — the builder never picks one, and it records no reason of its own;
- a context-only reference that is a range (`John 14:2-3`) resolves deterministically, and its extra
  verse is recorded as context only (`b43:c14:v3`) and never becomes a candidate;
- any owner reference that neither parses nor carries an owner-declared normalization **fails the
  build closed** rather than being guessed or silently dropped.

Every candidate carries `provenance_class = owner_specified_editorial_candidate`,
`candidate_status = review_candidate`, `accepted_translation = false`. Owner rationale is never mixed
into archive evidence: the owner block contains no `evidence` field and declares
`owner_rationale_is_archive_evidence: false`.

**Raw owner notes are preserved verbatim, never parsed.** Each candidate carries its owner-note
occurrences word for word, and each style policy carries its owner-note occurrences word for word.
Scripture references that appear *inside* a note or a style example are part of that note: they are not
scanned, not resolved into candidates, and not converted into archive evidence. In particular the Jude
note's `Matthew 22:14` and the reverential-capitalization example's `John 8:29` create no candidate, and
a test proves that replacing every raw note with injected references changes no candidate's identity or
verse key, while a structural guard confirms the resolver never reads the policy block or feeds note
text to the reference parser.

**Style policies.** The three style policies are a *separate* input class, not verse packets: they
create zero packets and appear only as preserved policy records. All three are `approved: false`,
`applied: false`, `implementation_status: not_implemented`, and each requires contextual
classification with blind replacement forbidden. Reverential capitalization is recorded as a
`final_reversible_style_pass` with `apply_order: last` and an explicit owner open question; the
Kingdom policy is contextual; the Word policy remains `review_candidate_question` with its wording
hedge (`might`) preserved. The reverential-capitalization policy carries its three owner notes word for
word — the general instruction with the NKJV/NASB mentions, the GD-translation explanation of why a
capitalized `Me`/`My` implies no lack of humility, and the owner's reason for keeping the rule last and
reversible — and none of that text is treated as evidence or as an accepted style decision.

**Track C storage (no payload duplication).** Ten unique owner verse keys are published as a small
deterministic overlay stream, `owner_candidate_review_overlay.jsonl`, plus a small deterministic unique
`review_universe_index.jsonl`. An owner verse already published in Track A or Track B gets one
`merge_into_existing_packet` **pointer** record (owner block + a merge instruction naming the stream
that holds the authoritative text and evidence; `payload_embedded: false`, no A/B payload copied). An
owner-only verse gets one complete standalone Track C packet. The review universe index has exactly one
row per unique `verse_key` across A + B + C with `review_identity == verse_key`, so the deterministic
merge-on-verse-key rule means an owner candidate already in A or B can never cause a second model
judgment. Track A and Track B packet objects are not modified by the overlay.

## 4. Audit results (pinned, full corpus)

All 77 audit checks pass; `verdict = pass`. The Track B text-difference invariant
(`track_b_packets_with_unmanifested_text_difference == 0`) is one of the pinned checks: a Track B verse
is by definition absent from the transformation manifest, so a standard/current text difference there is
an integrity discrepancy, and a pinned build fails instead of treating it as a normal candidate.

| Track A | |
|---|---|
| Packets | **335** |
| With direct archive evidence | **215** |
| Without direct archive evidence | **120** (still emitted) |
| Evidence rows on changed verses | **2,385** |
| Unique evidence findings | **2,121** |
| Verses affected by more than one rule | 25 |

| Track B | |
|---|---|
| Packets | **316** |
| Overlap with Track A | **0** |
| Minimum revision-relevant findings | **20** |
| Maximum revision-relevant findings | 309 |
| Unique evidence findings | 13,381 |
| Evidence rows summed across packets | 17,791 |
| Source-document associations | 14,612 |
| Packets with unmanifested text difference | 0 |

| Combined | |
|---|---|
| Packets | **651** |
| Unique verse keys | **651** |
| Duplicate packet verse keys | **0** |
| Track A/B disjoint | yes |

| Track C (owner-specified) | |
|---|---|
| Owner verse candidates | **10** (10 unique verse keys) |
| Raw owner-note occurrences | **12** |
| Duplicate owner-note occurrences | **1** (1 John 2:20, one review identity) |
| Unresolved owner references | **0** |
| Overlap with Track A | **0** |
| Overlap with Track B | **4** — Jeremiah 17:9, Malachi 3:17, John 14:2, Ephesians 1:14 |
| Owner-only verses | **6** — Isaiah 35:7, Luke 15:25, 1 Corinthians 2:12, 1 John 2:20, 1 John 4:2, Jude 1 |
| Pointer records / standalone packets | **4** / **6** |
| Owner candidates with / without archive evidence | **10** / **0** (measured; the threshold is what differs, not presence) |
| Archive-evidence threshold | **none** |

| Review universe (A ∪ B ∪ C) | |
|---|---|
| Unique review identities | **657** |
| Duplicate review identities | **0** |
| Track A only | 335 |
| Track B only | 312 |
| Owner overlay on Track B | 4 |
| Track C only | 6 |

| Style policies | |
|---|---|
| Policies | **3** (all `approved: false`, `applied: false`) |
| Verse packets created | **0** |

Transformation manifest reconciliation: 33 rules, 383 applications, 364 reference entries, 335 unique
changed verses, 2 rules with duplicate reference entries.

Every evidence `finding_uid` exists in `finding_reference_map.jsonl`; no evidence association exists
that is absent from `verse_evidence_index.jsonl`; every standard/current Bible coordinate was
re-resolved through the fail-closed text index and matched its stored verbatim text (651 lookups,
0 failures); the anomaly stream was independently counted (4,061 rows).

## 5. Evidence distribution and size estimate (Track B)

Revision-relevant findings per packet (selection quantity): min 20, median 29.0, p75 41.0, p90 62.0,
p95 73.75, max 309.
All (deduplicated) evidence findings per packet (payload quantity): min 21, median 45.0, p75 61.25,
p90 91.5, p95 122.25, max 457.
Percentiles use linear interpolation between order statistics.

Top 20 largest Track B packets by all evidence: 2 Corinthians 4:4 (457 findings), Revelation 12:9 (313),
Matthew 24:22 (295), Genesis 1:1 (272), John 1:1 (222), Matthew 24:14 (218), Genesis 1:26 (214),
Matthew 16:18 (208), Ephesians 2:2 (168), Genesis 2:7 (160), Matthew 24:21 (156), 1 John 3:4 (142),
1 Corinthians 2:11 (139), Romans 8:16 (135), Revelation 3:8 (125), Romans 6:23 (123),
Revelation 3:7 (122), John 3:6 (121), Romans 8:7 (116), Mark 1:14 (112).

Exact in-memory JSONL sizes (no production file written):

| Stream | Packets | Bytes | MiB | SHA-256 |
|---|---|---|---|---|
| `existing_change_review_packets.jsonl` | 335 | 4,394,249 | 4.191 | `be68fe90ecdd924d6b57cfc19055fe8c978dcf8ff87dbf388fc0f7c7b915d1cf` |
| `new_change_tier1_review_packets.jsonl` | 316 | 27,657,062 | 26.376 | `b11d8176e4854930bd819da5911244c08129cf84425dd7e7e96633fe5e371f08` |
| Combined (A + B) | 651 | 32,051,311 | 30.567 | — |
| `owner_candidate_review_overlay.jsonl` | 10 | 176,012 | 0.168 | `389ff0e6c4e725424fa04d246316f335c1ea23871a54e57969c9753995facefb` |
| `review_universe_index.jsonl` | 657 | 332,955 | 0.318 | `f083e0b2312aee6dfe92eac88fcfde93854c33e7b9d5b3a2005943104e5d4186` |

The two Track C streams together add **508,967 bytes (0.49 MiB)** to a 32,051,311-byte artifact — the
overlay does not duplicate any Track A/B payload (pointer records carry no text or evidence).

## 5a. Writer defect found and repaired this round

The first attempt at a *temporary* production publication was refused by the staged-artifact verifier:

```
staged artifact failed verification (2):
new_change_tier1_review_packets.jsonl: staged line count 317 != manifest packets 316;
new_change_tier1_review_packets.jsonl: staged line is not JSON
```

**Exact cause, not a guess:** `_verify_staged_artifact` counted staged records with
`payload.splitlines()`. `str.splitlines()` breaks on `\x0b`, `\x0c`, `\x1c`, `\x1d`, `\x1e`, `\x85`,
`\u2028` and `\u2029` in addition to `\n`. `json.dumps(ensure_ascii=False)` escapes C0 controls
(U+001E is written as the six characters `\u001e`) but emits U+2028/U+2029/U+0085 **raw inside string
values**. One Track B record — 0-based index 169 / 1-based record 170, `b46:c15:v50`
(1 Corinthians 15:50 wording), field
`.evidence[24].finding_quote`, offset 95, context `'…flesh-and-blood human being? ␨1 Corinthians
15:50.'` — contains a raw U+2028, so the verifier saw two "lines" for one record: 316 records became
317. Only one of the three U+2028 occurrences in `finding_reference_map.jsonl` lands on a Track B
verse, which is why the count was 317 and not 319. Track A contains zero such characters and was
never affected.

**Repair (writer/verifier boundary only).** The verifier now splits on the actual record terminator
with `split_jsonl_records(text)`: records are `"\n"`-separated, a trailing `"\n"` is required, and any
other character is ordinary data. No packet-selection, evidence-join, Bible-join or packet-content
logic changed. Both original streams are byte-identical to the reviewed revision (same byte counts and
the same SHA-256 shown above), proving the repair did not touch the payload. The audit now reports per
stream `records_with_unicode_line_boundary` (Track B: 1, Track A: 0), `record_terminator: "\n"` and an
explicit `record_split_rule` telling consumers to split on `"\n"` only. A regression test reproduces the
exact production shape (a Track B record containing U+2028) and asserts that `splitlines()` really does
report 2 lines while the record contract reports 1, that publication now succeeds, and that the written
file hashes to the manifest. A second test proves a genuinely extra blank record is still refused.

## 5. Publication boundary (hardened)

`--write` has **no default destination**: it requires an explicit `--out-dir` and refuses (exit 2)
before reading any input or writing anything if it is absent. No future production directory is
hard-coded anywhere in the builder or CLI.

Publication is a single atomic set operation:

1. Re-validate the result at the boundary: `inputs_pinned == true`, `audit.verdict == "pass"`, no failed
   checks, and every stream re-derived from its packet objects and re-checked against the manifest
   packet count, byte length and SHA-256. A caller that mutates a previously validated result — the
   serialized text, the packet list, or the manifest hashes — is refused.
2. Write all five files into a temporary sibling directory.
3. Verify the staged set in full (byte length, SHA-256, staged record count vs manifest packet count
   using the `"\n"` record rule, per-record JSON validity and packet `track`, overlay `track`, review
   universe `record_type`/`review_identity`, manifest self-consistency).
4. Rename the completed directory onto the destination once. An existing destination (file or
   directory) is refused, never overwritten or merged into. On any failure the staging directory is
   removed and the destination is left absent.

## 6. Usage

```bash
# deterministic audit only (default; writes nothing)
python3 gd_bible_revision_review_packets.py --audit-only

# explicit unpinned test mode (still writes nothing without --write)
python3 gd_bible_revision_review_packets.py --audit-only --allow-unpinned

# alternate owner-input document (audited against the pin; a pinned run fails closed
# unless the file matches OWNER_INPUTS_SHA256)
python3 gd_bible_revision_review_packets.py --audit-only --owner-inputs <path>

# production write — NOT performed in this milestone; --out-dir is required
python3 gd_bible_revision_review_packets.py --write --out-dir <explicit-destination>
```

`--write` without `--out-dir`, and `--write` combined with `--allow-unpinned`, are both refused. A
pinned run aborts on any hash/count drift, an explicit alternate coordinate source, any manifest
reference that does not resolve to exactly one verse, any missing `finding_uid` record, any Bible
coordinate failure, or any failed audit check.

## 7. Tests

- Focused suite: `python3 -m unittest tests.test_gd_bible_revision_review_packets` — **141 tests, OK**
  (123 always-on, 18 gated behind `GD_RUN_FULL_PACKET_AUDIT=1`).
- Gated frozen-input audit: `GD_RUN_FULL_PACKET_AUDIT=1 python3 -m unittest
  tests.test_gd_bible_revision_review_packets` — **141 tests, OK** (3.9 s, one shared pinned build).
- GD regressions: `tests.test_gd_bible_revision_mapping` **75 OK** (1 skipped),
  `tests.test_gd_scripture_engine` **83 OK**.

New coverage this round: committed dependency hashes/versions match their pins and mismatches fail
closed; the pinned run refuses any explicit `--coordinates` path before reading input while an unpinned
run still measures an alternate table truthfully; `--write` without `--out-dir` is refused; the
artifact set publishes atomically; injected failure after the first or second file leaves the
destination absent with no staging left behind; a corrupted staged file is caught before publication;
an existing destination is refused untouched; and a mutated stream, packet list or manifest is refused
at the boundary.

Track C / writer coverage added this round: the exact ten owner verses and twelve raw occurrences; the
duplicated 1 John 2:20 note preserved on one review identity; `Jude 1 → b65:c1:v1`; `Isaias 35:7`
preserved with canonical `Isaiah 35:7` and an `owner_declared` normalization that is not a parser alias;
`John 14:3` never a candidate; the three Jeremiah alternatives preserved with no selection; owner
rationale never archive evidence; an owner-only verse with zero archive evidence still review eligible;
overlap merging by verse key into a pointer with no copied payload; no duplicate model-review identity
after A + B + C; style policies creating zero verse packets; reverential capitalization final,
reversible and not applied; the Kingdom policy contextual and not a blind replace; the Word policy still
a candidate question; an unparseable owner reference failing closed instead of being guessed; the exact
317-record writer failure reproduced and repaired with a blank-record counter-test; and Track A / Track B
byte counts and SHA-256 asserted unchanged (`4394249 / be68fe90…`, `27657062 / b11d8176…`).

Context-preservation coverage added in the record-correction pass: the full first Jude owner note is
present with its `Matthew 22:14` / "many are called, but few are chosen" contrast and the owner's
personally-inviting context, while the existing second occurrence is untouched and both remain on the
single identity `b65:c1:v1`; the three reverential-capitalization notes are preserved verbatim
(NKJV/NASB as owner context, the Me/My lack-of-humility explanation, and the owner's reversibility
rationale) with the structured policy fields unchanged; `Matthew 22:14` and `John 8:29` classify to real
verse keys yet create no candidate, no context promotion and no overlay entry; injecting references into
every raw note changes no candidate identity; style-policy notes carry no archive-evidence field; and the
10 / 12 / 0 / 4 / 6 / 657 invariants are re-asserted against the frozen inputs.

## 8. Readiness

The packet layer is ready for ChatGPT code review. Production packets were deliberately not emitted;
the RTX 3090 Ti / Qwen judgment stage has not begun. Track C and the style policies are review inputs
only: they are not accepted translation and no model judgment has been made on them.

## 9. Review patch fingerprint

The canonical review patch treats `.gitignore` as a TRACKED modification and uses `git diff` (not
`--no-index`) for it. The remaining four files are new and use `git diff --no-index` against `/dev/null`.

The exact five-file order is:

1. `.gitignore` (tracked modification)
2. `gd_bible_revision_review_packets.py` (new)
3. `tests/test_gd_bible_revision_review_packets.py` (new)
4. `docs/GD_BIBLE_REVISION_REVIEW_PACKETS_V1_AUDIT.md` (new)
5. `gd_bible_owner_review_inputs.json` (new)

The recipe (no color) is:

```bash
{ git diff --no-color -- .gitignore
  git diff --no-index --no-color -- /dev/null gd_bible_revision_review_packets.py
  git diff --no-index --no-color -- /dev/null tests/test_gd_bible_revision_review_packets.py
  git diff --no-index --no-color -- /dev/null docs/GD_BIBLE_REVISION_REVIEW_PACKETS_V1_AUDIT.md
  git diff --no-index --no-color -- /dev/null gd_bible_owner_review_inputs.json
} | sha256sum
```

The order is fixed and the owner-input document is included verbatim, so the digest covers the data the
build is pinned to. The SHA-256 of this revision is reported with the deliverable rather than embedded
here, because this file is part of the patch and embedding the digest would make the fingerprint
self-referential.

Packet-producing logic is unchanged from the reviewed revision: the two serialized packet streams are
byte-identical (same byte counts and same SHA-256), so the patch grew only by the writer repair, the
owner-input pin, Track C and the publication hardening described above.
