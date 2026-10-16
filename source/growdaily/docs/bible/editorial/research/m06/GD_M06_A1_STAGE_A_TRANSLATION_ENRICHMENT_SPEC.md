# GD-M06-A1 Stage A Translation Enrichment Specification

## Purpose

Define the Grow Daily Bible Stage A enrichment output.

This specification is for Bible translation research, not CASE search,
semantic retrieval, vectors, embeddings, ranking, or search UI behavior.

## Core Question

For each archived research finding, determine whether it preserves useful
evidence for Bible translation work, including:

- wording decisions
- terminology consistency
- scripture-reference review
- doctrinal or contextual precision
- capitalization or formatting observations
- original-language follow-up
- later human review

## Boundary

Grow Daily Bible creates archive-derived Bible translation research evidence.

CASE owns search, vector retrieval, embeddings, hybrid ranking, and result
presentation.

Do not add fields solely to improve CASE search.

## Required Output Fields

Each model output must be one JSON object with these fields:

- finding_uid
- quote_echo
- topic
- research_observation
- translation_relevance
- translation_issue_type
- word_or_phrase_under_review
- scripture_refs_raw
- scripture_refs_normalized
- scripture_ref_confidence
- doctrinal_or_contextual_theme
- terminology_note
- wording_note
- capitalization_note
- evidence_summary
- evidence_strength
- requires_original_language_check
- requires_human_review
- human_review_priority
- quote_verification
- verification_status
- risk_flags
- model_identity
- generation_timestamp

## Field Intent

finding_uid:
Preserve exact linkage to the original research finding.

quote_echo:
Echo the source quote exactly. This is a guard against accidental rewriting.

topic:
Use the existing finding topic unless clearly unsuitable.

research_observation:
Concise explanation of what the finding may contribute to Bible translation
research.

translation_relevance:
Allowed values:
- none
- low
- medium
- high

translation_issue_type:
Allowed values:
- scripture_reference
- translation
- terminology
- wording
- capitalization
- context
- doctrine
- none
- other

word_or_phrase_under_review:
Specific word or phrase involved, if any.

scripture_refs_raw:
Original scripture reference text from the input.

scripture_refs_normalized:
Array of normalized scripture references. Empty array if none are clear.

scripture_ref_confidence:
Allowed values:
- none
- low
- medium
- high

doctrinal_or_contextual_theme:
Short theme if directly supported by the quote. Do not invent a taxonomy.

terminology_note:
Translation terminology note, if any.

wording_note:
Wording or phrasing note, if any.

capitalization_note:
Capitalization or formatting note, if any.

evidence_summary:
Brief summary of why the quote matters or does not matter.

evidence_strength:
Allowed values:
- weak
- moderate
- strong

requires_original_language_check:
Boolean. True when Hebrew/Greek/source-language review is needed before any
translation decision.

requires_human_review:
Boolean. True when this finding should be reviewed by a human before use.

human_review_priority:
Allowed values:
- none
- low
- medium
- high

quote_verification:
Use the input anchor verdict:
- valid
- mismatch
- out_of_bounds
- unknown

verification_status:
Allowed values:
- model_observation_unverified
- rejected_weak_evidence
- needs_human_review

risk_flags:
Array. Allowed examples:
- invalid_anchor
- weak_quote
- unverified_scripture_ref
- unsupported_claim_risk
- needs_source_context
- possible_duplicate
- original_language_required

## Rules

The model must not:

- invent source text
- rewrite the quote
- create final Bible translation decisions
- claim doctrinal authority
- claim scripture normalization is verified unless deterministic validation did it
- output CASE/search metadata
- output vectors, embeddings, or search phrases

The model must:

- preserve finding_uid exactly
- preserve quote_echo exactly
- treat archive findings as evidence, not final authority
- mark uncertainty clearly
- require human review where appropriate
- return strict JSON only

## Status

Frozen for GD-M06-A1 Stage A preparation.

No model execution is authorized by this file.
