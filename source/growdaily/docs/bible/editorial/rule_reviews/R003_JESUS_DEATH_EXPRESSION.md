# R003/R005 Family — Death Expression (Jesus)

**Rule IDs:** R003, R005 (R009 deferred)
**Family:** Jesus death-expression modernization
**Status:** EVIDENCE_AUDIT
**Recorded:** 2026-10-15 (EDT)

---

## 1. Family Overview

This rule family modernizes the death expression in the five Gospel accounts of Jesus's death. The existing R003/R005 architecture collapses distinct propositions that must be preserved separately.

### 1.1 The Five Jesus Death Verses

| Reference | Gospel |
|-----------|--------|
| Matthew 27:50 | Matthew |
| Mark 15:37 | Mark |
| Mark 15:39 | Mark (narrative continuation) |
| Luke 23:46 | Luke |
| John 19:30 | John |

### 1.2 Existing Rules

| Rule | Transformation | References |
|------|----------------|------------|
| **R003** | ghost → Spirit | 5 |
| **R005** | the → His | 5 |
| **R009** | he → He (Luke 23:46 only) | 1 |

**R009 is explicitly DEFERRED** to the later reverential-capitalization/style-policy pass. Do not include R009 as an approved member of the R003/R005 semantic family.

---

## 2. Proposition Separation

The existing R003/R005 architecture collapses distinct propositions. These must be preserved separately:

### 2.1 P1: Lexical Proposition

**ghost → spirit**

- The core lexical modernization
- Replaces archaic "ghost" with contemporary "spirit"
- Requires linguistic/theological justification

### 2.2 P2: Grammatical Proposition

**the → his**

- Grammatical consequence of P1
- Changes "the ghost" to "his spirit"
- Appears to be grammatical/editorial consequence

### 2.3 P3: Reverential Style Proposition

**his → His**

- Reverential capitalization
- Belongs to reverential-capitalization policy
- Separate from lexical modernization

### 2.4 P4: Semantic/Theological Capitalization Proposition

**spirit → Spirit**

- Theological capitalization of "Spirit"
- Requires RECONSIDERATION
- Archive-cited Fenton wording uses lowercase "spirit"
- Luke 23:46 canonical KJV already contains Jesus saying:
  > "Father, into thy hands I commend my spirit"

  before the narrative clause "he gave up the ghost"

  Therefore, capitalization of "Spirit" must not be silently bundled with the lexical modernization.

---

## 3. Manifest Facts

| Fact | Value |
|------|-------|
| R003 manifest references | 5 |
| R005 manifest references | 5 |
| R009 manifest references | 1 (Luke 23:46 only) |
| Unique verses | 5 |
| Currently present in GD | true (R003, R005) |
| R009 status | deferred_to_style_policy = true |

---

## 4. Archive Evidence Audit

### 4.1 Evidence Summary by Proposition

| Proposition | Archive Support | Notes |
|-------------|-----------------|-------|
| **P1 (ghost→spirit)** | WEAK | Sparse overall; limited support |
| **P2 (the→his)** | NONE | Grammatical consequence |
| **P3 (his→His)** | NONE | Reverential style policy |
| **P4 (spirit→Spirit)** | NONE | Requires reconsideration |

### 4.2 P1 Evidence Details

- **Matthew 27:50:** Contains limited bracketed/archive-cited support
- **Luke 23:46:** Has two relevant bracketed clarifications and stronger local support
- **Other Jesus death verses:** Have no direct packet grounding

### 4.3 P4 Evidence Gap — Critical

Archive-cited Fenton wording uses lowercase "spirit" in this context. Additionally, Luke 23:46 canonical KJV already contains Jesus saying "my spirit" (lowercase) before the narrative clause "he gave up the ghost."

**Therefore:** Capitalization of "Spirit" must not be silently bundled with the lexical modernization. This requires explicit RECONSIDERATION.

### 4.4 Contrary Evidence

No direct contrary archive evidence was identified, but the Fenton citation (ARCHIVE_CITED_EXTERNAL) using lowercase "spirit" challenges P4.

---

## 5. Evidence Gap Analysis

### 5.1 Archive Support Assessment

| Proposition | Assessment |
|-------------|------------|
| P1 | Sparse/WEAK overall |
| P2 | NONE (grammatical) |
| P3 | NONE (style policy) |
| P4 | NONE (requires reconsideration) |

### 5.2 External Verification Questions

1. **P1:** Is "ghost → spirit" semantically faithful for Jesus's death expression?
2. **P2:** Is the possessive "his" grammatically and theologically appropriate?
3. **P3:** Should reverential capitalization apply here (deferred to style policy)?
4. **P4:** Should "spirit" be capitalized as "Spirit" in this context, given:
   - Fenton uses lowercase
   - Jesus's own words in Luke 23:46 use lowercase "spirit"
   - Theological implications of capitalization

### 5.3 Provenance Distinction

Fenton/Moffatt/other translations quoted or cited inside archive documents are:

**ARCHIVE_CITED_EXTERNAL**

They prove archive usage/citation, not independent linguistic correctness.

---

## 6. Provisional Editorial Disposition

| Field | Value |
|-------|-------|
| Provisional disposition | REVIEW FAMILY |
| Provisional confidence | MEDIUM |
| Lifecycle status | EVIDENCE_AUDIT |
| Currently present in GD | true |
| Owner decision | pending |
| Approved for application | false |
| R009 deferred_to_style_policy | true |

### 6.1 Reasoning

- **P1:** Sparse archive support; external verification needed
- **P2:** Grammatical consequence; no separate evidence needed
- **P3:** Belongs to reverential-capitalization policy (deferred)
- **P4:** Requires RECONSIDERATION due to Fenton lowercase and Luke 23:46 internal evidence

### 6.2 Important Note

Do not call R003/R005 approved. The P4 capitalization proposition requires explicit reconsideration.

---

## 7. Lifecycle State

```
Current: EVIDENCE_AUDIT
Next: EXTERNAL_VERIFICATION (required for P1, P4) → OWNER_DECISION (with P4 reconsideration)
```

---

## 8. Deferred Rules

### 8.1 R009

**R009 (he → He in Luke 23:46)** is explicitly deferred to the reverential-capitalization/style-policy pass.

| Field | Value |
|-------|-------|
| Rule ID | R009 |
| Transformation | he → He |
| Reference | Luke 23:46 |
| Status | deferred_to_style_policy = true |
| Family | Not part of R003/R005 semantic family |

---

## 9. CASE-Safe Eligibility

| Field | Value |
|-------|-------|
| CASE-safe eligible | partial |
| CASE-safe export status | not_generated |

The Matthew 27:50 and Luke 23:46 bracketed clarifications provide some archive-grounded material. The Fenton citation (ARCHIVE_CITED_EXTERNAL) is also CASE-safe.

---

## 10. Source Artifacts

### 10.1 Production Review Packets

Review packets for R003/R005 verses are contained in:

```
Location: /home/liongateos/PCOG-Research-Archive/research/gd-bible-revision-review-packets-v1
File: existing_change_review_packets.jsonl
SHA-256: be68fe90ecdd924d6b57cfc19055fe8c978dcf8ff87dbf388fc0f7c7b915d1cf
```

### 10.2 Fine-Grained Finding UIDs

Individual finding UIDs must be sourced from the production artifacts before any future final church-review publication. This document records aggregate evidence facts.

---

## 11. Notes

1. **Proposition separation is critical:** P1-P4 must be evaluated separately, not as a bundled transformation.

2. **P4 requires reconsideration:** The capitalization of "Spirit" is not automatically justified by the lexical modernization.

3. **R009 is deferred:** The reverential capitalization of "He" belongs to a separate style policy.

4. **Luke 23:46 internal evidence:** Jesus's own words ("my spirit") in the same verse challenge the capitalization of "Spirit" in the narrative clause.

5. **Archive-cited translations:** Fenton/Moffatt citations are ARCHIVE_CITED_EXTERNAL, proving archive usage but not independent correctness.

---

## 12. Registry Record Reference

This document corresponds to the R003/R005 family record in `gd_bible_editorial_rule_review_registry.jsonl`.
