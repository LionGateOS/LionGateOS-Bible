# GD Bible Rule Reviews

**Purpose:** Explain how individual rule/family audit documents are structured and how they relate to the machine-readable registry.

---

## 1. Overview

This directory contains individual audit documents for GD Bible transformation rule families. Each document records:

- Verified facts about the rule family
- Archive evidence audit results
- Evidence gap identification
- External verification needs
- Provisional editorial disposition
- Lifecycle state

---

## 2. Document Structure

Each rule review document follows this structure:

### 2.1 Header

- Rule ID(s) covered
- Title/description
- Family members (for multi-rule families)

### 2.2 Manifest Facts

- Transformation description
- Manifest application count
- Unique verse count
- Canonical coverage verification

### 2.3 Archive Evidence Audit

- Evidence summary
- Direct/partial/indirect finding counts
- Evidence themes identified
- Contrary evidence status

### 2.4 Evidence Gap Analysis

- Where evidence is sparse or absent
- What external verification is needed
- Linguistic/theological questions requiring external sources

### 2.5 Proposition Separation

For families with multiple propositions:
- Lexical proposition (word substitution)
- Grammatical proposition (article/pronoun changes)
- Stylistic proposition (capitalization)
- Theological/semantic proposition

### 2.6 Provisional Disposition

- Review status (e.g., `REVIEW FAMILY`)
- Confidence level (HIGH/MEDIUM/LOW)
- Reasoning for disposition

### 2.7 Lifecycle State

- Current lifecycle state
- `currently_present_in_gd` status
- `owner_decision` status
- `approved_for_application` status

### 2.8 Deferred Rules

Any rules deferred to other policy passes (e.g., reverential capitalization)

---

## 3. Relationship to Machine-Readable Registry

The human-readable documents in this directory correspond to records in:

```
gd_bible_editorial_rule_review_registry.jsonl
```

### 3.1 Registry Schema

Each registry record contains:
- `family_id`: Unique identifier for the rule family
- `rule_ids`: List of rule IDs in the family
- `title`: Human-readable title
- `propositions`: Separated proposition definitions
- `currently_present_in_gd`: Boolean
- `review_lifecycle_status`: Current lifecycle state
- `owner_decision`: Owner decision status
- `approved_for_application`: Approval status
- `provisional_disposition`: Review disposition
- `provisional_confidence`: Confidence level
- `manifest_scope`: Application counts
- `deterministic_coverage`: Coverage verification
- `archive_support`: Archive evidence assessment
- `evidence_counts`: Verified finding counts
- `evidence_themes`: Identified themes
- `contrary_evidence_status`: Contrary evidence finding
- `evidence_gap`: Gap documentation
- `external_verification_questions`: External verification needs
- `deferred_rules`: Deferred rule documentation
- `case_safe_eligibility`: CASE export eligibility
- `case_safe_export_status`: Export generation status
- `source_artifacts`: Source artifact paths/hashes
- `notes`: Additional notes

### 3.2 Synchronization

The registry is the authoritative machine-readable source. Human-readable documents provide:
- Detailed reasoning
- Evidence theme explanations
- Contextual documentation
- Future church-review supporting material

---

## 4. Current Rule Families

| Document | Rule Family | Status |
|----------|-------------|--------|
| `R001_HOLY_GHOST_TO_HOLY_SPIRIT.md` | R001 | EVIDENCE_AUDIT |
| `R002_DEATH_EXPRESSION_ORDINARY.md` | R002/R004/R006/R007/R008 | EVIDENCE_AUDIT |
| `R003_JESUS_DEATH_EXPRESSION.md` | R003/R005 (R009 deferred) | EVIDENCE_AUDIT |
| `R015_GENESIS_1_2_WAS_TO_BECAME.md` | R015 | EVIDENCE_AUDIT |

---

## 5. Armstrong/Flurry Direct Scripture Corrections

**Verified direct Scripture corrections taught by Herbert W. Armstrong or Gerald Flurry are accepted under the owner's standing editorial authority policy.**

See `docs/GD_BIBLE_EDITORIAL_REVIEW_V1.md` §11.3 for the complete policy.

### Source Quotation Requirements

When documenting direct authorial corrections:

1. **Quotation limit:** Up to 3 direct quotations normally, up to 4 when justified
2. **Multiple authors:** Include at least one quotation from each author when both addressed the correction
3. **Source verification:** Record exact source path, document hash (SHA-256), and character position ranges
4. **Distinction:** Separate direct authorial statements from quotations of third-party translations

### Example Documentation

Rule review documents that include direct authorial corrections should follow this format:

```
**Armstrong [DATE] [DOCUMENT TYPE]:**

> [Exact quotation]

- **Source:** `/home/liongateos/PCOG-Research-Archive/[path/to/document.doc]`
- **SHA-256:** `[hash]`
- **Character position:** `[start]–[end]`
```

---

## 6. Evidence Finding UIDs

Fine-grained finding UIDs are sourced from production artifacts (`gd-bible-revision-review-packets-v1`). Individual finding rows must be recovered from those artifacts before any future final church-review publication.

This milestone records aggregate evidence facts and explicitly notes where fine-grained sourcing is required.

---

## 6. Provenance Classes

See `docs/GD_BIBLE_EDITORIAL_REVIEW_V1.md` §7 for the complete provenance class definitions:

- `DETERMINISTIC_CANONICAL`
- `ARCHIVE_NATIVE`
- `ARCHIVE_CITED_EXTERNAL`
- `MODEL_DERIVED`
- `MODEL_EXTERNAL`
- `OWNER_EDITORIAL`

---

## 7. Lifecycle States

See `docs/GD_BIBLE_EDITORIAL_REVIEW_V1.md` §12 for the complete lifecycle:

```
EVIDENCE_AUDIT → EXTERNAL_VERIFICATION → OWNER_DECISION → APPROVED_FOR_APPLICATION → APPLIED → VERIFIED
```

This milestone operates at the `EVIDENCE_AUDIT` stage. No rules are marked as approved.

---

## 8. Important Notes

1. **No Blind Global Replacement:** Rules are not applied as blind search-and-replace. Each rule has deterministic criteria and verse-level exception handling.

2. **Current Presence ≠ Approval:** A transformation's current presence in the GD Bible does NOT constitute approval under this lifecycle.

3. **AI Recommendations ≠ Edits:** Model recommendations do not edit Bible text. Only owner decisions marked `approved_for_application: true` may result in canonical changes.

4. **CASE-Safe Separation:** GD editorial conclusions must not be imported into CASE as archive fact. See `docs/GD_BIBLE_EDITORIAL_REVIEW_V1.md` §14.
