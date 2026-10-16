# GD Bible Editorial Review V1 — Methodology

**Version:** 1.0
**Recorded:** 2026-10-15 (EDT)
**Status:** Governing methodology for the editorial-review stage
**Authority:** GD Bible workstream; owner decisions required for all approvals

---

## 1. Purpose

This document establishes a durable repository/GitHub-backed editorial evidence-review layer for the Grow Daily Bible (GD Bible) so that:

1. Church reviewers can later determine why each GD Bible change was retained, reconsidered, or added.
2. Archive evidence remains distinguishable from model reasoning and owner/editorial decisions.
3. Rule-level transformations can be audited once with verse-level exceptions rather than redundantly reviewed verse by verse.
4. Deterministic whole-Bible coverage checks can be preserved.
5. A future CASE-safe research insight export can contain archive-grounded material without importing GD editorial conclusions.

### 1.1 Existing Modified-GD Baseline

The current GD Bible is already a modified KJV. This milestone documents/audits the EXISTING GD transformations and the evidence-review methodology. It does NOT regenerate the Bible from an untouched KJV.

**Repository attribution:** The canonical GD Bible text resides in the separate `LionGateOS-Bible` repository (`/home/liongateos/LionGateOS-Bible`), which contains `en_kjv.json`, `kjv_modified.json`, and `TRANSFORMATION_MANIFEST.json`. This editorial review documentation in the `Church-Archive-Search` repository (branch `gd-full-high-research-closeout`, HEAD `fea4ab7`) documents and audits transformations without modifying the canonical Bible text.

**HEAD verification:** The branch `gd-full-high-research-closeout` is the active development branch for the GD Bible editorial review workstream in the shared Church-Archive-Search repository.

### 1.2 Comparison Baseline

For transformation analysis, the standard KJV comparison baseline is the canonical `en_kjv.json` file. This file is preserved read-only and serves as the reference point for identifying what transformations have been applied.

---

## 2. Track Definitions

The review universe partitions into three tracks:

### Track A: Existing GD-Changed Verses

Verses where the current GD Bible differs from the canonical KJV baseline. These transformations are already present in the GD Bible but require editorial review under this new lifecycle.

- **Count:** 335 unique verses
- **Purpose:** Audit existing transformations for retention, reconsideration, or modification

### Track B: Unchanged Tier-1 Archive-Evidence Candidates

Verses that currently match the KJV baseline but are candidates for potential transformation. These are unchanged verses with at least 20 unique revision-relevant findings, excluding scripture-only findings.

- **Count:** 316 unique verses
- **Purpose:** Evaluate whether archive evidence warrants transformation
- **Inclusion criteria:** Unchanged verses with ≥20 unique revision-relevant findings (scripture-only findings excluded)

### Track C: Owner Candidates

Verses nominated by the owner for review, regardless of current state.

- **Count:** 10 owner candidates
- **Overlap with Track B:** 4 verses
- **Owner-only (not in Track B):** 6 verses

### Track D: Explicit Authorial Corrections

Verses with verified direct corrections from Herbert W. Armstrong or Gerald Flurry, as documented in the church archive. These corrections are accepted under the owner's standing editorial authority policy.

- **Count:** To be determined as explicit-correction records are verified
- **Purpose:** Apply verified authorial corrections under the Armstrong/Flurry authority policy
- **Inclusion criteria:** Direct quotations from Armstrong/Flurry explicitly correcting a specific translation or wording
- **Registry status:** No candidate registry currently exists. Do not claim 8 candidate passages are registered unless actual records exist.

### 2.1 Review Universe Totals

- **Total unique review identities (Tracks A-C):** 657
- **Track D (Explicit Authorial Corrections):** Count pending verification of explicit-correction records
- **Duplicate review identities:** 0

---

## 3. Proposition-Specific Evidence Rule

Evidence must be evaluated against specific propositions, not against vague or conflated claims.

### 3.1 Proposition Separation

Each transformation rule must explicitly define:
- The lexical proposition (word substitution)
- The grammatical proposition (article/pronoun changes)
- The stylistic proposition (capitalization, formatting)
- The theological/semantic proposition (meaning changes)

These propositions must be audited separately because archive evidence may support one proposition while being irrelevant to another.

### 3.2 Evidence Relevance

Evidence is proposition-relevant only if it:
1. Directly addresses the specific word/phrase being changed
2. Provides linguistic, theological, or translation justification for the specific change
3. Is not merely a simple quotation that happens to contain the target word

---

## 4. Rule-Level vs Verse-Level Review

### 4.1 Rule-Level Audit

A rule-level audit evaluates:
- The semantic coherence of the transformation across all applications
- The deterministic coverage (does the rule capture all qualifying verses?)
- The consistency of archive evidence across the rule family
- Whether exceptions exist that require verse-level treatment

### 4.2 Verse-Level Exceptions

Verse-level review is required when:
- Archive evidence supports the rule for most verses but not all
- Contextual factors create genuine exceptions
- The rule's deterministic criteria are ambiguous for specific verses

### 4.3 Audit Efficiency

The goal is to audit rules once at the family level, documenting:
- Where the rule is uniformly supported
- Where verse-level exceptions exist
- Where evidence gaps require external verification

---

## 5. Evidence-Gap Behavior

When archive evidence is sparse or absent for a transformation:

1. **Do not fabricate evidence.** Record the gap explicitly.
2. **Do not mark as approved.** The lifecycle status remains at `EVIDENCE_AUDIT`.
3. **Flag for external verification.** Document what external sources (linguistic, historical, theological) would be needed.
4. **Preserve the transformation's current state.** Record whether it is `currently_present_in_gd: true` without implying approval.

### 5.1 Lack of Evidence is Neutral for Existing Transformations

**Critical:** Lack of direct verse-level evidence is NEUTRAL for existing transformations, NOT evidence against them. An existing transformation may have been implemented based on:
- Rule-level evidence that applies uniformly
- Armstrong/Flurry direct corrections
- Editorial decisions predating this audit framework

The absence of verse-specific archive findings does not constitute a reason to remove an existing transformation. It simply indicates that verse-level evidence was not captured in the archive research corpus.

---

## 6. Change-Burden Rules

### 6.1 Burden of Justification

- **Existing transformations:** Require evidence audit to justify retention under the new lifecycle.
- **New transformations:** Require explicit owner decision and approval before application.
- **Reconsidered transformations:** Require documented reason for change from previous disposition.

### 6.2 No Retroactive Approval

Current presence in the GD Bible does NOT constitute approval under this new lifecycle. Each transformation must progress through the lifecycle explicitly.

---

## 7. Provenance Classes

The methodology defines and preserves these provenance classes:

### 7.1 DETERMINISTIC_CANONICAL

Canonical KJV/GD text, canonical coordinates, transformation-manifest facts, whole-Bible scans, hashes/counts, deterministic mappings.

**Characteristics:**
- Reproducible by any reader with the same artifacts
- No model interpretation required
- Serves as the foundation for all other evidence

### 7.2 ARCHIVE_NATIVE

Statements or quotations authored in the church archive documents themselves.

**Characteristics:**
- Authored by church teachers/authors
- Preserves original wording and intent
- Primary evidence for editorial decisions

### 7.3 ARCHIVE_CITED_EXTERNAL

External translations/sources cited or quoted inside an archive document (e.g., Fenton, Moffatt, RSV).

**Characteristics:**
- Proves that the archive document used/cited that source
- Does NOT independently prove the external translation is correct
- Must be distinguished from ARCHIVE_NATIVE content

### 7.4 MODEL_DERIVED

Model-produced classification, topic labels, direct/partial/indirect judgments, evidence-theme grouping, synthesis, confidence assessment.

**Characteristics:**
- AI-generated interpretation of evidence
- May contain genuine archive quotations while being MODEL_DERIVED
- Requires human verification

### 7.5 MODEL_EXTERNAL

Greek/Hebrew, historical-English, linguistic, theological, or other reasoning supplied by a model but not established by the archive evidence.

**Characteristics:**
- External to the archive corpus
- Requires external verification
- Cannot serve as sole basis for editorial approval

### 7.6 OWNER_EDITORIAL

Owner proposals, owner judgments, approvals, final wording decisions.

**Characteristics:**
- Ultimate authority for GD Bible content
- Required for all approvals
- Distinct from model recommendations

### 7.7 Critical Distinction

A model-attributed research finding can contain a genuine quotation/snippet from an archive document. The classification may be `MODEL_DERIVED` while the quoted source content is still archive-derived. Do not collapse these layers.

---

## 8. Evidence Theme and Repetition Handling

### 8.1 Evidence Themes

Substantive evidence themes for transformation justification:

1. **Explicit terminology critique** — Archive documents explicitly critiquing KJV terminology
2. **Modern-translation evidence** — Archive-cited modern translations supporting the change
3. **Church-document substitution/bracketing** — Archive documents using bracketed clarifications
4. **Explicit teaching usage** — Archive documents teaching the modern terminology
5. **Linguistic analysis** — Archive-based linguistic justification

### 8.2 Simple Quotations

Simple quotations form a large contextual population but are NOT a substantive support theme. They provide context but not independent justification.

### 8.3 Independence Assessment

Do not count repeated simple quotations as independent arguments. Group findings by theme and assess:
- **Direct findings:** Explicitly address the proposition
- **Partial findings:** Partially relevant or require inference
- **Indirect/context findings:** Provide context but not direct support

---

## 9. Confidence Definitions

### 9.1 Confidence vs Evidence Quantity

**Critical distinction:** Confidence levels describe the strength of the model's recommendation, NOT the quantity of evidence. A large volume of indirect/context findings does not increase confidence. Confidence is based on:

1. **Directness of evidence** — How explicitly the evidence addresses the specific proposition
2. **Quality of justification** — Whether the evidence provides linguistic, theological, or translation reasoning
3. **Consistency** — Whether evidence is uniform across applications or has exceptions
4. **External verification availability** — Whether independent sources can confirm the analysis

### 9.2 High Confidence

- Strong archive evidence (multiple direct findings with explicit justification)
- Consistent across all applications
- No contrary evidence identified
- External verification available

### 9.3 Medium Confidence

- Moderate archive evidence (some direct findings, some partial)
- Generally consistent with limited gaps
- No contrary evidence identified
- External verification may be needed

### 9.4 Low Confidence

- Sparse or indirect archive evidence
- Evidence gaps identified
- External verification required
- May require reconsideration

---

## 10. External Verification Boundary

### 10.1 When Required

External verification is required when:
- Archive evidence is sparse or absent
- Linguistic justification is needed beyond archive content
- Historical/etymological analysis is required
- Theological implications extend beyond archive teaching

### 10.2 External Sources

External verification may draw from:
- Greek/Hebrew lexicons and grammars
- Historical English usage dictionaries
- Academic translation comparisons
- Historical theological analysis

### 10.3 Provenance Recording

External verification must be recorded with:
- Source attribution
- Distinction from archive evidence
- `MODEL_EXTERNAL` or appropriate provenance classification

---

## 11. Owner Authority

### 11.1 Owner Decisions

Only the owner may:
- Mark rules as `owner_decision: approve` or `owner_decision: reject`
- Mark rules as `approved_for_application: true`
- Make final wording decisions
- Authorize new transformations

### 11.2 Model Recommendations

Model recommendations:
- Do NOT edit Bible text
- Do NOT constitute approval
- Serve as provisional dispositions for owner review
- Must be explicitly separated from owner decisions

### 11.3 Armstrong/Flurry Direct Scripture Corrections

**Verified direct Scripture corrections taught by Herbert W. Armstrong or Gerald Flurry are accepted under the owner's standing editorial authority policy.**

This policy applies when:
1. A direct quotation from HWA or Flurry explicitly addresses a specific Scripture passage
2. The quotation provides a clear correction, translation note, or interpretive guidance
3. The quotation is verified against the original archive document with checksum validation

**Source quotation requirements:**
- Up to 3 direct quotations normally, up to 4 when justified
- Include at least one quotation from each author when both addressed the correction
- Record exact source path, document hash (SHA-256), and character position ranges
- Distinguish direct authorial statements from quotations of third-party translations

**Examples of qualifying direct corrections:**
- HWA 1979-12-15 Bible study: "In 1611 in England when the Bible was translated into King James English, the trinity doctrine was still believed — and that is the reason Holy Ghost is used. It should be spirit."
- HWA 1978-05-12 Bible study: "And the earth was [That word 'was' should be translated 'became.' That is, it wasn't at the time God created it; but it was later. It became] without form and void."

### 11.4 Reverential Capitalization

#### 11.4.1 Owner-Approved Contextual Reverential Capitalization

The following contextual reverential capitalization rules are owner-approved and may be applied where context supports them:

- **God** (when referring to the Father)
- **Christ** (when referring to Jesus as Messiah)
- **God's Holy Spirit** (when referring to the third person of the Godhead)
- **Kingdom** (when referring to God's Kingdom)
- **Word** (when referring to God's Word/Scripture)
- **Bride** (when referring to the Bride of Christ)
- **Divine pronouns** (He, Him, His) when unambiguously referring to God the Father or Christ

These rules require contextual judgment and are not blind global replacements.

#### 11.4.2 Flurry Usage Observations (Pending Verification)

The owner has reported observations of Gerald Flurry's capitalization usage in *A Father's Love*. These observations are recorded pending exact source verification:

- Specific instances to be documented with source path, document hash, and character positions
- Verification required before any editorial application

#### 11.4.3 "Work" as Flurry Writing Convention

**"Work"** (as in "God's Work" or "the Work") is documented as an observed Flurry writing convention only. There is **no owner approval** to capitalize "Work" in the GD Bible.

**Important:** These observations do NOT constitute:
- Owner-approved reverential style for "Work"
- Independently verified editorial decisions
- Automatically applicable transformations

No blanket capitalization rules apply. Each instance requires contextual judgment under the reverential-capitalization/style policy.

---

## 12. Lifecycle

The authoritative lifecycle is:

```
EVIDENCE_AUDIT
    ↓
EXTERNAL_VERIFICATION
    ↓
OWNER_DECISION
    ↓
APPROVED_FOR_APPLICATION
    ↓
APPLIED
    ↓
VERIFIED
```

### 12.1 Lifecycle States

| State | Description |
|-------|-------------|
| `EVIDENCE_AUDIT` | Archive evidence has been audited; external verification may be needed |
| `EXTERNAL_VERIFICATION` | External sources are being consulted to fill evidence gaps |
| `OWNER_DECISION` | Owner has made a decision pending formal approval |
| `APPROVED_FOR_APPLICATION` | Approved for application to the GD Bible |
| `APPLIED` | Transformation has been applied to the GD Bible |
| `VERIFIED` | Application has been verified and confirmed |

### 12.2 Current Milestone Scope

This milestone operates at the `EVIDENCE_AUDIT` stage. No rules are being newly approved.

---

## 13. Deterministic Coverage Before Application

### 13.1 Whole-Bible Coverage Check

Before any rule is applied:
1. Verify deterministic coverage against the canonical KJV
2. Confirm all qualifying verses are captured
3. Document any edge cases or ambiguities
4. Preserve the coverage check as reproducible evidence

### 13.2 No Blind Global Replacement

No transformation may be applied as a blind global search-and-replace. Each rule must:
- Have deterministic criteria for verse qualification
- Account for context-dependent applications
- Preserve verse-level exception handling

---

## 14. CASE-Safe Separation

### 14.1 Research Insight Export

A future CASE-safe research insight export will contain archive-grounded material only:

**Allowed exports (with provenance preserved):**
- ARCHIVE_NATIVE evidence quotations and verified source metadata
- ARCHIVE_CITED_EXTERNAL quotations with explicit attribution
- Source-native Scripture references (verbatim from archive documents)
- Neutral navigation identifiers (verse keys, document paths)

**DETERMINISTIC_CANONICAL classification alone does not confer CASE-export eligibility.** The following DETERMINISTIC_CANONICAL facts are NOT eligible:
- Canonical GD wording
- KJV-to-GD text comparisons
- Transformation-manifest facts (rule definitions, coverage counts)
- GD editorial counts and statistics

### 14.2 Excluded from CASE Export

The following must NOT be imported into CASE as archive fact:
- GD editorial recommendations and dispositions
- Owner decisions and approvals
- MODEL_EXTERNAL reasoning and justifications
- MODEL_DERIVED classifications and syntheses
- `approved_for_application` status
- Lifecycle states beyond `EVIDENCE_AUDIT`
- Canonical GD Bible text or KJV-to-GD comparisons
- Transformation-manifest details and rule coverage data

### 14.3 Field-Level Eligibility

**CASE-safe export eligibility is field-level, not rule-level.** A rule may have some fields eligible for CASE export while others are not.

**Eligible fields (archive-grounded only):**
- ARCHIVE_NATIVE evidence quotations with source path, document hash, character positions
- ARCHIVE_CITED_EXTERNAL quotations with explicit source attribution
- Source-native Scripture references (verbatim from archive documents, not model-normalized)
- Neutral navigation identifiers (verse keys, document paths) with provenance

**Non-eligible fields:**
- `provisional_disposition` and `provisional_confidence`
- `owner_decision` and `approved_for_application`
- `lifecycle_status` beyond `EVIDENCE_AUDIT`
- MODEL_EXTERNAL and MODEL_DERIVED content
- Canonical GD wording or KJV-to-GD comparisons
- Transformation-manifest facts, rule definitions, coverage counts
- GD editorial statistics and counts

### 14.4 Provenance Preservation

Every exported field must retain its provenance class. CASE may consume only:
- Archive-grounded fields (ARCHIVE_NATIVE, ARCHIVE_CITED_EXTERNAL)
- Source-native identifiers with explicit provenance
- Fields clearly distinguished from editorial conclusions

---

## 15. Church-Review/Audit Requirement

### 15.1 Church Review

All transformations require eventual church review for:
- Editorial approval
- Theological alignment
- Pastoral appropriateness

### 15.2 Audit Trail

The repository must preserve:
- All evidence audit documentation
- Owner decision records
- Lifecycle state history
- External verification sources

---

## 16. Current Rule-Family Pilot Status

### 16.1 Audited Rule Families

This milestone audits three rule families:

1. **R001** — Holy Ghost → Holy Spirit
2. **R002/R004/R006/R007/R008** — Death expression (ordinary persons)
3. **R003/R005** — Death expression (Jesus)

### 16.2 Pilot Scope

These families serve as the pilot for the editorial-review methodology. They demonstrate:
- Proposition separation
- Evidence theme analysis
- Evidence gap handling
- External verification identification
- Lifecycle state recording

---

## 17. Explicit Statement: AI Recommendations Do Not Edit Bible Text

**Critical:** AI recommendations, model-derived analysis, and provisional dispositions do NOT edit Bible text. Only owner decisions marked as `approved_for_application: true` may result in canonical changes.

This methodology documents existing transformations and establishes an audit framework. It does not authorize any new changes without explicit owner approval.

---

## 18. Source Artifacts

### 18.1 Production Review Packets

| File | SHA-256 |
|------|---------|
| `existing_change_review_packets.jsonl` | `be68fe90ecdd924d6b57cfc19055fe8c978dcf8ff87dbf388fc0f7c7b915d1cf` |
| `new_change_tier1_review_packets.jsonl` | `b11d8176e4854930bd819da5911244c08129cf84425dd7e7e96633fe5e371f08` |
| `owner_candidate_review_overlay.jsonl` | `389ff0e6c4e725424fa04d246316f335c1ea23871a54e57969c9753995facefb` |
| `review_universe_index.jsonl` | `f083e0b2312aee6dfe92eac88fcfde93854c33e7b9d5b3a2005943104e5d4186` |
| `manifest.json` | `04d89f8db429790fb95b47943b98491ad1cb0765c03e0438db05c53f287171d7` |

**Location:** `/home/liongateos/PCOG-Research-Archive/research/gd-bible-revision-review-packets-v1`

### 18.2 Production Backup

```
Location: /mnt/SanDisk-Backup/MASTER_BACKUPS/GD-Bible/gd-bible-revision-review-packets-v1-production-20261015-153001.tgz
SHA-256: 37f3ad3a2ec46e8444ab5615ab6b0ba3ff655857179c1470cf8f147cc09685a5
```

### 18.3 Preimplementation Checkpoint

```
Location: /mnt/SanDisk-Backup/MASTER_BACKUPS/GD-Bible/gd-bible-editorial-review-v1-preimplementation-fea4ab7-20261015-194100.tgz
SHA-256: 4b006746986391b393edd9cfb5acc35f999ad9d38f9afd377066957efe8eff21
```

---

## 19. Deterministic Ghost Coverage Fact

A read-only whole-Bible scan of canonical `en_kjv.json` found:

**108 unique KJV verses containing the word "ghost."**

The candidate universe partitions as:
- 89 unique R001 "Holy Ghost" verses
- 14 ordinary-person death-expression verses in R002
- 5 Jesus death-expression verses in R003

R001 has 90 manifest applications across 89 unique verses because one reference contains the phrase twice.

Therefore, the current candidate detection accounts for the complete canonical "ghost" verse universe.

Where practical, independently re-check deterministic manifest/canonical facts before recording them.

**Do NOT infer editorial correctness from coverage completeness.**
