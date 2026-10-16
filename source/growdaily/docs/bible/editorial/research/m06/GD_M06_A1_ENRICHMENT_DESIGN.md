# GD-M06-A1 Scripture Normalization & Enrichment Design

## Purpose

Define the enrichment layer used by GD Bible research before large-scale
processing begins.

This document defines design only. It does not modify databases,
archive originals, or generate production findings.

## Principles

- Archive originals remain immutable.
- Existing research findings remain derived artifacts.
- AI observations are not authoritative until verified.
- Every result must preserve provenance.

## Enrichment Categories

Initial categories:

1. Scripture references
2. Translation observations
3. Wording observations
4. Terminology observations
5. Historical/context observations

## Evidence Layers

### Layer 1 — Raw Observation

Contains:
- model output
- source document
- quotation
- provenance
- confidence

### Layer 2 — Verification

Contains:
- verified quotation
- scripture assertion status
- supporting evidence
- reviewer/model traceability

### Layer 3 — Approved Research

Contains only validated research conclusions.

## Existing Reference Artifact

The 1,000-entry GD Bible preview review is preserved as a schema reference.

It demonstrates:
- topics
- quotations
- research notes
- confidence
- provenance
- triage status

It is not an authoritative Bible correction set.

## Future Processing Rules

- Preserve raw model output.
- Never silently repair text.
- Separate suggestions from approved findings.
- Maintain source traceability.

## Current Status

Design phase only.

No corpus-wide enrichment execution authorized.

